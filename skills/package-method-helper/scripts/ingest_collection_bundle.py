#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ingest_workflow_lib import (
    compute_shard_manifest,
    compute_task_manifest,
    copy_mapping,
    load_json,
    update_master_manifest,
    write_json,
)


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Apply an approved plan to ingest a new package bundle or paper-layer update into a collection.")
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument("--approve", action="store_true", help="Required safety flag to apply the plan.")
    parser.add_argument("--rebuild-db", action="store_true")
    parser.add_argument("--comparisons-root", type=Path, default=None)
    parser.add_argument("--output-db", type=Path, default=repo_root / "work" / "generated" / "duckdb" / "package_method_helper.duckdb")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def rebuild_duckdb(collection_root: Path, comparisons_root: Path | None, output_db: Path) -> dict:
    script = Path(__file__).resolve().parent / "build_package_method_helper_duckdb.py"
    cmd = [
        sys.executable,
        str(script),
        "--collection-root",
        str(collection_root),
        "--output-db",
        str(output_db),
    ]
    if comparisons_root:
        cmd.extend(["--comparisons-root", str(comparisons_root)])
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def main() -> int:
    args = parse_args()
    if not args.approve:
        raise SystemExit("Refusing to ingest without --approve")

    approval_path = args.approval_manifest.resolve()
    plan = load_json(approval_path)
    collection_root = Path(plan["collection_root"]).resolve()
    target_task_path = Path(plan["target_task_path"]).resolve()
    target_shard_path = Path(plan["target_shard_path"]).resolve()
    target_task_manifest_path = target_task_path / "language_upload_manifest.json"
    target_shard_manifest_path = target_shard_path / "shard_manifest.json"

    mapping = [(Path(item["source_path"]), Path(item["target_shard_relative_path"])) for item in plan["file_plan"]]
    copied = copy_mapping(mapping, target_shard_path)

    old_shard_manifest = load_json(target_shard_manifest_path)
    new_shard_manifest = compute_shard_manifest(target_shard_path, old_shard_manifest)
    write_json(target_shard_manifest_path, new_shard_manifest)

    old_task_manifest = load_json(target_task_manifest_path)
    new_task_manifest = compute_task_manifest(target_task_path, old_task_manifest)
    write_json(target_task_manifest_path, new_task_manifest)

    master_manifest = update_master_manifest(collection_root)

    rebuild_summary = None
    if args.rebuild_db:
        rebuild_summary = rebuild_duckdb(collection_root, args.comparisons_root.resolve() if args.comparisons_root else None, args.output_db.resolve())

    result = {
        "status": "ok",
        "approval_manifest_path": str(approval_path),
        "action_type": plan["action_type"],
        "language": plan["language"],
        "package": plan["package"],
        "copied_files": copied,
        "updated_shard_manifest_path": str(target_shard_manifest_path),
        "updated_task_manifest_path": str(target_task_manifest_path),
        "updated_master_manifest_path": str(collection_root / "master_manifest.json"),
        "shard_package_count": new_shard_manifest["package_count"],
        "task_package_count": new_task_manifest["package_count"],
        "task_id": new_task_manifest["task_id"],
        "shard_id": new_shard_manifest["shard_id"],
        "duckdb_rebuild": rebuild_summary,
    }
    applied_path = approval_path.with_name("ingest_applied_manifest.json")
    write_json(applied_path, result)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Applied ingest plan and wrote {applied_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
