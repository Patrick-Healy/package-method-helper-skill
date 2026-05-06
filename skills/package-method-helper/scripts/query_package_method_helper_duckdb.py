#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
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
EXACT_PACKAGE_DOC_BOOSTS = {
    "summary_card": 40,
    "decision_card": 30,
    "function_card": 20,
    "function_documentation": 15,
}
FOLLOW_UP_DOC_TYPE_ORDER = {
    "summary_card": 0,
    "decision_card": 1,
    "package_overview": 2,
    "paper_note": 3,
    "function_card": 4,
    "function_documentation": 5,
    "empirical_pattern": 6,
    "raw_meta": 7,
    "documentation": 8,
    "raw_doc": 9,
    "comparison_card": 10,
}
PACKAGE_LANGUAGE_HINTS = {
    "fixest": "r",
    "aer": "r",
    "plm": "r",
    "lme4": "r",
    "survival": "r",
    "lavaan": "r",
    "matchit": "r",
    "synth": "r",
    "rdrobust": "r",
    "psych": "r",
    "quanteda": "r",
    "dplyr": "r",
    "tidyr": "r",
    "data.table": "r",
    "readr": "r",
    "haven": "r",
    "ggplot2": "r",
    "glmnet": "r",
    "reghdfe": "stata",
    "ivreghdfe": "stata",
    "ivreg2": "stata",
    "csdid": "stata",
    "drdid": "stata",
    "did_multiplegt": "stata",
    "did_imputation": "stata",
    "bacondecomp": "stata",
    "scpi": "stata",
    "sdid": "stata",
    "rddensity": "stata",
    "psmatch2": "stata",
    "ebalance": "stata",
    "boottest": "stata",
    "ritest": "stata",
    "winsor2": "stata",
    "esttab": "stata",
    "estout": "stata",
    "outreg2": "stata",
    "coefplot": "stata",
    "asdoc": "stata",
    "regsave": "stata",
    "binscatter": "stata",
    "ddml": "stata",
    "xtabond2": "stata",
    "acreg": "stata",
    "econml": "python",
    "dowhy": "python",
    "causallib": "python",
    "doubleml": "python",
    "linearmodels": "python",
    "statsmodels": "python",
    "lifelines": "python",
    "svy": "python",
    "spreg": "python",
    "geopandas": "python",
    "libpysal": "python",
    "esda": "python",
    "sklearn": "python",
    "scikit-learn": "python",
    "scipy": "python",
    "pymc": "python",
    "pandas": "python",
    "numpy": "python",
    "xarray": "python",
    "dask": "python",
    "joblib": "python",
    "tqdm": "python",
    "miceforest": "python",
    "nltk": "python",
    "gensim": "python",
    "transformers": "python",
    "sentence_transformers": "python",
    "matplotlib": "python",
    "seaborn": "python",
    "plotly": "python",
    "plotnine": "python",
    "bs4": "python",
    "beautifulsoup4": "python",
    "requests": "python",
    "lxml": "python",
    "eurostat": "python",
    "torch": "python",
    "tensorflow": "python",
    "cv2": "python",
    "moviepy": "python",
    "numba": "python",
    "cvxopt": "python",
}
LANGUAGE_PATTERNS = {
    "r": [
        re.compile(r"\bin r\b", re.IGNORECASE),
        re.compile(r"\br code\b", re.IGNORECASE),
        re.compile(r"\blibrary\s*\(", re.IGNORECASE),
        re.compile(r"<-"),
        re.compile(r"\.(r|rmd|qmd)\b", re.IGNORECASE),
        re.compile(r"\bfeols\b", re.IGNORECASE),
    ],
    "stata": [
        re.compile(r"\bin stata\b", re.IGNORECASE),
        re.compile(r"\bssc install\b", re.IGNORECASE),
        re.compile(r"\bdo[- ]file\b", re.IGNORECASE),
        re.compile(r"\.(do|ado)\b", re.IGNORECASE),
        re.compile(r"(^|\s)gen\s+[A-Za-z_]", re.IGNORECASE),
    ],
    "python": [
        re.compile(r"\bin python\b", re.IGNORECASE),
        re.compile(r"\bpython code\b", re.IGNORECASE),
        re.compile(r"\bimport\s+[A-Za-z_]", re.IGNORECASE),
        re.compile(r"\bpd\.", re.IGNORECASE),
        re.compile(r"\bnp\.", re.IGNORECASE),
        re.compile(r"\bpip(?:3)?\b", re.IGNORECASE),
        re.compile(r"\.(py|ipynb)\b", re.IGNORECASE),
    ],
}


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
    parser.add_argument("--allow-cross-language", action="store_true", help="Permit cross-language search when you explicitly want broad similarity search.")
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


