#!/usr/bin/env python3
"""Download the published prebuilt DuckDB bundle and extract it locally."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ENV_URL = "PACKAGE_METHOD_HELPER_PREBUILT_DUCKDB_URL"
USER_AGENT = "package-method-helper-prebuilt-db/1.0"
EXPECTED_FILES = ("package_method_helper.duckdb", "package_method_helper.summary.json")


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Download the prebuilt Package Method Helper DuckDB bundle.")
    parser.add_argument("--url", default=os.environ.get(ENV_URL, ""), help=f"Direct download URL for the published DuckDB bundle zip. Defaults to ${ENV_URL} if set.")
    parser.add_argument("--output-dir", type=Path, default=repo_root / "work" / "generated" / "duckdb")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def download(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/zip, */*;q=0.2"})
    with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out)


def main() -> int:
    args = parse_args()
    if not args.url:
        raise SystemExit(
            f"Missing bundle URL. Pass --url or set {ENV_URL} to a direct zip download URL containing "
            "package_method_helper.duckdb and package_method_helper.summary.json."
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        zip_path = tmpdir / "package_method_helper_bundle.zip"
        download(args.url, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            names = {Path(name).name: name for name in zf.namelist() if not name.endswith("/")}
            extracted = {}
            for filename in EXPECTED_FILES:
                member = names.get(filename)
                if not member:
                    raise FileNotFoundError(f"Expected {filename} in archive downloaded from {args.url}")
                outpath = args.output_dir / filename
                with zf.open(member) as src, outpath.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted[filename] = str(outpath)

    payload = {
        "status": "ok",
        "source_url": args.url,
        "output_dir": str(args.output_dir),
        "files": extracted,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Downloaded prebuilt DuckDB bundle into {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
