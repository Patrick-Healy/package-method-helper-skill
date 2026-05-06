#!/usr/bin/env python3
"""Resolve and fetch methods paper landing pages for R, Python, and Stata packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from acquire_official_package_docs import (
    _first_heading,
    _follow_meta_refresh_if_needed,
    _http_get,
    _norm_text,
    build_document_content,
)

KNOWN_PAPER_URLS: dict[tuple[str, str], list[dict[str, str]]] = {
    ("r", "matchit"): [
        {
            "url": "https://www.jstatsoft.org/article/view/v042i08",
            "title": "MatchIt: Nonparametric preprocessing for parametric causal inference",
            "source_type": "software_paper",
            "notes": "JSS article page",
        }
    ],
    ("r", "plm"): [
        {
            "url": "https://www.jstatsoft.org/article/view/v027i02",
            "title": "plm: Linear Models for Panel Data in R",
            "source_type": "software_paper",
            "notes": "JSS article page",
        }
    ],
    ("r", "fixest"): [
        {
            "url": "https://arxiv.org/abs/2601.21749",
            "title": "Fast and user-friendly econometrics estimations: The R package fixest",
            "source_type": "software_paper",
            "notes": "arXiv abstract page",
        }
    ],
    ("r", "lavaan"): [
        {
            "url": "https://www.jstatsoft.org/article/view/v048i02",
            "title": "lavaan: An R Package for Structural Equation Modeling",
            "source_type": "software_paper",
            "notes": "JSS article page",
        }
    ],
    ("python", "doubleml"): [
        {
            "url": "https://www.jmlr.org/papers/v23/21-0862.html",
            "title": "DoubleML - An Object-Oriented Implementation of Double Machine Learning in Python",
            "source_type": "software_paper",
            "notes": "JMLR article page",
        }
    ],
    ("python", "statsmodels"): [
        {
            "url": "https://proceedings.scipy.org/articles/Majora-92bf1922-011",
            "title": "Statsmodels: Econometric and Statistical Modeling with Python",
            "source_type": "software_paper",
            "notes": "SciPy proceedings article page",
        }
    ],
    ("python", "pymc"): [
        {
            "url": "https://www.jstatsoft.org/article/view/v024i03",
            "title": "PyMC: Bayesian Stochastic Modelling in Python",
            "source_type": "software_paper",
            "notes": "JSS article page",
        }
    ],
    ("stata", "boottest"): [
        {
            "url": "https://ideas.repec.org/a/tsj/stataj/v19y2019i1p4-60.html",
            "title": "Fast and wild: Bootstrap inference in Stata using boottest",
            "source_type": "methods_paper",
            "notes": "Stata Journal abstract page",
        }
    ],
}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_output = script_dir.parents[2] / "work" / "generated" / "paper_acquisition"
    parser = argparse.ArgumentParser(description="Resolve and fetch methods paper landing pages.")
    parser.add_argument("--language", required=True, choices=("r", "python", "stata"))
    parser.add_argument("--package", required=True)
    parser.add_argument("--paper-url", default="", help="Manual paper URL override.")
    parser.add_argument("--paper-title", default="", help="Optional manual title override.")
    parser.add_argument("--paper-source-type", default="", choices=("", "software_paper", "methods_paper"))
    parser.add_argument("--output-root", type=Path, default=default_output)
    parser.add_argument("--resolve-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _rank_paper_candidate(url: str) -> tuple[int, str]:
    url_low = url.lower()
    if "jstatsoft.org/article/view/" in url_low:
        return (0, url_low)
    if "jmlr.org/papers/" in url_low:
        return (1, url_low)
    if "joss.theoj.org/papers/" in url_low:
        return (2, url_low)
    if "ideas.repec.org/" in url_low:
        return (3, url_low)
    if "arxiv.org/abs/" in url_low:
        return (2, url_low)
    if "/doi/" in url_low or "doi.org/" in url_low:
        return (5, url_low)
    return (9, url_low)


def _classify_capture_scope(fetched_url: str, markdown: str) -> str:
    url_low = fetched_url.lower()
    markdown_low = markdown.lower()
    if url_low.endswith(".pdf"):
        return "pdf_source"
    if "arxiv.org/abs/" in url_low:
        return "abstract_page"
    if "ideas.repec.org/" in url_low:
        return "abstract_page"
    if "jstatsoft.org/article/view/" in url_low or "jmlr.org/papers/" in url_low:
        if "abstract" in markdown_low and len(markdown) < 15000:
            return "landing_page"
        return "long_form_html"
    if len(markdown) >= 15000:
        return "long_form_html"
    return "landing_page"


def _extract_meta_content(raw_html: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_html, re.IGNORECASE)
        if match:
            return _norm_text(match.group(1))
    return ""


def _host_specific_markdown(final_url: str, raw_html: str) -> tuple[str, str] | None:
    parsed = urlparse(final_url)
    if parsed.netloc.lower().endswith("arxiv.org") and "/abs/" in parsed.path.lower():
        title = _extract_meta_content(raw_html, "citation_title") or _extract_meta_content(raw_html, "og:title")
        abstract = _extract_meta_content(raw_html, "citation_abstract") or _extract_meta_content(raw_html, "description")
        authors = re.findall(r'<meta[^>]+name=["\']citation_author["\'][^>]+content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
        date = _extract_meta_content(raw_html, "citation_date")
        lines = []
        if title:
            lines.extend([f"# {title}", ""])
        if abstract:
            lines.extend(["## Abstract", "", abstract, ""])
        details: list[str] = []
        if authors:
            details.append(f"- Authors: {', '.join(_norm_text(item) for item in authors if _norm_text(item))}")
        if date:
            details.append(f"- Published: {date}")
        details.append(f"- Host: {parsed.netloc}")
        lines.extend(["## Bibliographic Details", ""])
        lines.extend(details)
        return title or "arXiv paper", "\n".join(lines).strip()
    return None


def resolve_paper_sources(language: str, package: str, paper_url: str = "", paper_title: str = "", paper_source_type: str = "") -> dict[str, Any]:
    package_norm = _norm_text(package)
    language_norm = _norm_text(language).lower()
    candidates: list[dict[str, str]] = []
    if _norm_text(paper_url):
        candidates.append(
            {
                "url": _norm_text(paper_url),
                "title": _norm_text(paper_title),
                "source_type": _norm_text(paper_source_type) or "methods_paper",
                "notes": "manual override",
            }
        )
    candidates.extend(KNOWN_PAPER_URLS.get((language_norm, package_norm.lower()), []))
    seen: set[str] = set()
    ordered: list[dict[str, str]] = []
    for row in sorted(candidates, key=lambda item: _rank_paper_candidate(item.get("url", ""))):
        url = _norm_text(row.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        ordered.append(
            {
                "url": url,
                "title": _norm_text(row.get("title")),
                "source_type": _norm_text(row.get("source_type")) or "methods_paper",
                "notes": _norm_text(row.get("notes")),
            }
        )
    return {"language": language_norm, "package": package_norm, "paper_candidates": ordered}


def _fetch_paper(candidates: list[dict[str, str]], language: str, package: str) -> tuple[dict[str, Any], str]:
    errors: list[dict[str, str]] = []
    for candidate in candidates:
        url = candidate["url"]
        try:
            text, content_type, final_url = _http_get(url)
            text, final_url = _follow_meta_refresh_if_needed(text, content_type, final_url)
            host_specific = _host_specific_markdown(final_url, text)
            if host_specific:
                title, body = host_specific
                markdown = f"# {title}\n\nSource: {final_url}\n\n---\n\n{body}\n"
                code_block_count = 0
                code_languages: list[str] = []
            else:
                suffix = Path(final_url).suffix or Path(url).suffix or ".html"
                content = build_document_content(text, suffix, default_language=language, source_url=final_url)
                title = _first_heading(content["markdown_body"]) or _norm_text(candidate.get("title")) or f"{package} methods paper"
                markdown = f"# {title}\n\nSource: {final_url}\n\n---\n\n{content['markdown_body']}\n"
                code_block_count = content["code_block_count"]
                code_languages = content["code_languages"]
            meta = {
                "selected_url": url,
                "fetched_url": final_url,
                "title": title,
                "content_type": content_type,
                "source_type": _norm_text(candidate.get("source_type")) or "methods_paper",
                "capture_scope": _classify_capture_scope(final_url, markdown),
                "markdown_chars": len(markdown),
                "code_block_count": code_block_count,
                "code_languages": code_languages,
                "sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            }
            return meta, markdown
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
    raise RuntimeError(f"Unable to fetch any paper candidate for {language}::{package}: {errors}")


def write_outputs(output_root: Path, manifest: dict[str, Any], markdown: str | None, meta: dict[str, Any] | None) -> Path:
    outdir = output_root / manifest["language"] / manifest["package"]
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "paper_source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if markdown is not None and meta is not None:
        (outdir / "paper_source.md").write_text(markdown)
        (outdir / "paper_source.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return outdir


def main() -> int:
    args = parse_args()
    resolved = resolve_paper_sources(
        args.language,
        args.package,
        paper_url=args.paper_url,
        paper_title=args.paper_title,
        paper_source_type=args.paper_source_type,
    )
    if not resolved["paper_candidates"]:
        raise SystemExit(f"No paper candidates known for {args.language}::{args.package}. Pass --paper-url.")

    manifest: dict[str, Any] = {
        "workflow_version": "1.0",
        "package": resolved["package"],
        "language": resolved["language"],
        "resolved_at_utc": _utc_now(),
        "paper_url_override_used": bool(_norm_text(args.paper_url)),
        "source_resolution": {"paper_candidates": resolved["paper_candidates"]},
    }

    markdown: str | None = None
    meta: dict[str, Any] | None = None
    if not args.resolve_only:
        meta, markdown = _fetch_paper(resolved["paper_candidates"], resolved["language"], resolved["package"])
        manifest["selected_paper_url"] = meta["fetched_url"]
        manifest["paper_source_type"] = meta["source_type"]
        manifest["paper_capture_scope"] = meta["capture_scope"]
        manifest["paper"] = {
            "title": meta["title"],
            "content_type": meta["content_type"],
            "capture_scope": meta["capture_scope"],
            "markdown_chars": meta["markdown_chars"],
            "code_block_count": meta["code_block_count"],
            "code_languages": meta["code_languages"],
            "sha256": meta["sha256"],
        }

    outdir = write_outputs(args.output_root, manifest, markdown, meta)
    if args.json:
        print(json.dumps({"status": "ok", "output_dir": str(outdir), "manifest": manifest}, indent=2))
    else:
        print(f"Wrote paper acquisition bundle to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
