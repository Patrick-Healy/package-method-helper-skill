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
    parser = argparse.ArgumentParser(description="Live tests for methods-paper acquisition.")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--output-root", type=Path, default=repo_root / "work" / "generated" / "paper_acquisition_tests")
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
        [sys.executable, "-m", "py_compile", str(scripts / "acquire_methods_paper.py")],
        check=True,
    )

    cases = [
        {
            "language": "r",
            "package": "MatchIt",
            "host_checks": ("jstatsoft.org",),
            "min_chars": 900,
            "source_type": "software_paper",
            "scope_checks": ("landing_page", "long_form_html"),
            "must_contain": ("matchit", "abstract"),
        },
        {
            "language": "r",
            "package": "plm",
            "host_checks": ("jstatsoft.org",),
            "min_chars": 600,
            "source_type": "software_paper",
            "scope_checks": ("landing_page", "long_form_html"),
            "must_contain": ("panel data", "plm"),
        },
        {
            "language": "python",
            "package": "doubleml",
            "host_checks": ("jmlr.org",),
            "min_chars": 1200,
            "source_type": "software_paper",
            "scope_checks": ("landing_page", "long_form_html"),
            "must_contain": ("doubleml", "machine learning"),
        },
        {
            "language": "python",
            "package": "statsmodels",
            "host_checks": ("proceedings.scipy.org",),
            "min_chars": 1100,
            "source_type": "software_paper",
            "scope_checks": ("landing_page", "long_form_html"),
            "must_contain": ("statsmodels", "econometric"),
        },
        {
            "language": "stata",
            "package": "boottest",
            "host_checks": ("ideas.repec.org",),
            "min_chars": 1200,
            "source_type": "methods_paper",
            "scope_checks": ("abstract_page",),
            "must_contain": ("boottest", "bootstrap"),
        },
        {
            "language": "r",
            "package": "fixest",
            "host_checks": ("arxiv.org",),
            "min_chars": 1000,
            "source_type": "software_paper",
            "scope_checks": ("landing_page", "abstract_page"),
            "must_contain": ("fixest", "econometric"),
        },
        {
            "language": "r",
            "package": "lavaan",
            "paper_url": "https://www.jstatsoft.org/article/view/v048i02",
            "paper_title": "lavaan: An R Package for Structural Equation Modeling",
            "paper_source_type": "software_paper",
            "host_checks": ("jstatsoft.org",),
            "min_chars": 900,
            "source_type": "software_paper",
            "scope_checks": ("landing_page", "long_form_html"),
            "must_contain": ("structural equation", "lavaan"),
        },
    ]

    results: list[dict] = []
    for case in cases:
        cmd = [
            sys.executable,
            str(scripts / "acquire_methods_paper.py"),
            "--language",
            case["language"],
            "--package",
            case["package"],
            "--output-root",
            str(args.output_root),
            "--json",
        ]
        if case.get("paper_url"):
            cmd.extend(["--paper-url", case["paper_url"]])
        if case.get("paper_title"):
            cmd.extend(["--paper-title", case["paper_title"]])
        if case.get("paper_source_type"):
            cmd.extend(["--paper-source-type", case["paper_source_type"]])

        payload = run_json(cmd)
        manifest = payload["manifest"]
        output_dir = Path(payload["output_dir"])
        meta_path = output_dir / "paper_source.meta.json"
        assert_true(output_dir.exists(), f"Expected output dir missing: {output_dir}")
        assert_true((output_dir / "paper_source_manifest.json").exists(), "Missing paper_source_manifest.json")
        assert_true((output_dir / "paper_source.md").exists(), "Missing paper_source.md")
        assert_true(meta_path.exists(), "Missing paper_source.meta.json")

        meta = json.loads(meta_path.read_text())
        markdown_text = (output_dir / "paper_source.md").read_text().lower()
        fetched_url = manifest.get("selected_paper_url", "")
        assert_true(any(host in fetched_url for host in case["host_checks"]), f"Unexpected fetched URL: {fetched_url}")
        assert_true(meta["markdown_chars"] >= case["min_chars"], f"Expected richer paper content for {case['language']}::{case['package']}")
        assert_true(manifest.get("paper_source_type") == case["source_type"], f"Unexpected paper source type for {case['package']}")
        assert_true(manifest.get("paper_capture_scope") in case["scope_checks"], f"Unexpected paper capture scope for {case['package']}")
        for token in case["must_contain"]:
            assert_true(token in markdown_text, f"Expected token '{token}' in paper source for {case['package']}")
        results.append(
            {
                "language": case["language"],
                "package": case["package"],
                "selected_paper_url": fetched_url,
                "paper_source_type": manifest.get("paper_source_type"),
                "paper_capture_scope": manifest.get("paper_capture_scope"),
                "markdown_chars": meta["markdown_chars"],
            }
        )

    print(json.dumps({"status": "ok", "output_root": str(args.output_root), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
