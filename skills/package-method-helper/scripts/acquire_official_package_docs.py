#!/usr/bin/env python3
"""Resolve and fetch official package documentation for R, Python, and Stata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

USER_AGENT = "package-method-helper-doc-acquisition/1.0"
TIMEOUT_SEC = 20.0
SKIP_HTML_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "button", "svg"}
BLOCK_HTML_TAGS = {
    "article", "blockquote", "br", "dd", "div", "dl", "dt", "li", "main", "ol", "p", "section",
    "table", "tbody", "td", "th", "thead", "tr", "ul",
}
HTML_NOISE_LINES = {
    "/", "home", "menu", "search", "skip to content", "skip to main content", "sign in", "log in",
    "privacy policy", "terms of use",
}
HEADING_TAGS = {f"h{level}": level for level in range(1, 7)}
FENCE_LINE_RE = re.compile(r"^```([\w.+-]+)?(?:\s+.*)?$")
FENCED_BLOCK_RE = re.compile(r"```([\w.+-]*)[^\n]*\n(.*?)\n```", re.S)
RST_CODE_DIRECTIVE_RE = re.compile(r"^\.\.\s+(?:code-block|sourcecode)::\s*([\w.+-]*)\s*$", re.I)
GIT_HOSTS = {"github.com", "gitlab.com", "bitbucket.org", "codeberg.org"}
DOC_URL_KEYS = ("doc", "document", "readthedocs", "manual", "reference", "homepage", "home")
REPO_URL_KEYS = ("source", "repo", "repository", "code", "github", "gitlab")
IGNORE_PYPI_URL_KEYS = ("issue", "tracker", "changelog", "download", "release")
STATA_DOC_SUFFIXES = (".sthlp", ".hlp", ".txt", ".pdf")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_output = script_dir.parents[2] / "work" / "generated" / "source_acquisition"
    parser = argparse.ArgumentParser(description="Resolve and fetch official package docs.")
    parser.add_argument("--language", required=True, choices=("r", "python", "stata"))
    parser.add_argument("--package", required=True)
    parser.add_argument("--output-root", type=Path, default=default_output)
    parser.add_argument("--doc-url", default="", help="Optional manual override for the primary documentation URL.")
    parser.add_argument("--resolve-only", action="store_true", help="Resolve sources but do not fetch docs.")
    parser.add_argument("--json", action="store_true", help="Print the acquisition manifest as JSON.")
    return parser.parse_args()


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _decode_text(body: bytes, content_type: str) -> str:
    charset = ""
    lowered = content_type.lower()
    if "charset=" in lowered:
        charset = lowered.split("charset=", 1)[1].split(";", 1)[0].strip()
    for encoding in [enc for enc in (charset, "utf-8", "latin-1") if enc]:
        try:
            return body.decode(encoding, errors="strict")
        except Exception:
            continue
    return body.decode("utf-8", errors="ignore")


def _http_get(url: str, timeout_sec: float = TIMEOUT_SEC) -> tuple[str, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/html, text/plain;q=0.9, */*;q=0.2",
        },
    )
    context = ssl.create_default_context() if url.lower().startswith("https://") else None
    with urllib.request.urlopen(request, timeout=timeout_sec, context=context) as response:
        body = response.read()
        content_type = _norm_text(response.headers.get("Content-Type")) or "text/plain"
        final_url = _norm_text(response.geturl()) or url
    return _decode_text(body, content_type), content_type, final_url


def _http_get_json(url: str, timeout_sec: float = TIMEOUT_SEC) -> tuple[dict[str, Any], str]:
    text, _, final_url = _http_get(url, timeout_sec)
    payload = json.loads(text) if text.strip() else {}
    return payload if isinstance(payload, dict) else {}, final_url


def _follow_meta_refresh_if_needed(text: str, content_type: str, base_url: str) -> tuple[str, str]:
    if "html" not in content_type.lower():
        return text, base_url
    match = re.search(
        r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^;]+;\s*url=([^"\']+)["\']',
        text,
        re.IGNORECASE,
    )
    if not match:
        return text, base_url
    redirect_url = urljoin(base_url, _norm_text(match.group(1)))
    if not redirect_url or redirect_url == base_url:
        return text, base_url
    redirected_text, _, redirected_final = _http_get(redirect_url)
    return redirected_text, redirected_final


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._text_parts: list[str] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_map = {k: (v or "") for k, v in attrs}
        self._href = _norm_text(attrs_map.get("href"))
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is None:
            return
        text = " ".join(data.split())
        if text:
            self._text_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        self.links.append({"href": self._href, "text": " ".join(self._text_parts).strip()})
        self._href = None
        self._text_parts = []


def _extract_anchors(html_text: str, base_url: str) -> list[dict[str, str]]:
    parser = _AnchorCollector()
    parser.feed(html_text)
    parser.close()
    out: list[dict[str, str]] = []
    for link in parser.links:
        href = _norm_text(link.get("href"))
        if not href:
            continue
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)
        if parsed.scheme not in {"http", "https"}:
            continue
        out.append({"url": absolute_url, "text": _norm_text(link.get("text"))})
    return out


def _normalize_link(url: str, *, title: str = "", notes: str = "", link_origin: str = "") -> dict[str, str] | None:
    clean_url = _norm_text(url)
    if not clean_url:
        return None
    return {"url": clean_url, "title": _norm_text(title), "notes": _norm_text(notes), "link_origin": _norm_text(link_origin)}


def _dedupe_links(items: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        url = _norm_text(item.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(item)
    return out


def _extract_cran_field_links(html_text: str, base_url: str, field_label: str) -> list[dict[str, str]]:
    pattern = re.compile(rf"<td>\s*{re.escape(field_label)}:\s*</td>\s*<td>(.*?)</td>", re.IGNORECASE | re.DOTALL)
    match = pattern.search(html_text)
    if not match:
        return []
    return _extract_anchors(match.group(1), base_url)


def _parse_description_text(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key = ""
    for raw_line in text.splitlines():
        if not raw_line.strip():
            current_key = ""
            continue
        if raw_line[0].isspace() and current_key:
            fields[current_key] = f"{fields[current_key]} {raw_line.strip()}".strip()
            continue
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        current_key = key.strip()
        fields[current_key] = value.strip()
    return fields


def _resolve_r_sources(package: str) -> dict[str, Any]:
    package_q = quote(package)
    refman_package = f"https://search.r-project.org/CRAN/refmans/{package_q}/html/{package_q}-package.html"
    refman_index = f"https://search.r-project.org/CRAN/refmans/{package_q}/html/00Index.html"
    cran_index = f"https://cran.r-project.org/web/packages/{package_q}/index.html"
    cran_short = f"https://cran.r-project.org/package={package_q}"
    description_url = f"https://cran.r-project.org/web/packages/{package_q}/DESCRIPTION"
    rdrr_url = f"https://rdrr.io/cran/{package_q}/"
    manual_url = f"https://cran.r-project.org/web/packages/{package_q}/{package_q}.pdf"

    docs: list[dict[str, str]] = []
    repos: list[dict[str, str]] = []
    registry_metadata: dict[str, Any] = {"registry": "cran", "description_url": description_url}

    for url, title, notes in (
        (refman_package, f"{package} package doc", "CRAN refman package page"),
        (refman_index, f"{package} index", "CRAN refman index"),
        (cran_index, f"{package} CRAN page", "CRAN package page"),
        (cran_short, f"{package} CRAN shortcut", "CRAN shortcut"),
        (rdrr_url, f"{package} rdrr page", "rdrr package page"),
        (manual_url, f"{package} reference manual", "CRAN manual PDF"),
    ):
        item = _normalize_link(url, title=title, notes=notes, link_origin="registry_cran")
        if item:
            docs.append(item)

    try:
        description_text, _, _ = _http_get(description_url)
        fields = _parse_description_text(description_text)
        registry_metadata.update({
            "package": fields.get("Package", package),
            "title": fields.get("Title", ""),
            "version": fields.get("Version", ""),
            "maintainer": fields.get("Maintainer", ""),
            "release_date": fields.get("Date/Publication", ""),
            "url": fields.get("URL", ""),
            "bug_reports": fields.get("BugReports", ""),
        })
        for raw_url in re.split(r"[\s,]+", fields.get("URL", "")):
            candidate = _norm_text(raw_url)
            if not candidate.startswith(("http://", "https://")):
                continue
            parsed = urlparse(candidate)
            item = _normalize_link(candidate, title=parsed.netloc, notes="Declared package URL", link_origin="registry_cran")
            if not item:
                continue
            if parsed.netloc.lower() in GIT_HOSTS:
                repos.append(item)
            else:
                docs.append(item)
    except Exception as exc:
        registry_metadata["description_fetch_error"] = str(exc)

    try:
        cran_html, _, final_url = _http_get(cran_index)
        for anchor in _extract_cran_field_links(cran_html, final_url, "URL") + _extract_cran_field_links(cran_html, final_url, "Materials"):
            item = _normalize_link(anchor["url"], title=anchor["text"], notes="CRAN package link", link_origin="registry_cran")
            if not item:
                continue
            parsed = urlparse(anchor["url"])
            if parsed.netloc.lower() in GIT_HOSTS:
                repos.append(item)
            else:
                docs.append(item)
    except Exception as exc:
        registry_metadata["package_page_fetch_error"] = str(exc)

    return {
        "package": package,
        "language": "r",
        "documentation_candidates": _dedupe_links(docs),
        "repository_candidates": _dedupe_links(repos),
        "registry_metadata": registry_metadata,
    }


def _resolve_python_sources(package: str) -> dict[str, Any]:
    json_url = f"https://pypi.org/pypi/{quote(package)}/json"
    docs: list[dict[str, str]] = []
    repos: list[dict[str, str]] = []
    registry_metadata: dict[str, Any] = {"registry": "pypi", "pypi_json_url": json_url}
    payload, final_url = _http_get_json(json_url)
    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
    project_urls = info.get("project_urls") if isinstance(info.get("project_urls"), dict) else {}
    home_page = _norm_text(info.get("home_page"))
    project_page = f"https://pypi.org/project/{quote(package)}/"

    registry_metadata.update({
        "package": _norm_text(info.get("name")) or package,
        "summary": _norm_text(info.get("summary")),
        "version": _norm_text(info.get("version")),
        "maintainer": _norm_text(info.get("maintainer")) or _norm_text(info.get("author")),
        "release_date": "",
        "license": _norm_text(info.get("license")),
        "pypi_final_url": final_url,
    })

    if home_page:
        project_urls = {"Homepage": home_page, **project_urls}

    pypi_item = _normalize_link(project_page, title=f"{package} PyPI page", notes="PyPI project page", link_origin="registry_pypi")
    if pypi_item:
        docs.append(pypi_item)

    for label, raw_url in project_urls.items():
        url = _norm_text(raw_url)
        if not url:
            continue
        label_text = _norm_text(label) or url
        key = label_text.lower()
        parsed = urlparse(url)
        item = _normalize_link(url, title=label_text, notes=f"PyPI project URL: {label_text}", link_origin="registry_pypi")
        if not item or any(ignore in key for ignore in IGNORE_PYPI_URL_KEYS):
            continue
        if any(token in key for token in REPO_URL_KEYS) or parsed.netloc.lower() in GIT_HOSTS:
            repos.append(item)
        elif any(token in key for token in DOC_URL_KEYS):
            docs.append(item)
        else:
            docs.append(item)

    releases = payload.get("releases") if isinstance(payload.get("releases"), dict) else {}
    version = registry_metadata.get("version", "")
    if version and isinstance(releases.get(version), list) and releases[version]:
        uploaded = releases[version][0].get("upload_time_iso_8601") or releases[version][0].get("upload_time")
        registry_metadata["release_date"] = _norm_text(uploaded)

    return {
        "package": package,
        "language": "python",
        "documentation_candidates": _dedupe_links(docs),
        "repository_candidates": _dedupe_links(repos),
        "registry_metadata": registry_metadata,
    }


def _resolve_stata_sources(package: str) -> dict[str, Any]:
    package_lower = package.lower()
    first = package_lower[0]
    pkg_url = f"http://fmwww.bc.edu/repec/bocode/{first}/{package_lower}.pkg"
    base_dir = f"http://fmwww.bc.edu/repec/bocode/{first}/"
    docs: list[dict[str, str]] = []
    registry_metadata: dict[str, Any] = {"registry": "ssc", "ssc_pkg_url": pkg_url}

    pkg_text, _, _ = _http_get(pkg_url)
    description = ""
    files: list[str] = []
    for raw_line in pkg_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        marker = line[0].lower()
        payload = line[1:].strip()
        if marker == "d" and payload and not description:
            description = payload
        if marker in {"f", "g"} and payload:
            files.append(payload.split()[0])
    registry_metadata["description"] = description
    registry_metadata["files"] = files

    item = _normalize_link(pkg_url, title=f"{package_lower}.pkg", notes="SSC package manifest", link_origin="registry_stata_ssc")
    if item:
        docs.append(item)
    for rel_path in files:
        rel_file = _norm_text(rel_path)
        if not rel_file:
            continue
        file_url = urljoin(base_dir, rel_file)
        suffix = Path(rel_file).suffix.lower()
        if suffix in STATA_DOC_SUFFIXES:
            item = _normalize_link(file_url, title=Path(rel_file).name, notes="SSC package link", link_origin="registry_stata_ssc")
            if item:
                docs.append(item)

    return {
        "package": package_lower,
        "language": "stata",
        "documentation_candidates": _dedupe_links(docs),
        "repository_candidates": [],
        "registry_metadata": registry_metadata,
    }


def _rank_doc_candidate(language: str, package: str, url: str) -> tuple[int, str]:
    url_low = url.lower()
    package_low = package.lower()
    if language == "r":
        if f"/{package_low}-package.html" in url_low and "search.r-project.org/cran/refmans/" in url_low:
            return (0, url_low)
        if url_low.endswith("/00index.html") and "search.r-project.org/cran/refmans/" in url_low:
            return (1, url_low)
        if "cran.r-project.org/web/packages/" in url_low and url_low.endswith("/index.html"):
            return (2, url_low)
        if "rdrr.io/cran/" in url_low:
            return (3, url_low)
        if url_low.endswith(".pdf"):
            return (9, url_low)
        return (5, url_low)
    if language == "python":
        parsed = urlparse(url_low)
        host = parsed.netloc
        if "readthedocs" in host or host.startswith("docs.") or (host.endswith(".org") and "pypi.org" not in host):
            return (0, url_low)
        if "pypi.org/project/" in url_low:
            return (4, url_low)
        if host in GIT_HOSTS and parsed.path.endswith((".md", ".rst")):
            return (3, url_low)
        if host in GIT_HOSTS:
            return (5, url_low)
        return (2, url_low)
    if language == "stata":
        if url_low.endswith(".sthlp"):
            return (0, url_low)
        if url_low.endswith(".hlp"):
            return (1, url_low)
        if url_low.endswith(".pkg"):
            return (2, url_low)
        if "github.com" in url_low and "readme" in url_low:
            return (4, url_low)
        return (5, url_low)
    return (99, url_low)


def _select_primary_doc_url(language: str, package: str, candidates: list[dict[str, str]], override_url: str = "") -> list[dict[str, str]]:
    ordered: list[dict[str, str]] = []
    if _norm_text(override_url):
        ordered.append({
            "url": _norm_text(override_url),
            "title": "manual override",
            "notes": "User-specified primary doc URL",
            "link_origin": "manual_override",
        })
    ordered.extend(sorted(candidates, key=lambda row: _rank_doc_candidate(language, package, row.get("url", ""))))
    return _dedupe_links(ordered)


def _normalize_blank_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    blank = False
    for line in lines:
        if not _norm_text(line):
            if not blank:
                out.append("")
            blank = True
            continue
        out.append(line.rstrip())
        blank = False
    while out and not _norm_text(out[0]):
        out.pop(0)
    while out and not _norm_text(out[-1]):
        out.pop()
    return out


def _strip_backticks(text: str) -> str:
    return re.sub(r"`([^`]+)`", r"\1", text)


def _normalize_language(value: str) -> str:
    token = _norm_text(value).lower()
    if token in {"py", "python3"}:
        return "python"
    if token in {"rscript"}:
        return "r"
    if token in {"stata-mp", "stata-se"}:
        return "stata"
    return token


def _language_from_attrs(attrs: dict[str, str]) -> str:
    class_values = " ".join([attrs.get("class", ""), attrs.get("data-language", ""), attrs.get("lang", "")]).lower()
    for token in re.split(r"[^a-z0-9_+-]+", class_values):
        if not token or token in {"sourcecode", "highlight", "hljs", "code", "listing"}:
            continue
        for prefix in ("language-", "lang-", "highlight-source-"):
            if token.startswith(prefix):
                token = token[len(prefix):]
                break
        normalized = _normalize_language(token)
        if normalized:
            return normalized
    return ""


def _guess_default_language(default_language: str, source_url: str) -> str:
    if _norm_text(default_language):
        return _normalize_language(default_language)
    parsed = urlparse(source_url or "")
    text = f"{parsed.netloc.lower()}{parsed.path.lower()}"
    if any(token in text for token in ("rdrr.io", "cran.r-project.org", "search.r-project.org", "tidyverse.org")):
        return "r"
    if any(token in text for token in ("pypi.org", "readthedocs", "python.org")):
        return "python"
    if any(token in text for token in ("stata.com", "fmwww.bc.edu", "repec.org")):
        return "stata"
    return ""


def _infer_code_language(code_text: str, default_language: str = "") -> str:
    lowered = code_text.lower()
    if "select " in lowered and " from " in lowered:
        return "sql"
    if any(token in lowered for token in ("import ", "from ", "def ", "print(", "client.")):
        return "python"
    if any(token in lowered for token in ("library(", "<-", "%>%", "|>", "mutate(", "left_join(")):
        return "r"
    if any(token in lowered for token in ("reghdfe ", "reg ", "egen ", "collapse ", "xtset ")):
        return "stata"
    return _normalize_language(default_language)


def _clean_prose_text(text: str) -> str:
    lines = []
    for raw_line in text.replace("\xa0", " ").splitlines():
        normalized = " ".join(raw_line.split())
        if not normalized:
            lines.append("")
            continue
        if normalized.lower() in HTML_NOISE_LINES:
            continue
        lines.append(normalized)
    return "\n".join(_normalize_blank_lines(lines)).strip()


def _clean_code_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not _norm_text(lines[0]):
        lines.pop(0)
    while lines and not _norm_text(lines[-1]):
        lines.pop()
    return "\n".join(lines).strip("\n")


class _HTMLStructuredMarkdownParser(HTMLParser):
    def __init__(self, *, default_language: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.default_language = _normalize_language(default_language)
        self.skip_depth = 0
        self.in_pre = False
        self.inline_code_depth = 0
        self.current_prose: list[str] = []
        self.current_heading: list[str] = []
        self.current_heading_level: int | None = None
        self.current_code: list[str] = []
        self.current_code_lang = ""
        self.blocks: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in SKIP_HTML_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth > 0:
            return
        attr_map = {str(key).lower(): str(value or "") for key, value in attrs}
        if tag == "pre":
            self._flush_heading()
            self._flush_prose()
            self.in_pre = True
            self.current_code = []
            self.current_code_lang = _language_from_attrs(attr_map) or self.default_language
            return
        if tag == "code":
            if self.in_pre:
                self.current_code_lang = _language_from_attrs(attr_map) or self.current_code_lang
            else:
                self.inline_code_depth += 1
                self.current_prose.append("`")
            return
        if tag in HEADING_TAGS:
            self._flush_heading()
            self._flush_prose()
            self.current_heading_level = HEADING_TAGS[tag]
            self.current_heading = []
            return
        if tag == "br":
            self.current_prose.append("\n")
            return
        if tag == "li":
            if self.current_prose and not "".join(self.current_prose).endswith("\n"):
                self.current_prose.append("\n")
            self.current_prose.append("- ")
            return
        if tag in {"td", "th"}:
            self.current_prose.append(" ")
            return
        if tag in BLOCK_HTML_TAGS and self.current_prose and not "".join(self.current_prose).endswith("\n"):
            self.current_prose.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_HTML_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if self.skip_depth > 0:
            return
        if tag == "pre" and self.in_pre:
            self._flush_code()
            self.in_pre = False
            self.current_code = []
            self.current_code_lang = ""
            return
        if tag == "code" and not self.in_pre and self.inline_code_depth > 0:
            self.current_prose.append("`")
            self.inline_code_depth -= 1
            return
        if tag in HEADING_TAGS and self.current_heading_level is not None:
            self._flush_heading()
            return
        if tag in BLOCK_HTML_TAGS:
            self._flush_prose()

    def handle_data(self, data: str) -> None:
        if self.skip_depth > 0:
            return
        if self.in_pre:
            self.current_code.append(data)
            return
        if self.current_heading_level is not None:
            self._append_text(self.current_heading, data)
            return
        self._append_text(self.current_prose, data)

    def close(self) -> None:
        super().close()
        self._flush_heading()
        self._flush_prose()
        if self.current_code:
            self._flush_code()

    def _append_text(self, target: list[str], data: str) -> None:
        text = " ".join(data.replace("\xa0", " ").split())
        if not text:
            return
        if target and not target[-1].endswith((" ", "\n", "`")):
            target.append(" ")
        target.append(text)

    def _flush_heading(self) -> None:
        if self.current_heading_level is None:
            return
        text = _norm_text("".join(self.current_heading))
        if text and text.lower() not in HTML_NOISE_LINES:
            self.blocks.append({"kind": "heading", "level": str(self.current_heading_level), "text": text})
        self.current_heading = []
        self.current_heading_level = None

    def _flush_prose(self) -> None:
        text = _clean_prose_text("".join(self.current_prose))
        if text:
            self.blocks.append({"kind": "prose", "text": text})
        self.current_prose = []

    def _flush_code(self) -> None:
        text = _clean_code_text("".join(self.current_code))
        if not text:
            return
        language = self.current_code_lang or _infer_code_language(text, self.default_language)
        self.blocks.append({"kind": "code", "text": text, "language": language})


def _convert_rst_to_markdown(text: str, default_language: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        directive_match = RST_CODE_DIRECTIVE_RE.match(line.strip())
        if directive_match:
            language = _normalize_language(directive_match.group(1)) or _normalize_language(default_language)
            idx += 1
            while idx < len(lines) and not _norm_text(lines[idx]):
                idx += 1
            block: list[str] = []
            while idx < len(lines):
                current = lines[idx]
                if current.startswith("   "):
                    block.append(current[3:])
                elif current.startswith("\t"):
                    block.append(current[1:])
                elif not _norm_text(current) and block:
                    block.append("")
                else:
                    break
                idx += 1
            if block:
                out.extend([f"```{language}".rstrip(), "\n".join(block).rstrip(), "```", ""])
                continue
            out.append(line)
            continue
        out.append(line)
        idx += 1
    return "\n".join(out).strip() + "\n"


def _convert_indented_code_blocks(text: str, default_language: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    idx = 0
    in_fence = False
    while idx < len(lines):
        line = lines[idx]
        if FENCE_LINE_RE.match(line.strip()):
            in_fence = not in_fence
            out.append(line.rstrip())
            idx += 1
            continue
        if in_fence:
            out.append(line.rstrip())
            idx += 1
            continue
        if line.startswith("    ") or line.startswith("\t"):
            block: list[str] = []
            start_idx = idx
            while idx < len(lines):
                current = lines[idx]
                if current.startswith("    "):
                    block.append(current[4:])
                elif current.startswith("\t"):
                    block.append(current[1:])
                elif not _norm_text(current) and block:
                    block.append("")
                else:
                    break
                idx += 1
            if len([row for row in block if _norm_text(row)]) >= 2:
                language = _infer_code_language("\n".join(block), default_language)
                out.extend([f"```{language}".rstrip(), "\n".join(block).rstrip(), "```", ""])
                continue
            out.extend(lines[start_idx:idx])
            continue
        out.append(line.rstrip())
        idx += 1
    return "\n".join(out).strip() + "\n"


def _render_blocks_to_markdown(blocks: list[dict[str, str]], default_language: str) -> dict[str, Any]:
    markdown_lines: list[str] = []
    plain_lines: list[str] = []
    code_count = 0
    code_languages: list[str] = []
    seen_languages: set[str] = set()
    for block in blocks:
        kind = block.get("kind")
        if kind == "heading":
            level = max(1, min(6, int(_norm_text(block.get("level")) or "1")))
            text = _norm_text(block.get("text"))
            if not text:
                continue
            markdown_lines.extend([f"{'#' * level} {text}", ""])
            plain_lines.extend([text, ""])
            continue
        if kind == "prose":
            text = _clean_prose_text(_norm_text(block.get("text")))
            if not text:
                continue
            markdown_lines.extend(text.splitlines())
            markdown_lines.append("")
            plain_lines.extend(_strip_backticks(text).splitlines())
            plain_lines.append("")
            continue
        if kind == "code":
            code = _clean_code_text(_norm_text(block.get("text")))
            if not code:
                continue
            language = _normalize_language(block.get("language") or "") or _infer_code_language(code, default_language)
            markdown_lines.append(f"```{language}".rstrip())
            markdown_lines.extend(code.splitlines())
            markdown_lines.extend(["```", ""])
            plain_lines.extend(code.splitlines())
            plain_lines.append("")
            code_count += 1
            if language and language not in seen_languages:
                seen_languages.add(language)
                code_languages.append(language)
    markdown_body = "\n".join(_normalize_blank_lines(markdown_lines)).strip()
    plain_text = "\n".join(_normalize_blank_lines(plain_lines)).strip()
    return {
        "markdown_body": markdown_body,
        "plain_text": plain_text,
        "code_block_count": code_count,
        "code_languages": code_languages,
        "content_format": "structured_markdown",
    }


def build_document_content(raw_text: str, suffix: str, *, default_language: str = "", source_url: str = "") -> dict[str, Any]:
    normalized_suffix = _norm_text(suffix).lower()
    guessed_language = _guess_default_language(default_language, source_url)
    if normalized_suffix in {".html", ".htm"}:
        parser = _HTMLStructuredMarkdownParser(default_language=guessed_language)
        parser.feed(raw_text)
        parser.close()
        return _render_blocks_to_markdown(parser.blocks, guessed_language)
    markdown_body = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized_suffix == ".rst":
        markdown_body = _convert_rst_to_markdown(markdown_body, guessed_language)
    markdown_body = _convert_indented_code_blocks(markdown_body, guessed_language)
    markdown_body = markdown_body.strip() + "\n"
    code_count = 0
    code_languages: list[str] = []
    seen_languages: set[str] = set()
    for match in FENCED_BLOCK_RE.finditer(markdown_body):
        code_count += 1
        lang = _normalize_language(match.group(1)) or _infer_code_language(match.group(2), guessed_language)
        if lang and lang not in seen_languages:
            seen_languages.add(lang)
            code_languages.append(lang)
    plain_lines: list[str] = []
    in_fence = False
    for raw_line in markdown_body.splitlines():
        stripped = raw_line.strip()
        if FENCE_LINE_RE.match(stripped):
            in_fence = not in_fence
            continue
        plain_lines.append(raw_line if in_fence else _strip_backticks(raw_line))
    return {
        "markdown_body": markdown_body.strip(),
        "plain_text": "\n".join(_normalize_blank_lines(plain_lines)).strip(),
        "code_block_count": code_count,
        "code_languages": code_languages,
        "content_format": "structured_markdown",
    }


def _pick_repository_url(candidates: list[dict[str, str]]) -> str:
    for item in candidates:
        url = _norm_text(item.get("url"))
        if url:
            return url
    return ""


def _first_heading(markdown_body: str) -> str:
    for line in markdown_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _fetch_primary_doc(language: str, package: str, candidates: list[dict[str, str]]) -> tuple[dict[str, Any], str]:
    errors: list[dict[str, str]] = []
    for candidate in candidates:
        url = candidate["url"]
        try:
            text, content_type, final_url = _http_get(url)
            text, final_url = _follow_meta_refresh_if_needed(text, content_type, final_url)
            suffix = Path(urlparse(final_url).path).suffix or Path(urlparse(url).path).suffix or ".txt"
            content = build_document_content(text, suffix, default_language=language, source_url=final_url)
            title = _first_heading(content["markdown_body"]) or _norm_text(candidate.get("title")) or f"{package} package docs"
            markdown = f"# {title}\n\nSource: {final_url}\n\n---\n\n{content['markdown_body']}\n"
            meta = {
                "selected_url": url,
                "fetched_url": final_url,
                "content_type": content_type,
                "code_block_count": content["code_block_count"],
                "code_languages": content["code_languages"],
                "markdown_chars": len(markdown),
                "plain_text_chars": len(content["plain_text"]),
                "title": title,
                "sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            }
            return meta, markdown
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
    raise RuntimeError(f"Unable to fetch any documentation candidate for {language}::{package}: {errors}")


def resolve_sources(language: str, package: str, override_url: str = "") -> dict[str, Any]:
    if language == "r":
        payload = _resolve_r_sources(package)
    elif language == "python":
        payload = _resolve_python_sources(package)
    elif language == "stata":
        payload = _resolve_stata_sources(package)
    else:
        raise ValueError(f"Unsupported language: {language}")
    payload["documentation_candidates"] = _select_primary_doc_url(language, package, payload.get("documentation_candidates", []), override_url=override_url)
    payload["selected_repository_url"] = _pick_repository_url(payload.get("repository_candidates", []))
    return payload


def write_outputs(output_root: Path, manifest: dict[str, Any], markdown: str | None, doc_meta: dict[str, Any] | None) -> Path:
    outdir = output_root / manifest["language"] / manifest["package"]
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "acquisition_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if markdown is not None and doc_meta is not None:
        (outdir / "official_doc.md").write_text(markdown)
        (outdir / "official_doc.meta.json").write_text(json.dumps(doc_meta, indent=2, ensure_ascii=False) + "\n")
    return outdir


def main() -> int:
    args = parse_args()
    package = _norm_text(args.package)
    language = _norm_text(args.language).lower()
    resolved = resolve_sources(language, package, override_url=args.doc_url)
    manifest: dict[str, Any] = {
        "workflow_version": "1.0",
        "package": resolved["package"],
        "language": resolved["language"],
        "resolved_at_utc": _utc_now(),
        "doc_url_override_used": bool(_norm_text(args.doc_url)),
        "selected_repository_url": resolved.get("selected_repository_url", ""),
        "registry_metadata": resolved.get("registry_metadata", {}),
        "source_resolution": {
            "documentation_candidates": resolved.get("documentation_candidates", []),
            "repository_candidates": resolved.get("repository_candidates", []),
        },
    }

    markdown: str | None = None
    doc_meta: dict[str, Any] | None = None
    if not args.resolve_only:
        doc_meta, markdown = _fetch_primary_doc(language, package, resolved["documentation_candidates"])
        manifest["selected_primary_doc_url"] = doc_meta["fetched_url"]
        manifest["primary_doc"] = {
            "title": doc_meta["title"],
            "content_type": doc_meta["content_type"],
            "markdown_chars": doc_meta["markdown_chars"],
            "code_block_count": doc_meta["code_block_count"],
            "code_languages": doc_meta["code_languages"],
            "sha256": doc_meta["sha256"],
        }

    outdir = write_outputs(args.output_root, manifest, markdown, doc_meta)
    if args.json:
        print(json.dumps({"status": "ok", "output_dir": str(outdir), "manifest": manifest}, indent=2))
    else:
        print(f"Wrote acquisition bundle to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
