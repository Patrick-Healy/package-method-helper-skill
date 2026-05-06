#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


LANGUAGES = ["r", "python", "stata"]


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Build all public Package Method Helper bundles.")
    parser.add_argument("--collection-root", type=Path, required=True, help="Local collection root")
    parser.add_argument("--comparisons-root", type=Path, required=True, help="Local shared comparisons root")
    parser.add_argument("--output-root", type=Path, default=repo_root / "work/generated", help="Output root for DB, bundles, and embeddings")
    parser.add_argument("--embed", action="store_true", help="Create embeddings after exporting JSONL bundles")
    parser.add_argument("--model", default="text-embedding-3-small", help="Embedding model when --embed is set")
    parser.add_argument("--dimensions", type=int, help="Optional embedding dimensions")
    parser.add_argument("--force", action="store_true", help="Rebuild exports and embeddings even when output files already exist")
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("$", " ".join(str(part) for part in cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parents[1]
    scripts = skill_root / "scripts"
    output_root = args.output_root
    duckdb_dir = output_root / "duckdb"
    bundles_dir = output_root / "bundles"
    embeddings_dir = output_root / "embeddings"
    duckdb_dir.mkdir(parents=True, exist_ok=True)
    bundles_dir.mkdir(parents=True, exist_ok=True)
    embeddings_dir.mkdir(parents=True, exist_ok=True)

    db_path = duckdb_dir / "package_method_helper.duckdb"

    run([
        sys.executable,
        str(scripts / "build_package_method_helper_duckdb.py"),
        "--collection-root",
        str(args.collection_root),
        "--comparisons-root",
        str(args.comparisons_root),
        "--output-db",
        str(db_path),
    ])

    export_targets: list[tuple[str, Path]] = [("all", bundles_dir / "package_method_helper_all_embedding_chunks.jsonl")]
    export_targets.extend((lang, bundles_dir / f"package_method_helper_{lang}_embedding_chunks.jsonl") for lang in LANGUAGES)

    for language, output_jsonl in export_targets:
        manifest_path = output_jsonl.with_suffix(output_jsonl.suffix + ".manifest.json")
        if not args.force and output_jsonl.exists() and manifest_path.exists():
            print(f"Skipping existing export: {output_jsonl}")
            continue
        cmd = [
            sys.executable,
            str(scripts / "export_embedding_chunks.py"),
            "--db",
            str(db_path),
            "--output-jsonl",
            str(output_jsonl),
        ]
        if language != "all":
            cmd.extend(["--language", language])
        run(cmd)

    embedding_targets: list[tuple[str, Path, Path]] = []
    if args.embed:
        for language, input_jsonl in export_targets:
            output_jsonl = embeddings_dir / f"package_method_helper_{language}_embeddings.jsonl"
            embedding_targets.append((language, input_jsonl, output_jsonl))
            manifest_path = output_jsonl.with_suffix(output_jsonl.suffix + ".manifest.json")
            if not args.force and output_jsonl.exists() and manifest_path.exists():
                print(f"Skipping existing embeddings: {output_jsonl}")
                continue
            cmd = [
                sys.executable,
                str(scripts / "embed_chunks_openai.py"),
                "--input-jsonl",
                str(input_jsonl),
                "--output-jsonl",
                str(output_jsonl),
                "--model",
                args.model,
            ]
            if args.dimensions is not None:
                cmd.extend(["--dimensions", str(args.dimensions)])
            run(cmd)

    summary = {
        "schema_version": 1,
        "db": str(db_path),
        "exports": {
            language: str(path)
            for language, path in export_targets
        },
        "embeddings": {
            language: str(path)
            for language, _, path in embedding_targets
        },
        "embedding_model": args.model if args.embed else None,
    }
    summary_path = output_root / "package_method_helper_bundle_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
