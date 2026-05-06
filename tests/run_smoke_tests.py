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

    statsmodels = run_json([
        sys.executable,
        str(scripts / "query_package_method_helper_duckdb.py"),
        "--db",
        str(args.db),
        "--language",
        "python",
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

    reghdfe = run_json([
        sys.executable,
        str(scripts / "query_package_method_helper_duckdb.py"),
        "--db",
        str(args.db),
        "--language",
        "stata",
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

    expected = [
        args.bundles_root / "package_method_helper_all_embedding_chunks.jsonl",
        args.bundles_root / "package_method_helper_r_embedding_chunks.jsonl",
        args.bundles_root / "package_method_helper_python_embedding_chunks.jsonl",
        args.bundles_root / "package_method_helper_stata_embedding_chunks.jsonl",
    ]
    for path in expected:
        assert_true(path.exists(), f"Expected bundle missing: {path}")
        manifest = Path(str(path) + ".manifest.json")
        assert_true(manifest.exists(), f"Expected manifest missing: {manifest}")
        meta = json.loads(manifest.read_text())
        assert_true(meta["record_count"] > 0, f"Expected non-empty bundle: {path}")

    print(json.dumps({
        "status": "ok",
        "db": str(args.db),
        "bundles_root": str(args.bundles_root),
        "checks": [
            "py_compile",
            "fixest_query",
            "statsmodels_query",
            "reghdfe_query",
            "bundle_presence",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
