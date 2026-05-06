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
    parser = argparse.ArgumentParser(description="Generate and validate paper-layer cards from acquired paper sources.")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--paper-source-root", type=Path, default=repo_root / "work" / "generated" / "paper_layer_test_sources")
    parser.add_argument("--output-root", type=Path, default=repo_root / "work" / "generated" / "paper_layer_tests")
    return parser.parse_args()


def run_json(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_fixture_manifest(path: Path, *, language: str, package: str, top_functions: list[str]) -> None:
    payload = {
        "language": language,
        "package": package,
        "canonical_package_name": package,
        "content_presence": {"paper_card_count": 0},
        "status": {"has_paper_layer": False},
        "rag_agent": {"top_functions_or_commands": top_functions},
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root
    scripts = repo_root / "skills/package-method-helper/scripts"
    if args.paper_source_root.exists():
        shutil.rmtree(args.paper_source_root)
    if args.output_root.exists():
        shutil.rmtree(args.output_root)
    args.paper_source_root.mkdir(parents=True, exist_ok=True)
    args.output_root.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(scripts / "acquire_methods_paper.py"),
            str(scripts / "generate_paper_layer_from_source.py"),
        ],
        check=True,
    )

    cases = [
        {
            "language": "r",
            "package": "fixest",
            "top_functions": ["feols", "feglm"],
            "must_contain": ("estimands", "feols"),
        },
        {
            "language": "python",
            "package": "statsmodels",
            "top_functions": ["statsmodels.formula.api.ols", "statsmodels.api.OLS"],
            "must_contain": ("econometric", "statsmodels.formula.api.ols"),
        },
        {
            "language": "stata",
            "package": "boottest",
            "top_functions": ["boottest"],
            "must_contain": ("bootstrap", "boottest"),
        },
    ]

    results: list[dict] = []
    for case in cases:
        run_json([
            sys.executable,
            str(scripts / "acquire_methods_paper.py"),
            "--language",
            case["language"],
            "--package",
            case["package"],
            "--output-root",
            str(args.paper_source_root),
            "--json",
        ])

        manifest_dir = args.output_root / "fixtures"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / f"{case['language']}_{case['package']}.json"
        write_fixture_manifest(
            manifest_path,
            language=case["language"],
            package=case["package"],
            top_functions=case["top_functions"],
        )

        payload = run_json([
            sys.executable,
            str(scripts / "generate_paper_layer_from_source.py"),
            "--language",
            case["language"],
            "--package",
            case["package"],
            "--paper-source-root",
            str(args.paper_source_root),
            "--output-root",
            str(args.output_root),
            "--package-manifest",
            str(manifest_path),
            "--json",
        ])

        outdir = Path(payload["output_dir"])
        layer_manifest = json.loads((outdir / "paper_layer_manifest.json").read_text())
        paper_path = outdir / f"paper_{case['language']}_{case['package']}.md"
        equation_path = outdir / f"equation_{case['language']}_{case['package']}.md"
        bridge_path = outdir / f"bridge_{case['language']}_{case['package']}.md"
        updated_manifest_path = outdir / "updated_package_manifest.json"

        for path in (paper_path, equation_path, bridge_path, updated_manifest_path):
            assert_true(path.exists(), f"Expected generated file missing: {path}")

        paper_text = paper_path.read_text().lower()
        equation_text = equation_path.read_text().lower()
        bridge_text = bridge_path.read_text().lower()
        for token in case["must_contain"]:
            assert_true(token.lower() in paper_text or token.lower() in equation_text or token.lower() in bridge_text, f"Expected token '{token}' in generated cards for {case['package']}")

        assert_true("[TYPE] paper_note" in paper_path.read_text(), "paper_note header missing")
        assert_true("[TYPE] equation_note" in equation_path.read_text(), "equation_note header missing")
        assert_true("[TYPE] method_bridge_card" in bridge_path.read_text(), "method_bridge_card header missing")

        updated_manifest = json.loads(updated_manifest_path.read_text())
        assert_true(updated_manifest["content_presence"]["paper_card_count"] == 3, "paper_card_count not updated")
        assert_true(updated_manifest["status"]["has_paper_layer"] is True, "has_paper_layer not updated")
        assert_true(layer_manifest["paper_source_url"], "paper_source_url missing from layer manifest")

        results.append(
            {
                "language": case["language"],
                "package": case["package"],
                "paper_source_url": layer_manifest["paper_source_url"],
                "generated_files": layer_manifest["generated_files"],
            }
        )

    print(json.dumps({"status": "ok", "output_root": str(args.output_root), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
