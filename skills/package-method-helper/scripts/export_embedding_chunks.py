#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import duckdb


ABSOLUTE_PATH_RE = re.compile(r"/Users/[^\s)]+")
PATH_HEADER_RE = re.compile(r"^\[[A-Z0-9_]*PATH\]\s+.*$", re.MULTILINE)
WHITESPACE_RE = re.compile(r"\s+")
EMBEDDING_LANGUAGES = ["r", "python", "stata"]


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Export safe chunk payloads for external embedding pipelines.")
    parser.add_argument(
        "--db",
        type=Path,
        default=repo_root / "work/generated/duckdb/package_method_helper.duckdb",
        help="DuckDB file created by the build script.",
    )
    parser.add_argument("--language", choices=EMBEDDING_LANGUAGES, required=True, help="Export one language at a time.")
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        required=True,
        help="JSONL file to write.",
    )
    parser.add_argument(
        "--output-manifest",
        type=Path,
        help="Optional manifest path. Defaults to <output-jsonl>.manifest.json.",
    )
    parser.add_argument(
        "--include-raw-docs",
        action="store_true",
        help="Include full raw docs in the export. Off by default because chunked/card layers are safer for embeddings.",
    )
    return parser.parse_args()


def scrub_text(text: str) -> str:
    text = ABSOLUTE_PATH_RE.sub("[SCRUBBED_PATH]", text or "")
    text = PATH_HEADER_RE.sub("", text)
    return text.strip()


def embedding_text_for_row(row: dict[str, Any]) -> str:
    body = row.get("body_text") or ""
    full = row.get("full_text") or ""
    doc_type = str(row.get("doc_type") or "")
    chunk_type = str(row.get("chunk_type") or "")

    text = body or full

    # Function cards in this corpus often append a full help page after a divider.
    # For embeddings, the concise pre-divider guidance is the higher-signal text.
    if doc_type == "function_card" and "\n---\n" in text:
        text = text.split("\n---\n", 1)[0].strip()

    # Function documentation can still be long because some packages expose
    # very large help pages as single entry-point docs. Keep the high-signal
    # front section and bound the payload for embeddings.
    if doc_type == "function_documentation" and len(text) > 12000:
        text = text[:12000]

    # Comparison cards can be verbose. Keep them compact and deterministic.
    if doc_type == "comparison_card":
        text = text[:8000]

    # Fallback guard for any unusually large item that still passed export filters.
    if len(text) > 14000:
        text = text[:14000]

    return scrub_text(text)


def load_json_field(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        return [str(value)]
    if isinstance(parsed, list):
        return [str(v) for v in parsed]
    return [str(parsed)]


def text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    args = parse_args()
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_manifest = args.output_manifest or args.output_jsonl.with_suffix(args.output_jsonl.suffix + ".manifest.json")

    con = duckdb.connect(str(args.db), read_only=True)
    try:
        query = """
            SELECT *
            FROM documents
            WHERE source_kind <> 'raw_meta'
              AND doc_type <> 'raw_meta'
        """
        params: list[Any] = []
        if not args.include_raw_docs:
            query += " AND source_kind <> 'raw_doc' AND doc_type <> 'raw_doc'"
        query += " AND language = ?"
        params.append(args.language)
        rows = con.execute(query, params).fetchdf().to_dict("records")
    finally:
        con.close()

    records = []
    for row in rows:
        text = embedding_text_for_row(row)
        if not text:
            continue
        record = {
            "id": row.get("doc_id"),
            "language": row.get("language"),
            "package": row.get("package"),
            "canonical_package_name": row.get("canonical_package_name"),
            "doc_type": row.get("doc_type"),
            "chunk_type": row.get("chunk_type") or row.get("doc_type"),
            "importance_tier": row.get("importance_tier") or "",
            "title": row.get("title") or "",
            "function_or_command": row.get("function_or_command") or "",
            "section_title": row.get("section_title") or "",
            "task_tags": load_json_field(row.get("task_tags")),
            "top_functions_or_commands": load_json_field(row.get("top_functions_or_commands")),
            "retrieval_priority": row.get("retrieval_priority") or "",
            "role_class": row.get("role_class") or "",
            "agent_safety_class": row.get("agent_safety_class") or "",
            "source_kind": row.get("source_kind") or "",
            "text": text,
            "text_sha256": text_digest(text),
        }
        records.append(record)

    with args.output_jsonl.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": 1,
        "db": str(args.db),
        "language": args.language,
        "record_count": len(records),
        "output_jsonl": str(args.output_jsonl),
        "output_jsonl_sha256": text_digest(args.output_jsonl.read_text(encoding="utf-8")),
        "notes": [
            "Safe export for external embedding pipelines.",
            "Absolute local paths and PATH headers are scrubbed from the text payload.",
            "Full raw docs are excluded by default; use --include-raw-docs to export them explicitly.",
        ],
    }
    output_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
