#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import duckdb


HEADER_RE = re.compile(r"^\[([A-Z0-9_]+)\]\s*(.*)$")
HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    return argparse.ArgumentParser(description="Build a DuckDB index for the Package Method Helper corpus.").parse_args([]) if False else _build_parser(repo_root).parse_args()


def _build_parser(repo_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a DuckDB index for the Package Method Helper corpus.")
    parser.add_argument(
        "--collection-root",
        type=Path,
        default=repo_root / "work/generated/upload_ready/package_methods_top50_language_upload_tasks",
        help="Root folder containing the language upload tasks.",
    )
    parser.add_argument(
        "--comparisons-root",
        type=Path,
        default=repo_root / "work/generated/upload_ready/package_methods_top50_sync_safe/00_comparisons",
        help="Optional shared comparisons shard.",
    )
    parser.add_argument(
        "--output-db",
        type=Path,
        default=repo_root / "work/generated/duckdb/package_method_helper.duckdb",
        help="DuckDB file to create.",
    )
    parser.add_argument(
        "--schema-sql",
        type=Path,
        default=repo_root / "skills/package-method-helper/assets/duckdb_schema.sql",
        help="Path to the SQL schema file.",
    )
    return parser


def repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_csvish(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_header_and_body(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    header: dict[str, str] = {}
    idx = 0
    matched_any = False
    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            idx += 1
            break
        match = HEADER_RE.match(line)
        if not match:
            break
        matched_any = True
        header[match.group(1)] = match.group(2).strip()
        idx += 1
    if matched_any:
        body = "\n".join(lines[idx:]).strip()
        return header, body
    return {}, text.strip()


def first_heading(text: str) -> str | None:
    match = HEADING_RE.search(text)
    return match.group(1).strip() if match else None


def infer_doc_context(path: Path, header: dict[str, str]) -> tuple[str | None, str | None, str | None]:
    language = header.get("LANGUAGE", "").strip().lower() or None
    package = header.get("PACKAGE", "").strip() or None
    canonical = header.get("CANONICAL_PACKAGE", "").strip() or package
    parts = path.parts
    if "raw_docs" in parts:
        idx = parts.index("raw_docs")
        if idx + 1 < len(parts):
            language = language or parts[idx + 1].lower()
        if idx + 2 < len(parts) and package is None:
            name = parts[idx + 2]
            if name.endswith(".meta.json"):
                package = name[: -len(".meta.json")]
            else:
                package = Path(name).stem
            canonical = canonical or package
    elif "package_manifests" in parts:
        idx = parts.index("package_manifests")
        if idx + 1 < len(parts):
            language = language or parts[idx + 1].lower()
        if idx + 2 < len(parts) and package is None:
            package = Path(parts[idx + 2]).stem
            canonical = canonical or package
    else:
        for marker in ("cards", "chunks"):
            if marker in parts:
                idx = parts.index(marker)
                for offset in range(1, min(5, len(parts) - idx)):
                    segment = parts[idx + offset]
                    lower = segment.lower()
                    if lower in {"r", "python", "stata", "shared", "comparisons", "functions", "papers", "overview", "briefings"}:
                        if lower in {"r", "python", "stata", "shared"}:
                            language = language or lower
                        continue
                    if package is None and Path(segment).suffix == "":
                        package = segment
                        canonical = canonical or package
                        break
    return language, package, canonical


def classify_source_kind(path: Path) -> str:
    parts = path.parts
    name = path.name
    if name.endswith(".meta.json"):
        return "raw_meta"
    if "raw_docs" in parts:
        return "raw_doc"
    if "package_doc_collection" in parts and "cards" in parts:
        return "comparison_card" if "comparisons" in parts else "card"
    if "package_doc_collection" in parts and "chunks" in parts:
        return "chunk"
    return "document"


def load_text_record(path: Path) -> tuple[dict[str, str], str, str]:
    text = path.read_text(encoding="utf-8")
    header, body = parse_header_and_body(text)
    full_text = text.strip()
    return header, body, full_text


def manifest_path_for_package(shard_dir: Path, language: str, package: str, repo_root: Path) -> str:
    path = shard_dir / "package_manifests" / language / f"{package}.json"
    return repo_relative(path, repo_root) if path.exists() else ""


def likely_summary_path(shard_dir: Path, language: str, package: str, repo_root: Path) -> str:
    path = shard_dir / "package_doc_collection" / "cards" / language / package / f"summary_{language}_{package}.md"
    return repo_relative(path, repo_root) if path.exists() else ""


def likely_raw_doc_path(shard_dir: Path, language: str, package: str, repo_root: Path) -> str:
    path = shard_dir / "raw_docs" / language / f"{package}.md"
    return repo_relative(path, repo_root) if path.exists() else ""


def build_rows(args: argparse.Namespace) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    repo_root = Path(__file__).resolve().parents[3]
    collection_root = args.collection_root.resolve()
    comparisons_root = args.comparisons_root.resolve() if args.comparisons_root else None

    master_manifest = load_json(collection_root / "master_manifest.json")

    task_rows: list[tuple[Any, ...]] = []
    shard_rows: list[tuple[Any, ...]] = []
    package_rows: list[tuple[Any, ...]] = []
    document_rows: list[tuple[Any, ...]] = []

    for task_id in master_manifest.get("global_upload_order", []):
        task_dir = collection_root / task_id
        task_manifest = load_json(task_dir / "language_upload_manifest.json")
        task_rows.append(
            (
                task_manifest.get("task_id"),
                task_manifest.get("label"),
                task_manifest.get("language"),
                task_manifest.get("upload_order"),
                task_manifest.get("package_count"),
                task_manifest.get("shard_count"),
                task_manifest.get("source_bundle"),
                bool(task_manifest.get("contains_shared_comparisons")),
                repo_relative(task_dir, repo_root),
                json.dumps(task_manifest, ensure_ascii=False),
            )
        )

        for shard_entry in task_manifest.get("shards", []):
            shard_id = shard_entry["shard_id"]
            shard_dir = task_dir / shard_id
            shard_manifest_path = shard_dir / "shard_manifest.json"
            shard_manifest = load_json(shard_manifest_path) if shard_manifest_path.exists() else shard_entry
            shard_rows.append(
                (
                    task_manifest.get("task_id"),
                    shard_manifest.get("shard_id"),
                    shard_manifest.get("label"),
                    shard_manifest.get("language"),
                    shard_manifest.get("upload_order"),
                    shard_manifest.get("package_count"),
                    shard_manifest.get("file_count"),
                    shard_manifest.get("total_bytes"),
                    shard_manifest.get("approx_token_estimate"),
                    bool(shard_manifest.get("contains_comparisons")),
                    bool(shard_manifest.get("depends_on_shared_comparisons")),
                    shard_manifest.get("content_digest_sha256"),
                    repo_relative(shard_dir, repo_root),
                    json.dumps(shard_manifest, ensure_ascii=False),
                )
            )

            for manifest_file in sorted((shard_dir / "package_manifests").rglob("*.json")):
                manifest = load_json(manifest_file)
                language = str(manifest.get("language", shard_manifest.get("language", ""))).lower()
                package = manifest.get("package")
                rag = manifest.get("rag_agent", {}) or {}
                package_rows.append(
                    (
                        task_manifest.get("task_id"),
                        shard_manifest.get("shard_id"),
                        language,
                        package,
                        manifest.get("canonical_name"),
                        manifest.get("canonical_package_name"),
                        rag.get("role_class"),
                        rag.get("agent_safety_class"),
                        rag.get("selection_priority"),
                        rag.get("retrieval_priority"),
                        json.dumps(manifest.get("aliases", []), ensure_ascii=False),
                        json.dumps(rag.get("query_aliases", []), ensure_ascii=False),
                        json.dumps(rag.get("task_tags", []), ensure_ascii=False),
                        json.dumps(rag.get("common_pairings", []), ensure_ascii=False),
                        json.dumps(rag.get("top_functions_or_commands", []), ensure_ascii=False),
                        json.dumps(rag.get("choose_when", []), ensure_ascii=False),
                        json.dumps(rag.get("avoid_when", []), ensure_ascii=False),
                        json.dumps(rag.get("not_for", []), ensure_ascii=False),
                        json.dumps(rag.get("decision_traps", []), ensure_ascii=False),
                        json.dumps(rag.get("neighbor_packages", []), ensure_ascii=False),
                        json.dumps(rag.get("workflow_position", []), ensure_ascii=False),
                        repo_relative(manifest_file, repo_root),
                        likely_summary_path(shard_dir, language, package, repo_root),
                        likely_raw_doc_path(shard_dir, language, package, repo_root),
                        json.dumps(manifest.get("source", {}), ensure_ascii=False),
                        json.dumps(manifest.get("version", {}), ensure_ascii=False),
                        json.dumps(manifest.get("status", {}), ensure_ascii=False),
                        json.dumps(manifest.get("content_presence", {}), ensure_ascii=False),
                        json.dumps(manifest, ensure_ascii=False),
                    )
                )

            doc_roots = [shard_dir / "raw_docs", shard_dir / "package_doc_collection"]
            for root in doc_roots:
                if not root.exists():
                    continue
                for path in sorted(root.rglob("*")):
                    if not path.is_file():
                        continue
                    if path.suffix.lower() not in {".md", ".json"}:
                        continue
                    if path.name == "shard_manifest.json":
                        continue
                    if path.suffix.lower() == ".json" and not path.name.endswith(".meta.json"):
                        continue
                    if path.suffix.lower() == ".md":
                        header, body, full_text = load_text_record(path)
                    else:
                        full_text = path.read_text(encoding="utf-8").strip()
                        header = {}
                        body = full_text
                    language, package, canonical = infer_doc_context(path, header)
                    source_kind = classify_source_kind(path)
                    doc_type = header.get("TYPE") or ("raw_meta" if source_kind == "raw_meta" else "raw_doc" if source_kind == "raw_doc" else "document")
                    title = header.get("TITLE") or first_heading(full_text) or path.stem
                    document_rows.append(
                        (
                            sha256_text(repo_relative(path, repo_root)),
                            task_manifest.get("task_id"),
                            shard_manifest.get("shard_id"),
                            language,
                            package,
                            canonical,
                            source_kind,
                            doc_type,
                            header.get("CHUNK_TYPE", ""),
                            header.get("IMPORTANCE_TIER", ""),
                            title,
                            header.get("FUNCTION_OR_COMMAND", ""),
                            header.get("SECTION_TITLE", ""),
                            header.get("RETRIEVAL_PRIORITY", ""),
                            header.get("ROLE_CLASS", ""),
                            header.get("AGENT_SAFETY_CLASS", ""),
                            json.dumps(split_csvish(header.get("KEYWORDS")), ensure_ascii=False),
                            json.dumps(split_csvish(header.get("TASK_TAGS")), ensure_ascii=False),
                            json.dumps(split_csvish(header.get("TOP_FUNCTIONS_OR_COMMANDS")), ensure_ascii=False),
                            repo_relative(path, repo_root),
                            header.get("OPEN_DOC_URL", ""),
                            json.dumps(header, ensure_ascii=False),
                            body,
                            full_text,
                        )
                    )

    if comparisons_root and comparisons_root.exists():
        comparison_task_id = "00_comparisons"
        comparison_manifest = load_json(comparisons_root / "shard_manifest.json")
        task_rows.append(
            (
                comparison_task_id,
                "Shared comparisons shard",
                "shared",
                0,
                0,
                1,
                "package_methods_top50_sync_safe",
                False,
                repo_relative(comparisons_root, repo_root),
                json.dumps({"task_id": comparison_task_id, "shards": [comparison_manifest]}, ensure_ascii=False),
            )
        )
        shard_rows.append(
            (
                comparison_task_id,
                comparison_manifest.get("shard_id"),
                comparison_manifest.get("label"),
                "shared",
                0,
                comparison_manifest.get("package_count", 0),
                comparison_manifest.get("file_count"),
                comparison_manifest.get("total_bytes"),
                comparison_manifest.get("approx_token_estimate"),
                bool(comparison_manifest.get("contains_comparisons", True)),
                False,
                comparison_manifest.get("content_digest_sha256"),
                repo_relative(comparisons_root, repo_root),
                json.dumps(comparison_manifest, ensure_ascii=False),
            )
        )
        for path in sorted((comparisons_root / "package_doc_collection").rglob("*.md")):
            header, body, full_text = load_text_record(path)
            language, package, canonical = infer_doc_context(path, header)
            document_rows.append(
                (
                    sha256_text(repo_relative(path, repo_root)),
                    comparison_task_id,
                    comparison_manifest.get("shard_id"),
                    language or "shared",
                    package,
                    canonical,
                    "comparison_card",
                    header.get("TYPE", "comparison_card"),
                    header.get("CHUNK_TYPE", ""),
                    header.get("IMPORTANCE_TIER", ""),
                    header.get("TITLE") or first_heading(full_text) or path.stem,
                    header.get("FUNCTION_OR_COMMAND", ""),
                    header.get("SECTION_TITLE", ""),
                    header.get("RETRIEVAL_PRIORITY", ""),
                    header.get("ROLE_CLASS", ""),
                    header.get("AGENT_SAFETY_CLASS", ""),
                    json.dumps(split_csvish(header.get("KEYWORDS")), ensure_ascii=False),
                    json.dumps(split_csvish(header.get("TASK_TAGS")), ensure_ascii=False),
                    json.dumps(split_csvish(header.get("TOP_FUNCTIONS_OR_COMMANDS")), ensure_ascii=False),
                    repo_relative(path, repo_root),
                    header.get("OPEN_DOC_URL", ""),
                    json.dumps(header, ensure_ascii=False),
                    body,
                    full_text,
                )
            )

    return task_rows, shard_rows, package_rows, document_rows


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    args.output_db.parent.mkdir(parents=True, exist_ok=True)
    if args.output_db.exists():
        args.output_db.unlink()

    task_rows, shard_rows, package_rows, document_rows = build_rows(args)

    con = duckdb.connect(str(args.output_db))
    try:
        con.execute(args.schema_sql.read_text(encoding="utf-8"))
        con.executemany(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            task_rows,
        )
        con.executemany(
            "INSERT INTO shards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            shard_rows,
        )
        con.executemany(
            "INSERT INTO packages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            package_rows,
        )
        con.executemany(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            document_rows,
        )

        con.execute("CREATE INDEX IF NOT EXISTS packages_lang_pkg_idx ON packages(language, package)")
        con.execute("CREATE INDEX IF NOT EXISTS docs_lang_pkg_idx ON documents(language, package)")
        con.execute("CREATE INDEX IF NOT EXISTS docs_doc_type_idx ON documents(doc_type)")

        summary = {
            "schema_version": 1,
            "collection_root": repo_relative(args.collection_root, repo_root),
            "comparisons_root": repo_relative(args.comparisons_root, repo_root) if args.comparisons_root.exists() else "",
            "output_db": repo_relative(args.output_db, repo_root),
            "task_count": len(task_rows),
            "shard_count": len(shard_rows),
            "package_count": len(package_rows),
            "document_count": len(document_rows),
            "db_sha256": sha256_text(args.output_db.read_bytes().hex()),
        }
        summary_path = args.output_db.with_suffix(".summary.json")
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
