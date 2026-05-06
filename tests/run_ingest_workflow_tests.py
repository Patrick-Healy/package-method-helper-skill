#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "skills/package-method-helper/scripts"


def run_json(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_base_r_collection(root: Path) -> tuple[Path, Path, Path]:
    collection_root = root / "collection"
    task_dir = collection_root / "01_r_upload"
    shard_dir = task_dir / "01_r_a"
    package = "fixest"
    language = "r"

    manifest = {
        "language": language,
        "package": package,
        "canonical_name": package,
        "canonical_package_name": package,
        "aliases": [package],
        "source": {"open_doc_url": "https://lrberge.github.io/fixest/reference/"},
        "version": {},
        "content_presence": {
            "raw_doc": True,
            "raw_meta": True,
            "documentation_chunks": True,
            "overview_card": True,
            "summary_card": True,
            "decision_card": True,
            "pattern_card": False,
            "function_card_count": 1,
            "function_documentation_count": 1,
            "paper_card_count": 0,
        },
        "status": {
            "completeness": "complete",
            "confidence_for_codegen": "high",
            "has_function_layer": True,
            "has_paper_layer": False,
        },
        "rag_agent": {
            "role_class": "estimation",
            "agent_safety_class": "safe_with_context",
            "task_tags": ["fixed_effects", "ols"],
            "top_functions_or_commands": ["feols"],
        },
    }
    write_json(shard_dir / "package_manifests/r/fixest.json", manifest)
    write_text(shard_dir / "raw_docs/r/fixest.md", "# fixest\n\nOfficial docs.")
    write_json(shard_dir / "raw_docs/r/fixest.meta.json", {"package": "fixest", "language": "R"})
    write_text(
        shard_dir / "package_doc_collection/cards/r/fixest/summary_r_fixest.md",
        "[TYPE] summary_card\n[LANGUAGE] R\n[PACKAGE] fixest\n\nSummary.\n",
    )
    write_text(
        shard_dir / "package_doc_collection/cards/overview/r/fixest/overview_r_fixest.md",
        "[TYPE] package_overview\n[LANGUAGE] R\n[PACKAGE] fixest\n\nOverview.\n",
    )
    write_text(
        shard_dir / "package_doc_collection/chunks/r/fixest/doc_r_fixest_001.md",
        "[TYPE] documentation\n[LANGUAGE] R\n[PACKAGE] fixest\n\nChunk.\n",
    )

    shard_manifest = {
        "schema_version": 1,
        "shard_id": "01_r_a",
        "label": "R test shard",
        "language": "r",
        "package_count": 1,
        "package_list": ["fixest"],
        "contains_comparisons": False,
        "depends_on_shared_comparisons": True,
        "upload_order": 1,
        "validation_timestamp_utc": "2026-01-01T00:00:00+00:00",
        "content_digest_sha256": "fixture",
        "file_count": 6,
        "total_bytes": 100,
        "median_file_size_bytes": 10,
        "largest_file_size_bytes": 50,
        "approx_token_estimate": 25,
        "largest_packages": [{"package": "fixest", "approx_bytes": 100}],
    }
    task_manifest = {
        "schema_version": 1,
        "task_id": "01_r_upload",
        "label": "R test upload task",
        "language": "r",
        "upload_order": 1,
        "source_bundle": "fixture",
        "contains_shared_comparisons": False,
        "shared_comparisons_note": "",
        "shard_count": 1,
        "package_count": 1,
        "package_list": ["fixest"],
        "shards": [shard_manifest],
    }
    master_manifest = {
        "schema_version": 1,
        "bundle_name": "fixture_collection",
        "source_bundle": "fixture",
        "task_count": 1,
        "global_upload_order": ["01_r_upload"],
        "contains_shared_comparisons": False,
        "shared_comparisons_source": "",
        "tasks": [task_manifest],
    }
    write_json(shard_dir / "shard_manifest.json", shard_manifest)
    write_json(task_dir / "language_upload_manifest.json", task_manifest)
    write_json(collection_root / "master_manifest.json", master_manifest)
    return collection_root, task_dir, shard_dir


def make_new_package_bundle(root: Path) -> Path:
    bundle_root = root / "bundle"
    language = "r"
    package = "mediation"
    manifest = {
        "language": language,
        "package": package,
        "canonical_name": package,
        "canonical_package_name": package,
        "aliases": [package],
        "source": {"open_doc_url": "https://search.r-project.org/CRAN/refmans/mediation/html/00Index.html"},
        "version": {},
        "content_presence": {
            "raw_doc": True,
            "raw_meta": True,
            "documentation_chunks": True,
            "overview_card": True,
            "summary_card": True,
            "decision_card": True,
            "pattern_card": False,
            "function_card_count": 1,
            "function_documentation_count": 1,
            "paper_card_count": 0,
        },
        "status": {
            "completeness": "gap_fill_draft",
            "confidence_for_codegen": "medium",
            "has_function_layer": True,
            "has_paper_layer": False,
        },
        "rag_agent": {
            "role_class": "causal_estimation",
            "agent_safety_class": "expert_only",
            "task_tags": ["mediation"],
            "top_functions_or_commands": ["mediate"],
        },
    }
    write_json(bundle_root / "package_manifests/r/mediation.json", manifest)
    write_text(bundle_root / "raw_docs/r/mediation.md", "# mediation\n\nOfficial docs.")
    write_json(bundle_root / "raw_docs/r/mediation.meta.json", {"package": "mediation", "language": "R"})
    write_text(
        bundle_root / "package_doc_collection/cards/r/mediation/summary_r_mediation.md",
        "[TYPE] summary_card\n[LANGUAGE] R\n[PACKAGE] mediation\n\nSummary.\n",
    )
    write_text(
        bundle_root / "package_doc_collection/cards/overview/r/mediation/overview_r_mediation.md",
        "[TYPE] package_overview\n[LANGUAGE] R\n[PACKAGE] mediation\n\nOverview.\n",
    )
    write_text(
        bundle_root / "package_doc_collection/chunks/r/mediation/doc_r_mediation_001.md",
        "[TYPE] documentation\n[LANGUAGE] R\n[PACKAGE] mediation\n\nChunk.\n",
    )
    return bundle_root


def query_db_count(db_path: Path, sql: str, params: tuple) -> int:
    con = duckdb.connect(str(db_path))
    try:
        return int(con.execute(sql, params).fetchone()[0])
    finally:
        con.close()


def main() -> int:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(SCRIPTS / "ingest_workflow_lib.py"),
            str(SCRIPTS / "plan_collection_ingest.py"),
            str(SCRIPTS / "ingest_collection_bundle.py"),
        ],
        check=True,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        collection_root, _, shard_dir = make_base_r_collection(tmpdir)
        output_root = tmpdir / "generated"
        paper_sources = output_root / "paper_sources"
        paper_layers = output_root / "paper_layers"
        plans_root = output_root / "plans"
        db_root = output_root / "duckdb"
        db_root.mkdir(parents=True, exist_ok=True)

        run_json([
            sys.executable,
            str(SCRIPTS / "acquire_methods_paper.py"),
            "--language",
            "r",
            "--package",
            "fixest",
            "--output-root",
            str(paper_sources),
            "--json",
        ])
        run_json([
            sys.executable,
            str(SCRIPTS / "generate_paper_layer_from_source.py"),
            "--language",
            "r",
            "--package",
            "fixest",
            "--paper-source-root",
            str(paper_sources),
            "--package-manifest",
            str(shard_dir / "package_manifests/r/fixest.json"),
            "--output-root",
            str(paper_layers),
            "--json",
        ])
        plan_existing = run_json([
            sys.executable,
            str(SCRIPTS / "plan_collection_ingest.py"),
            "--collection-root",
            str(collection_root),
            "--bundle-root",
            str(paper_layers),
            "--language",
            "r",
            "--package",
            "fixest",
            "--output-root",
            str(plans_root),
            "--json",
        ])
        assert_true(plan_existing["plan"]["action_type"] == "paper_layer_update", "Expected paper-layer update plan")
        assert_true(plan_existing["plan"]["existing_package_found"] is True, "Expected existing package")

        applied_existing = run_json([
            sys.executable,
            str(SCRIPTS / "ingest_collection_bundle.py"),
            "--approval-manifest",
            plan_existing["approval_manifest_path"],
            "--approve",
            "--rebuild-db",
            "--output-db",
            str(db_root / "paper_update.duckdb"),
            "--json",
        ])
        assert_true((shard_dir / "package_doc_collection/cards/papers/r/fixest/paper_r_fixest.md").exists(), "Missing ingested paper note")
        updated_manifest = json.loads((shard_dir / "package_manifests/r/fixest.json").read_text())
        assert_true(updated_manifest["content_presence"]["paper_card_count"] == 3, "paper_card_count not updated")
        assert_true(updated_manifest["status"]["has_paper_layer"] is True, "has_paper_layer not updated")
        assert_true(query_db_count(db_root / "paper_update.duckdb", "select count(*) from documents where package = ? and doc_type = ?", ("fixest", "paper_note")) == 1, "paper note not indexed")

        bundle_root = make_new_package_bundle(tmpdir / "new_package")
        plan_new = run_json([
            sys.executable,
            str(SCRIPTS / "plan_collection_ingest.py"),
            "--collection-root",
            str(collection_root),
            "--bundle-root",
            str(bundle_root),
            "--language",
            "r",
            "--package",
            "mediation",
            "--output-root",
            str(plans_root),
            "--json",
        ])
        assert_true(plan_new["plan"]["action_type"] == "package_addition", "Expected package addition plan")
        assert_true(plan_new["plan"]["existing_package_found"] is False, "Did not expect existing package")

        applied_new = run_json([
            sys.executable,
            str(SCRIPTS / "ingest_collection_bundle.py"),
            "--approval-manifest",
            plan_new["approval_manifest_path"],
            "--approve",
            "--rebuild-db",
            "--output-db",
            str(db_root / "package_add.duckdb"),
            "--json",
        ])
        assert_true((shard_dir / "package_manifests/r/mediation.json").exists(), "Missing ingested package manifest")
        task_manifest = json.loads((collection_root / "01_r_upload/language_upload_manifest.json").read_text())
        assert_true(task_manifest["package_count"] == 2, "Task package_count did not increment")
        assert_true("mediation" in task_manifest["package_list"], "New package not added to package_list")
        assert_true(query_db_count(db_root / "package_add.duckdb", "select count(*) from packages where package = ?", ("mediation",)) == 1, "New package not indexed")

        print(json.dumps({
            "status": "ok",
            "paper_update": applied_existing["duckdb_rebuild"],
            "package_addition": applied_new["duckdb_rebuild"],
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
