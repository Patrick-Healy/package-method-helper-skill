#!/usr/bin/env python3
"""Create a distributable prebuilt DuckDB bundle and optional manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BUNDLE_NAME = "package_method_helper_duckdb_bundle.zip"
EXPECTED_FILES = ("package_method_helper.duckdb", "package_method_helper.summary.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a distributable prebuilt DuckDB bundle.")
    parser.add_argument("--db-path", type=Path, required=True)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--move-source", action="store_true", help="Move the source DB and summary into the output directory instead of copying.")
    parser.add_argument("--include-readme", action="store_true", help="Write a small README.txt beside the bundle.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stage_file(src: Path, dst: Path, *, move: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() == dst.resolve():
        return
    if move:
        if dst.exists():
            dst.unlink()
        shutil.move(str(src), str(dst))
    else:
        shutil.copy2(src, dst)


def main() -> int:
    args = parse_args()
    db_src = args.db_path.resolve()
    summary_src = args.summary_path.resolve()
    if not db_src.exists():
        raise SystemExit(f"Missing DB source: {db_src}")
    if not summary_src.exists():
        raise SystemExit(f"Missing summary source: {summary_src}")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    staged_db = output_dir / EXPECTED_FILES[0]
    staged_summary = output_dir / EXPECTED_FILES[1]
    stage_file(db_src, staged_db, move=args.move_source)
    stage_file(summary_src, staged_summary, move=args.move_source)

    readme_path = output_dir / "README.txt"
    if args.include_readme:
        readme_path.write_text(
            "Package Method Helper prebuilt DuckDB bundle\n\n"
            "Files:\n"
            "- package_method_helper.duckdb\n"
            "- package_method_helper.summary.json\n"
            "- package_method_helper_duckdb_bundle.zip\n",
            encoding="utf-8",
        )

    zip_path = output_dir / BUNDLE_NAME
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(staged_db, arcname=staged_db.name)
        zf.write(staged_summary, arcname=staged_summary.name)
        if args.include_readme and readme_path.exists():
            zf.write(readme_path, arcname=readme_path.name)

    manifest = {
        "schema_version": 1,
        "created_utc": utc_now(),
        "bundle_name": BUNDLE_NAME,
        "files": {
            staged_db.name: {"size_bytes": staged_db.stat().st_size, "sha256": sha256_file(staged_db)},
            staged_summary.name: {"size_bytes": staged_summary.stat().st_size, "sha256": sha256_file(staged_summary)},
            zip_path.name: {"size_bytes": zip_path.stat().st_size, "sha256": sha256_file(zip_path)},
        },
        "moved_source": bool(args.move_source),
        "distribution_contents": [staged_db.name, staged_summary.name, zip_path.name],
        "notes": [
            "Public distribution manifest for the prebuilt DuckDB bundle.",
            "Local build paths are intentionally omitted.",
        ],
    }
    manifest_path = output_dir / "prebuilt_duckdb_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    payload = {"status": "ok", "output_dir": str(output_dir), "manifest_path": str(manifest_path), "bundle_path": str(zip_path), "moved_source": bool(args.move_source)}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Built prebuilt DB bundle at {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
