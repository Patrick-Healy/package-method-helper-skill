#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import duckdb


TOKEN_RE = re.compile(r"[a-zA-Z0-9_:.+-]+")
PACKAGE_BOOSTS = {
    "flagship": 30,
    "preferred": 20,
    "specialized": 12,
    "fallback": 5,
    "avoid": -10,
}
DOC_TYPE_BOOSTS = {
    "summary_card": 90,
    "decision_card": 75,
    "function_card": 80,
    "function_documentation": 70,
    "package_overview": 60,
    "paper_note": 55,
    "empirical_pattern": 45,
    "documentation": 35,
    "raw_doc": 20,
    "comparison_card": 40,
}
IMPORTANCE_BOOSTS = {"t1": 30, "t2": 20, "t3": 10, "t4": 0}


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Query the Package Method Helper DuckDB index.")
    parser.add_argument(
        "--db",
        type=Path,
        default=repo_root / "work/generated/duckdb/package_method_helper.duckdb",
        help="DuckDB file created by the build script.",
    )
    parser.add_argument("--language", choices=["r", "python", "stata", "shared"], help="Restrict search to one language.")
    parser.add_argument("--package", help="Exact package name to prioritize.")
    parser.add_argument("--query", default="", help="Free-text query.")
    parser.add_argument("--mode", choices=["packages", "documents", "both"], default="both")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    return parser.parse_args()


def norm(text: Any) -> str:
    if text is None:
        return ""
    return str(text).strip().lower()


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "")]


