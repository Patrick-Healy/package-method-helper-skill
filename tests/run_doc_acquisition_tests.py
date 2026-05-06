#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Live acquisition tests for official package docs.")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--output-root", type=Path, default=repo_root / "work" / "generated" / "source_acquisition_tests")
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
    if args.output_root.exists():
        shutil.rmtree(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [sys.executable, "-m", "py_compile", str(scripts / "acquire_official_package_docs.py")],
        check=True,
    )

    cases = [
        {
            "language": "r",
            "package": "mediation",
            "host_checks": ("search.r-project.org", "cran.r-project.org", "rdrr.io"),
            "min_chars": 2000,
            "metadata_key": "version",
        },
        {
            "language": "python",
            "package": "statsmodels",
            "host_checks": ("statsmodels.org", "pypi.org"),
            "min_chars": 2000,
            "metadata_key": "version",
        },
        {
            "language": "stata",
            "package": "ivreg2",
            "host_checks": ("fmwww.bc.edu",),
            "min_chars": 1000,
            "metadata_key": "description",
        },
    ]

    results: list[dict] = []
    for case in cases:
        payload = run_json(
            [
                sys.executable,
                str(scripts / "acquire_official_package_docs.py"),
                "--language",
                case["language"],
                "--package",
                case["package"],
                "--output-root",
                str(args.output_root),
                "--json",
            ]
        )
        manifest = payload["manifest"]
        output_dir = Path(payload["output_dir"])
        meta_path = output_dir / "official_doc.meta.json"
        assert_true(output_dir.exists(), f"Expected output dir missing: {output_dir}")
        assert_true((output_dir / "acquisition_manifest.json").exists(), "Missing acquisition_manifest.json")
        assert_true((output_dir / "official_doc.md").exists(), "Missing official_doc.md")
        assert_true(meta_path.exists(), "Missing official_doc.meta.json")

        meta = json.loads(meta_path.read_text())
        fetched_url = manifest.get("selected_primary_doc_url", "")
        assert_true(any(host in fetched_url for host in case["host_checks"]), f"Unexpected fetched URL: {fetched_url}")
        assert_true(meta["markdown_chars"] >= case["min_chars"], f"Expected richer doc content for {case['language']}::{case['package']}")
        assert_true(bool(manifest["registry_metadata"].get(case["metadata_key"])), f"Expected registry metadata {case['metadata_key']} for {case['package']}")
        results.append(
            {
                "language": case["language"],
                "package": case["package"],
                "selected_primary_doc_url": fetched_url,
                "markdown_chars": meta["markdown_chars"],
                "metadata_key": case["metadata_key"],
                "metadata_value": manifest["registry_metadata"].get(case["metadata_key"]),
            }
        )

    print(json.dumps({"status": "ok", "output_root": str(args.output_root), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
