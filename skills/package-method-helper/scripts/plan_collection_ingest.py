#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ingest_workflow_lib import (
    choose_target_shard,
    detect_bundle_type,
    enumerate_package_bundle_files,
    enumerate_paper_layer_files,
    find_package_in_task,
    find_task_manifest,
    load_json,
    utc_now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Create a reviewable approval plan before ingesting a new package bundle or paper-layer update.")
    parser.add_argument("--collection-root", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--language", required=True, choices=("r", "python", "stata"))
    parser.add_argument("--package", required=True)
    parser.add_argument("--output-root", type=Path, default=repo_root / "work" / "generated" / "ingest_plans")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def render_markdown(plan: dict) -> str:
    lines = [
        f"# Ingest Approval Plan — {plan['language']}::{plan['package']}",
        "",
        f"- Status: `{plan['approval_status']}`",
        f"- Action: `{plan['action_type']}`",
        f"- Collection root: `{plan['collection_root']}`",
        f"- Target task: `{plan['target_task_id']}`",
        f"- Target shard: `{plan['target_shard_id']}`",
        f"- Existing package found: `{plan['existing_package_found']}`",
        f"- Rebuild DuckDB recommended: `{plan['rebuild_duckdb_recommended']}`",
        "",
        "## Files to write",
    ]
    for item in plan["file_plan"]:
        lines.append(f"- `{item['target_relative_path']}` ← `{item['source_path']}`")
    lines.extend([
        "",
        "## Safety checks",
        "- Review this plan before applying it.",
        "- Use the ingest command only after confirming the target shard is appropriate.",
        "- Rebuild the DuckDB index after ingest so the new files are queryable.",
        "",
        "## Apply",
        "```bash",
        f"python3 skills/package-method-helper/scripts/ingest_collection_bundle.py --approval-manifest {plan['approval_manifest_path']} --approve --json",
        "```",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    collection_root = args.collection_root.resolve()
    bundle_root = args.bundle_root.resolve()
    language = args.language.lower()
    package = args.package

    task_dir, task_manifest = find_task_manifest(collection_root, language)
    existing = find_package_in_task(task_dir, language, package)
    bundle_type, detected_root = detect_bundle_type(bundle_root, language, package)

    if bundle_type == "paper_layer_update":
        if not existing:
            raise SystemExit(f"Paper-layer updates require an existing package manifest in the collection for {language}::{package}")
        target_shard_dir, existing_manifest_path, _ = existing
        mapping = enumerate_paper_layer_files(detected_root, language, package)
    else:
        if existing:
            raise SystemExit(f"Package {language}::{package} already exists in the collection; treat this as an update manually")
        target_shard_dir, _ = choose_target_shard(task_dir)
        existing_manifest_path = None
        mapping = enumerate_package_bundle_files(detected_root, language, package)

    outdir = args.output_root / language / package
    outdir.mkdir(parents=True, exist_ok=True)
    approval_manifest_path = outdir / "ingest_approval_manifest.json"
    file_plan = [
        {
            "source_path": str(src),
            "target_relative_path": str((target_shard_dir / rel).relative_to(collection_root)),
            "target_shard_relative_path": str(rel),
        }
        for src, rel in mapping
    ]
    plan = {
        "workflow_version": "1.0",
        "created_utc": utc_now_iso(),
        "approval_status": "pending_user_approval",
        "action_type": bundle_type,
        "language": language,
        "package": package,
        "collection_root": str(collection_root),
        "bundle_root": str(bundle_root),
        "bundle_detected_root": str(detected_root),
        "target_task_id": task_manifest.get("task_id", task_dir.name),
        "target_task_path": str(task_dir),
        "target_shard_id": target_shard_dir.name,
        "target_shard_path": str(target_shard_dir),
        "existing_package_found": bool(existing),
        "existing_package_manifest_path": str(existing_manifest_path) if existing_manifest_path else "",
        "rebuild_duckdb_recommended": True,
        "file_plan": file_plan,
        "approval_manifest_path": str(approval_manifest_path),
    }
    write_json(approval_manifest_path, plan)
    (outdir / "ingest_approval.md").write_text(render_markdown(plan), encoding="utf-8")

    payload = {"status": "ok", "approval_manifest_path": str(approval_manifest_path), "plan": plan}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Wrote approval plan to {approval_manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