def load_json_field(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    try:
        parsed = json.loads(value)
    except Exception:
        return [str(value)]
    if isinstance(parsed, list):
        return [str(v) for v in parsed]
    return [str(parsed)]


def score_package(row: dict[str, Any], package: str | None, query: str) -> float:
    score = 0.0
    query_norm = norm(query)
    package_norm = norm(package)
    package_name = norm(row.get("package"))
    canonical = norm(row.get("canonical_package_name"))
    aliases = [norm(v) for v in load_json_field(row.get("aliases")) + load_json_field(row.get("query_aliases"))]
    task_tags = [norm(v) for v in load_json_field(row.get("task_tags"))]
    top_functions = [norm(v) for v in load_json_field(row.get("top_functions_or_commands"))]
    choose_when = [norm(v) for v in load_json_field(row.get("choose_when"))]
    combined = " ".join(
        [
            package_name,
            canonical,
            " ".join(aliases),
            " ".join(task_tags),
            " ".join(top_functions),
            " ".join(choose_when),
            norm(row.get("role_class")),
            norm(row.get("agent_safety_class")),
        ]
    )
    if package_norm:
        if package_name == package_norm or canonical == package_norm:
            score += 200
        elif package_norm in aliases:
            score += 120
    if query_norm:
        for token in tokenize(query_norm):
            score += combined.count(token) * 8
            if token == package_name or token == canonical:
                score += 25
            if token in aliases:
                score += 18
            if token in top_functions:
                score += 16
            if token in task_tags:
                score += 12
    score += PACKAGE_BOOSTS.get(norm(row.get("selection_priority")), 0)
    if norm(row.get("retrieval_priority")) == "high":
        score += 12
    elif norm(row.get("retrieval_priority")) == "medium":
        score += 6
    return score


def score_document(row: dict[str, Any], package: str | None, query: str) -> float:
    score = 0.0
    query_terms = tokenize(query)
    package_norm = norm(package)
    package_name = norm(row.get("package"))
    canonical = norm(row.get("canonical_package_name"))
    title = norm(row.get("title"))
    function_name = norm(row.get("function_or_command"))
    section = norm(row.get("section_title"))
    keywords = [norm(v) for v in load_json_field(row.get("keywords"))]
    task_tags = [norm(v) for v in load_json_field(row.get("task_tags"))]
    top_functions = [norm(v) for v in load_json_field(row.get("top_functions_or_commands"))]
    haystack = " ".join(
        [
            package_name,
            canonical,
            title,
            function_name,
            section,
            " ".join(keywords),
            " ".join(task_tags),
            " ".join(top_functions),
            norm(row.get("body_text"))[:6000],
        ]
    )
    if package_norm:
        if package_name == package_norm or canonical == package_norm:
            score += 180
    for token in query_terms:
        score += haystack.count(token) * 4
        if token == function_name:
            score += 35
        if token == title:
            score += 20
        if token in keywords:
            score += 15
        if token in task_tags:
            score += 12
        if token in top_functions:
            score += 15
    score += DOC_TYPE_BOOSTS.get(norm(row.get("doc_type")), 10)
    score += IMPORTANCE_BOOSTS.get(norm(row.get("importance_tier")), 0)
    if norm(row.get("retrieval_priority")) == "high":
        score += 10
    elif norm(row.get("retrieval_priority")) == "medium":
        score += 5
    return score


def rows_to_dicts(cursor: duckdb.DuckDBPyConnection, query: str, params: list[Any]) -> list[dict[str, Any]]:
    result = cursor.execute(query, params)
    cols = [desc[0] for desc in result.description]
    return [dict(zip(cols, row)) for row in result.fetchall()]


def snippet(text: str, query: str, width: int = 180) -> str:
    stripped = re.sub(r"\s+", " ", text or "").strip()
    if not stripped:
        return ""
    terms = tokenize(query)
    if not terms:
        return stripped[:width]
    lower = stripped.lower()
    positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
    if not positions:
        return stripped[:width]
    start = max(0, min(positions) - width // 3)
    end = min(len(stripped), start + width)
    return stripped[start:end]


def main() -> int:
    args = parse_args()
    con = duckdb.connect(str(args.db), read_only=True)
    try:
        package_rows: list[dict[str, Any]] = []
        document_rows: list[dict[str, Any]] = []
        filters = []
        params: list[Any] = []
        if args.language:
            filters.append("language = ?")
            params.append(args.language)
        if args.package:
            filters.append("package = ?")
            params.append(args.package)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        if args.mode in {"packages", "both"}:
            package_rows = rows_to_dicts(
                con,
                f"SELECT * FROM packages {where_clause}",
                params,
            )
            for row in package_rows:
                row["score"] = score_package(row, args.package, args.query)
            package_rows = [row for row in package_rows if row["score"] > 0 or args.package]
            package_rows.sort(key=lambda row: row["score"], reverse=True)
            package_rows = package_rows[: args.limit]

        if args.mode in {"documents", "both"}:
            document_rows = rows_to_dicts(
                con,
                f"SELECT * FROM documents {where_clause}",
                params,
            )
            for row in document_rows:
                row["score"] = score_document(row, args.package, args.query)
            document_rows = [row for row in document_rows if row["score"] > 0 or args.package]
            document_rows.sort(key=lambda row: row["score"], reverse=True)
            document_rows = document_rows[: args.limit]

        if args.json:
            payload = {
                "db": str(args.db),
                "language": args.language,
                "package": args.package,
                "query": args.query,
                "packages": package_rows,
                "documents": document_rows,
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        print(f"DB: {args.db}")
        if args.mode in {"packages", "both"}:
            print("\nPackage hits:")
            if not package_rows:
                print("  (none)")
            for idx, row in enumerate(package_rows, 1):
                aliases = ", ".join(load_json_field(row.get("aliases"))[:4])
                print(f"  {idx}. {row.get('package')} [{row.get('language')}] score={row.get('score'):.1f}")
                print(f"     role={row.get('role_class')} safety={row.get('agent_safety_class')} retrieval={row.get('retrieval_priority')}")
                if aliases:
                    print(f"     aliases={aliases}")
                print(f"     manifest={row.get('manifest_path')}")
        if args.mode in {"documents", "both"}:
            print("\nDocument hits:")
            if not document_rows:
                print("  (none)")
            for idx, row in enumerate(document_rows, 1):
                print(
                    f"  {idx}. {row.get('doc_type')} :: {row.get('package') or '-'} :: {row.get('title')} "
                    f"[{row.get('language')}] score={row.get('score'):.1f}"
                )
                print(f"     path={row.get('path')}")
                text = row.get("body_text") or row.get("full_text") or ""
                excerpt = snippet(text, args.query)
                if excerpt:
                    print(f"     snippet={excerpt}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