def load_json_object(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def language_candidates_from_tokens(tokens: list[str]) -> set[str]:
    candidates: set[str] = set()
    for token in tokens:
        variants = {token}
        if "::" in token:
            variants.add(token.split("::", 1)[0])
            variants.add(token.split("::", 1)[1])
        if "." in token:
            variants.add(token.split(".", 1)[0])
        for variant in variants:
            language = PACKAGE_LANGUAGE_HINTS.get(variant)
            if language:
                candidates.add(language)
    return candidates


def detect_language(package: str | None, query: str) -> tuple[str | None, str]:
    package_norm = norm(package)
    if package_norm:
        package_language = PACKAGE_LANGUAGE_HINTS.get(package_norm)
        if package_language:
            return package_language, "package_hint"

    query_text = query or ""
    query_tokens = tokenize(query_text)
    token_languages = language_candidates_from_tokens(query_tokens)
    if len(token_languages) == 1:
        return next(iter(token_languages)), "query_package_hint"
    if len(token_languages) > 1:
        return None, "ambiguous_package_hints"

    scores = {
        language: sum(1 for pattern in patterns if pattern.search(query_text))
        for language, patterns in LANGUAGE_PATTERNS.items()
    }
    nonzero = {language: score for language, score in scores.items() if score > 0}
    if len(nonzero) == 1:
        language, score = next(iter(nonzero.items()))
        return language, f"syntax_hint:{score}"
    if nonzero:
        ordered = sorted(nonzero.items(), key=lambda item: item[1], reverse=True)
        if len(ordered) == 1 or ordered[0][1] > ordered[1][1]:
            return ordered[0][0], f"syntax_hint:{ordered[0][1]}"
        return None, "ambiguous_syntax_hints"

    return None, "no_language_signal"


def resolve_effective_language(args: argparse.Namespace) -> tuple[str | None, str]:
    if args.language:
        return args.language, "explicit"
    if args.allow_cross_language:
        return None, "cross_language_allowed"
    inferred, source = detect_language(args.package, args.query)
    return inferred, source


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


def package_matches_requested(row: dict[str, Any], requested_package: str | None) -> bool:
    requested_norm = norm(requested_package)
    if not requested_norm:
        return True
    candidates = [
        norm(row.get("package")),
        norm(row.get("canonical_package_name")),
        *[norm(v) for v in load_json_field(row.get("aliases"))],
        *[norm(v) for v in load_json_field(row.get("query_aliases"))],
    ]
    return requested_norm in {candidate for candidate in candidates if candidate}


def package_identity_keys(package_row: dict[str, Any]) -> set[str]:
    keys = {
        norm(package_row.get("package")),
        norm(package_row.get("canonical_package_name")),
    }
    keys.update(norm(v) for v in load_json_field(package_row.get("aliases")))
    keys.update(norm(v) for v in load_json_field(package_row.get("query_aliases")))
    return {key for key in keys if key}


def document_matches_package(row: dict[str, Any], package_keys: set[str]) -> bool:
    candidates = {
        norm(row.get("package")),
        norm(row.get("canonical_package_name")),
    }
    return any(candidate in package_keys for candidate in candidates if candidate)


def summarize_document_edge(row: dict[str, Any], query: str) -> dict[str, Any]:
    text = row.get("body_text") or row.get("full_text") or ""
    return {
        "doc_type": row.get("doc_type"),
        "title": row.get("title"),
        "function_or_command": row.get("function_or_command") or "",
        "section_title": row.get("section_title") or "",
        "path": row.get("path"),
        "open_doc_url": row.get("open_doc_url") or "",
        "role_class": row.get("role_class") or "",
        "agent_safety_class": row.get("agent_safety_class") or "",
        "task_tags": load_json_field(row.get("task_tags")),
        "top_functions_or_commands": load_json_field(row.get("top_functions_or_commands")),
        "score": row.get("score", 0.0),
        "snippet": snippet(text, query),
    }


def follow_up_doc_sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    return (
        FOLLOW_UP_DOC_TYPE_ORDER.get(norm(row.get("doc_type")), 99),
        -float(row.get("score", 0.0)),
        norm(row.get("title")),
    )


def build_adjacent_package_edges(
    package_row: dict[str, Any],
    package_lookup_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    language = norm(package_row.get("language"))
    package_name = norm(package_row.get("package"))
    candidates = [
        *load_json_field(package_row.get("common_pairings")),
        *load_json_field(package_row.get("neighbor_packages")),
    ]
    candidate_keys = [norm(value) for value in candidates if norm(value)]
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidate_keys:
        for row in package_lookup_rows:
            if norm(row.get("language")) != language:
                continue
            if norm(row.get("package")) == package_name:
                continue
            row_keys = package_identity_keys(row)
            if candidate not in row_keys:
                continue
            row_package = norm(row.get("package"))
            if row_package in seen:
                continue
            seen.add(row_package)
            edges.append(
                {
                    "package": row.get("package"),
                    "canonical_package_name": row.get("canonical_package_name"),
                    "role_class": row.get("role_class"),
                    "agent_safety_class": row.get("agent_safety_class"),
                    "task_tags": load_json_field(row.get("task_tags")),
                    "summary_card_path": row.get("summary_card_path"),
                    "manifest_path": row.get("manifest_path"),
                }
            )
            break
    return edges


def build_follow_up(
    package_row: dict[str, Any] | None,
    package_lookup_rows: list[dict[str, Any]],
    scored_document_rows: list[dict[str, Any]],
    query: str,
) -> dict[str, Any] | None:
    if not package_row:
        return None

    package_keys = package_identity_keys(package_row)
    package_docs = [row for row in scored_document_rows if document_matches_package(row, package_keys)]
    package_docs.sort(key=follow_up_doc_sort_key)

    core_documents = [
        summarize_document_edge(row, query)
        for row in package_docs
        if norm(row.get("doc_type")) in {"summary_card", "decision_card", "package_overview", "paper_note", "empirical_pattern"}
    ][:8]
    function_edges = [
        summarize_document_edge(row, query)
        for row in package_docs
        if norm(row.get("doc_type")) in {"function_card", "function_documentation"}
    ][:8]
    raw_meta_edges = []
    for row in package_docs:
        if norm(row.get("doc_type")) != "raw_meta":
            continue
        meta = load_json_object(row.get("full_text"))
        raw_meta_edges.append(
            {
                "path": row.get("path"),
                "source_url": meta.get("source_url", ""),
                "package_homepage": meta.get("version_metadata", {}).get("upstream", {}).get("package_homepage", ""),
                "latest_upstream_version": meta.get("version_metadata", {}).get("upstream", {}).get("latest_upstream_version", ""),
                "latest_upstream_release_date": meta.get("version_metadata", {}).get("upstream", {}).get("latest_upstream_release_date", ""),
                "maintenance_status": meta.get("maintenance", {}).get("status", ""),
                "maintainer": meta.get("version_metadata", {}).get("upstream", {}).get("maintainer", ""),
            }
        )
        if len(raw_meta_edges) >= 2:
            break

    content_presence = load_json_object(package_row.get("content_presence_json"))
    gaps = []
    for key in ("summary_card", "decision_card", "documentation_chunks", "raw_meta"):
        if content_presence.get(key) is False:
            gaps.append(key)
    if int(content_presence.get("function_card_count", 0) or 0) == 0:
        gaps.append("function_cards")
    if int(content_presence.get("function_documentation_count", 0) or 0) == 0:
        gaps.append("function_documentation")

    package_context = {
        "language": package_row.get("language"),
        "package": package_row.get("package"),
        "canonical_package_name": package_row.get("canonical_package_name"),
        "role_class": package_row.get("role_class"),
        "agent_safety_class": package_row.get("agent_safety_class"),
        "selection_priority": package_row.get("selection_priority"),
        "retrieval_priority": package_row.get("retrieval_priority"),
        "aliases": load_json_field(package_row.get("aliases")),
        "query_aliases": load_json_field(package_row.get("query_aliases")),
        "task_tags": load_json_field(package_row.get("task_tags")),
        "choose_when": load_json_field(package_row.get("choose_when")),
        "avoid_when": load_json_field(package_row.get("avoid_when")),
        "not_for": load_json_field(package_row.get("not_for")),
        "decision_traps": load_json_field(package_row.get("decision_traps")),
        "common_pairings": load_json_field(package_row.get("common_pairings")),
        "neighbor_packages": load_json_field(package_row.get("neighbor_packages")),
        "top_functions_or_commands": load_json_field(package_row.get("top_functions_or_commands")),
        "workflow_position": load_json_field(package_row.get("workflow_position")),
        "source": load_json_object(package_row.get("source_json")),
        "version": load_json_object(package_row.get("version_json")),
        "status": load_json_object(package_row.get("status_json")),
        "content_presence": content_presence,
        "paths": {
            "manifest_path": package_row.get("manifest_path"),
            "summary_card_path": package_row.get("summary_card_path"),
            "raw_doc_path": package_row.get("raw_doc_path"),
        },
    }

    return {
        "package_context": package_context,
        "core_documents": core_documents,
        "function_edges": function_edges,
        "raw_meta_edges": raw_meta_edges,
        "adjacent_packages": build_adjacent_package_edges(package_row, package_lookup_rows),
        "gaps": sorted(set(gaps)),
    }


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
            score += EXACT_PACKAGE_DOC_BOOSTS.get(norm(row.get("doc_type")), 0)
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


def fill_document_metadata_from_package(row: dict[str, Any], package_lookup: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    key = (norm(row.get("language")), norm(row.get("package") or row.get("canonical_package_name")))
    package_row = package_lookup.get(key)
    if not package_row:
        return row

    for field in ("role_class", "agent_safety_class", "retrieval_priority", "canonical_package_name"):
        if not norm(row.get(field)):
            row[field] = package_row.get(field)

    for doc_field, package_field in (
        ("task_tags", "task_tags"),
        ("top_functions_or_commands", "top_functions_or_commands"),
    ):
        if not load_json_field(row.get(doc_field)):
            row[doc_field] = package_row.get(package_field)

    return row


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
    effective_language, language_gate = resolve_effective_language(args)
    if args.language and args.package:
        inferred, _ = detect_language(args.package, args.query)
        if inferred and inferred != args.language:
            print(
                json.dumps(
                    {
                        "error": "language_package_mismatch",
                        "message": f"Package '{args.package}' maps to language '{inferred}', not '{args.language}'.",
                    },
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2
    if not effective_language and not args.allow_cross_language:
        print(
            json.dumps(
                {
                    "error": "language_gate_failed",
                    "message": "Language gate could not resolve a single language. Pass --language explicitly or use --allow-cross-language.",
                    "package": args.package,
                    "query": args.query,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2

    con = duckdb.connect(str(args.db), read_only=True)
    try:
        package_rows: list[dict[str, Any]] = []
        document_rows: list[dict[str, Any]] = []
        follow_up: dict[str, Any] | None = None
        filters = []
        params: list[Any] = []
        if effective_language:
            filters.append("language = ?")
            params.append(effective_language)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        package_lookup_rows = rows_to_dicts(
            con,
            f"SELECT * FROM packages {where_clause}",
            params,
        )
        package_scope_names = {
            norm(row.get("package"))
            for row in package_lookup_rows
            if package_matches_requested(row, args.package)
        }

        if args.mode in {"packages", "both"}:
            package_rows = list(package_lookup_rows)
            if args.package:
                package_rows = [
                    row for row in package_rows
                    if norm(row.get("package")) in package_scope_names
                ]
            for row in package_rows:
                row["score"] = score_package(row, args.package, args.query)
            package_rows = [row for row in package_rows if row["score"] > 0 or args.package]
            package_rows.sort(key=lambda row: row["score"], reverse=True)
            package_rows = package_rows[: args.limit]

        package_lookup: dict[tuple[str, str], dict[str, Any]] = {}
        for row in package_lookup_rows:
            package_lookup[(norm(row.get("language")), norm(row.get("package")))] = row
            canonical = norm(row.get("canonical_package_name"))
            if canonical:
                package_lookup[(norm(row.get("language")), canonical)] = row

        if args.mode in {"documents", "both"}:
            all_document_rows = rows_to_dicts(
                con,
                f"SELECT * FROM documents {where_clause}",
                params,
            )
            if args.package:
                all_document_rows = [
                    row for row in all_document_rows
                    if norm(row.get("package")) in package_scope_names
                    or norm(row.get("canonical_package_name")) in package_scope_names
                ]
            for row in all_document_rows:
                fill_document_metadata_from_package(row, package_lookup)
                row["score"] = score_document(row, args.package, args.query)
            scored_document_rows = [row for row in all_document_rows if row["score"] > 0 or args.package]
            scored_document_rows.sort(key=lambda row: row["score"], reverse=True)
            top_package_row = package_rows[0] if package_rows else None
            follow_up = build_follow_up(top_package_row, package_lookup_rows, scored_document_rows, args.query)
            document_rows = scored_document_rows[: args.limit]

        if args.json:
            payload = {
                "db": str(args.db),
                "requested_language": args.language,
                "effective_language": effective_language,
                "language_gate": language_gate,
                "cross_language": args.allow_cross_language,
                "package": args.package,
                "query": args.query,
                "packages": package_rows,
                "documents": document_rows,
                "follow_up": follow_up,
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        print(f"DB: {args.db}")
        print(f"Language gate: {language_gate}")
        print(f"Effective language: {effective_language or 'cross-language'}")
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
        if follow_up:
            print("\nFollow-up context:")
            context = follow_up.get("package_context", {})
            print(
                f"  package={context.get('package')} role={context.get('role_class')} "
                f"safety={context.get('agent_safety_class')} retrieval={context.get('retrieval_priority')}"
            )
            if follow_up.get("core_documents"):
                print("  core docs:")
                for row in follow_up["core_documents"][:4]:
                    print(f"    - {row.get('doc_type')}: {row.get('path')}")
            if follow_up.get("adjacent_packages"):
                print("  adjacent packages:")
                for row in follow_up["adjacent_packages"][:4]:
                    print(f"    - {row.get('package')} [{row.get('role_class')}]")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
