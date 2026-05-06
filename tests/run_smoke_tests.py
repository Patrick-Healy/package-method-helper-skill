#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Smoke tests for the public package-method-helper repo.")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--bundles-root", type=Path, required=True)
    return parser.parse_args()


def run_json(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def run_process(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root
    scripts = repo_root / "skills/package-method-helper/scripts"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(scripts / "build_package_method_helper_duckdb.py"),
            str(scripts / "query_package_method_helper_duckdb.py"),
            str(scripts / "export_embedding_chunks.py"),
            str(scripts / "embed_chunks_openai.py"),
            str(scripts / "build_all_bundles.py"),
            str(scripts / "download_prebuilt_duckdb.py"),
            str(scripts / "acquire_official_package_docs.py"),
            str(scripts / "acquire_methods_paper.py"),
            str(scripts / "generate_paper_layer_from_source.py"),
            str(scripts / "ingest_workflow_lib.py"),
            str(scripts / "plan_collection_ingest.py"),
            str(scripts / "ingest_collection_bundle.py"),
        ],
        check=True,
    )

    fixest = run_json([
        sys.executable,
        str(scripts / "query_package_method_helper_duckdb.py"),
        "--db",
        str(args.db),
        "--language",
        "r",
        "--package",
        "fixest",
        "--query",
        "fixed effects clustered standard errors",
        "--limit",
        "3",
        "--json",
    ])
    assert_true(bool(fixest["packages"]), "Expected package hit for fixest")
    assert_true(fixest["packages"][0]["package"] == "fixest", "Top package hit for fixest should be fixest")
    assert_true(bool(fixest["follow_up"]), "Expected follow-up payload for fixest")
    fixest_doc_types = {row["doc_type"] for row in fixest["follow_up"]["core_documents"]}
    assert_true("summary_card" in fixest_doc_types, "Expected summary card in fixest follow-up core docs")
    assert_true("decision_card" in fixest_doc_types, "Expected decision card in fixest follow-up core docs")
    assert_true(bool(fixest["follow_up"]["raw_meta_edges"]), "Expected raw meta edge for fixest")

    statsmodels = run_json([
        sys.executable,
        str(scripts / "query_package_method_helper_duckdb.py"),
        "--db",
        str(args.db),
        "--package",
        "statsmodels",
        "--query",
        "formula OLS clustered inference",
        "--limit",
        "3",
        "--json",
    ])
    assert_true(bool(statsmodels["packages"]), "Expected package hit for statsmodels")
    assert_true(statsmodels["packages"][0]["package"] == "statsmodels", "Top package hit for statsmodels should be statsmodels")
    assert_true(statsmodels["effective_language"] == "python", "Expected package-based language gate for statsmodels")
    assert_true(bool(statsmodels["follow_up"]), "Expected follow-up payload for statsmodels")

    sklearn_alias = run_json([
        sys.executable,
        str(scripts / "query_package_method_helper_duckdb.py"),
        "--db",
        str(args.db),
        "--package",
        "scikit-learn",
        "--query",
        "classification pipeline cross validation",
        "--limit",
        "3",
        "--json",
    ])
    assert_true(bool(sklearn_alias["packages"]), "Expected package hit for scikit-learn alias")
    assert_true(sklearn_alias["packages"][0]["package"] == "sklearn", "Alias scikit-learn should resolve to sklearn")
    assert_true(sklearn_alias["effective_language"] == "python", "Expected alias-based language gate for scikit-learn")

    reghdfe = run_json([
        sys.executable,
        str(scripts / "query_package_method_helper_duckdb.py"),
        "--db",
        str(args.db),
        "--package",
        "reghdfe",
        "--query",
        "event study coefficient plot clustered",
        "--limit",
        "3",
        "--json",
    ])
    assert_true(bool(reghdfe["packages"]), "Expected package hit for reghdfe")
    assert_true(reghdfe["packages"][0]["package"] == "reghdfe", "Top package hit for reghdfe should be reghdfe")
    assert_true(reghdfe["effective_language"] == "stata", "Expected package-based language gate for reghdfe")
    adjacent = {row["package"] for row in reghdfe["follow_up"]["adjacent_packages"]}
    assert_true("esttab" in adjacent or "coefplot" in adjacent, "Expected adjacent package edge for reghdfe")

    syntax_r = run_json([
        sys.executable,
        str(scripts / "query_package_method_helper_duckdb.py"),
        "--db",
        str(args.db),
        "--query",
        "library(dplyr) grouped mutate left_join",
        "--limit",
        "3",
        "--json",
    ])
    assert_true(syntax_r["effective_language"] == "r", "Expected syntax-based language gate for R query")

    ambiguous = run_process([
        sys.executable,
        str(scripts / "query_package_method_helper_duckdb.py"),
        "--db",
        str(args.db),
        "--query",
        "fixed effects clustered standard errors",
        "--json",
    ])
    assert_true(ambiguous.returncode == 2, "Expected ambiguous no-language query to fail language gate")
    ambiguous_payload = json.loads(ambiguous.stderr)
    assert_true(ambiguous_payload["error"] == "language_gate_failed", "Expected language gate failure payload")

    expected = [
        args.bundles_root / "package_method_helper_r_embedding_chunks.jsonl",
        args.bundles_root / "package_method_helper_python_embedding_chunks.jsonl",
        args.bundles_root / "package_method_helper_stata_embedding_chunks.jsonl",
    ]
    unexpected = [
        args.bundles_root / "package_method_helper_all_embedding_chunks.jsonl",
        args.bundles_root / "package_method_helper_all_embedding_chunks.jsonl.manifest.json",
    ]

    for path in expected:
        assert_true(path.exists(), f"Expected bundle missing: {path}")
        manifest = Path(str(path) + ".manifest.json")
        assert_true(manifest.exists(), f"Expected manifest missing: {manifest}")
        meta = json.loads(manifest.read_text())
        assert_true(meta["record_count"] > 0, f"Expected non-empty bundle: {path}")
    for path in unexpected:
        assert_true(not path.exists(), f"Unexpected all-language bundle artifact present: {path}")

    print(json.dumps({
        "status": "ok",
        "db": str(args.db),
        "bundles_root": str(args.bundles_root),
        "checks": [
            "py_compile",
            "fixest_query",
            "statsmodels_query",
            "sklearn_alias_query",
            "reghdfe_query",
            "follow_up_edges",
            "language_gate_r",
            "language_gate_ambiguous",
            "bundle_presence",
            "all_bundle_absent",
            "acquire_official_package_docs_compile",
            "acquire_methods_paper_compile",
            "generate_paper_layer_from_source_compile",
            "download_prebuilt_duckdb_compile",
            "plan_collection_ingest_compile",
            "ingest_collection_bundle_compile",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
