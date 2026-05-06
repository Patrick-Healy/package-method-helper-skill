#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


LANGUAGE_TASK_HINTS = {
    "r": "_r_",
    "python": "_python_",
    "stata": "_stata_",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_task_manifest(collection_root: Path, language: str) -> tuple[Path, dict[str, Any]]:
    master = load_json(collection_root / "master_manifest.json")
    for task_id in master.get("global_upload_order", []):
        task_dir = collection_root / task_id
        manifest_path = task_dir / "language_upload_manifest.json"
        if manifest_path.exists():
            manifest = load_json(manifest_path)
            if str(manifest.get("language", "")).lower() == language.lower():
                return task_dir, manifest
    hint = LANGUAGE_TASK_HINTS.get(language.lower(), language.lower())
    for task_dir in sorted(collection_root.iterdir()):
        if task_dir.is_dir() and hint in task_dir.name.lower():
            manifest_path = task_dir / "language_upload_manifest.json"
            if manifest_path.exists():
                return task_dir, load_json(manifest_path)
    raise FileNotFoundError(f"No language task found for {language} under {collection_root}")


def find_package_in_task(task_dir: Path, language: str, package: str) -> tuple[Path, Path, dict[str, Any]] | None:
    for shard_dir in sorted(p for p in task_dir.iterdir() if p.is_dir() and (p / "shard_manifest.json").exists()):
        manifest_path = shard_dir / "package_manifests" / language / f"{package}.json"
        if manifest_path.exists():
            return shard_dir, manifest_path, load_json(manifest_path)
    return None


def choose_target_shard(task_dir: Path) -> tuple[Path, dict[str, Any]]:
    candidates: list[tuple[int, int, str, Path, dict[str, Any]]] = []
    for shard_dir in sorted(p for p in task_dir.iterdir() if p.is_dir() and (p / "shard_manifest.json").exists()):
        manifest = load_json(shard_dir / "shard_manifest.json")
        candidates.append((int(manifest.get("package_count", 0)), int(manifest.get("file_count", 0)), shard_dir.name, shard_dir, manifest))
    if not candidates:
        raise FileNotFoundError(f"No shard manifests found under {task_dir}")
    _, _, _, shard_dir, manifest = min(candidates)
    return shard_dir, manifest


def detect_bundle_type(bundle_root: Path, language: str, package: str) -> tuple[str, Path]:
    for candidate in (bundle_root, bundle_root / language / package):
        if (candidate / "paper_layer_manifest.json").exists():
            return "paper_layer_update", candidate
    if (bundle_root / "package_manifests" / language / f"{package}.json").exists():
        return "package_addition", bundle_root
    raise FileNotFoundError(f"Could not detect bundle type for {language}::{package} under {bundle_root}")


def enumerate_package_bundle_files(bundle_root: Path, language: str, package: str) -> list[tuple[Path, Path]]:
    mapping: list[tuple[Path, Path]] = []
    for rel in (
        Path("raw_docs") / language / f"{package}.md",
        Path("raw_docs") / language / f"{package}.meta.json",
        Path("package_manifests") / language / f"{package}.json",
    ):
        src = bundle_root / rel
        if src.exists():
            mapping.append((src, rel))
    for root in (bundle_root / "package_doc_collection" / "cards", bundle_root / "package_doc_collection" / "chunks"):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and package in path.relative_to(bundle_root).parts:
                mapping.append((path, path.relative_to(bundle_root)))
    if not mapping:
        raise FileNotFoundError(f"No package bundle files found for {language}::{package} under {bundle_root}")
    return mapping


def enumerate_paper_layer_files(bundle_root: Path, language: str, package: str) -> list[tuple[Path, Path]]:
    paper_dir = bundle_root / language / package if (bundle_root / language / package).exists() else bundle_root
    mapping: list[tuple[Path, Path]] = []
    for stem in (f"paper_{language}_{package}.md", f"equation_{language}_{package}.md", f"bridge_{language}_{package}.md"):
        src = paper_dir / stem
        if src.exists():
            mapping.append((src, Path("package_doc_collection") / "cards" / "papers" / language / package / stem))
    updated_manifest = paper_dir / "updated_package_manifest.json"
    if updated_manifest.exists():
        mapping.append((updated_manifest, Path("package_manifests") / language / f"{package}.json"))
    if not mapping:
        raise FileNotFoundError(f"No paper-layer files found for {language}::{package} under {paper_dir}")
    return mapping


def package_file_bytes(shard_dir: Path, language: str) -> dict[str, int]:
    totals: dict[str, int] = {}
    manifest_root = shard_dir / "package_manifests" / language
    if manifest_root.exists():
        for manifest in manifest_root.glob("*.json"):
            totals.setdefault(manifest.stem, 0)
    for root in (shard_dir / "raw_docs" / language, shard_dir / "package_manifests" / language):
        if root.exists():
            for path in root.rglob("*"):
                if path.is_file():
                    package = path.stem.replace(".meta", "") if path.name.endswith(".meta.json") else path.stem
                    totals[package] = totals.get(package, 0) + path.stat().st_size
    for root in (shard_dir / "package_doc_collection" / "cards", shard_dir / "package_doc_collection" / "chunks"):
        if root.exists():
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                for segment in path.relative_to(root).parts:
                    if segment in totals:
                        totals[segment] = totals.get(segment, 0) + path.stat().st_size
                        break
    return totals


def compute_shard_manifest(shard_dir: Path, base_manifest: dict[str, Any]) -> dict[str, Any]:
    language = str(base_manifest.get("language", "")).lower()
    manifest_root = shard_dir / "package_manifests" / language
    package_list = sorted(p.stem for p in manifest_root.glob("*.json")) if manifest_root.exists() else []
    files = sorted(p for p in shard_dir.rglob("*") if p.is_file() and p.name != ".DS_Store")
    file_sizes = [p.stat().st_size for p in files]
    digest_source = "\n".join(f"{p.relative_to(shard_dir)}::{hashlib.sha256(p.read_bytes()).hexdigest()}" for p in files)
    package_bytes = package_file_bytes(shard_dir, language)
    largest_packages = [{"package": package, "approx_bytes": size} for package, size in sorted(package_bytes.items(), key=lambda item: (-item[1], item[0]))[:5]]
    total_bytes = sum(file_sizes)
    return {
        "schema_version": int(base_manifest.get("schema_version", 1)),
        "shard_id": base_manifest.get("shard_id", shard_dir.name),
        "label": base_manifest.get("label", shard_dir.name),
        "language": language,
        "package_count": len(package_list),
        "package_list": package_list,
        "contains_comparisons": bool(base_manifest.get("contains_comparisons", False)),
        "depends_on_shared_comparisons": bool(base_manifest.get("depends_on_shared_comparisons", True)),
        "upload_order": int(base_manifest.get("upload_order", 0)),
        "validation_timestamp_utc": utc_now_iso(),
        "content_digest_sha256": sha256_text(digest_source),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "median_file_size_bytes": sorted(file_sizes)[len(file_sizes) // 2] if file_sizes else 0,
        "largest_file_size_bytes": max(file_sizes) if file_sizes else 0,
        "approx_token_estimate": int(round(total_bytes / 4)) if total_bytes else 0,
        "largest_packages": largest_packages,
    }


def compute_task_manifest(task_dir: Path, base_manifest: dict[str, Any]) -> dict[str, Any]:
    shard_manifests = [load_json(shard_dir / "shard_manifest.json") for shard_dir in sorted(p for p in task_dir.iterdir() if p.is_dir() and (p / "shard_manifest.json").exists())]
    package_list = sorted({pkg for shard in shard_manifests for pkg in shard.get("package_list", [])})
    return {
        "schema_version": int(base_manifest.get("schema_version", 1)),
        "task_id": base_manifest.get("task_id", task_dir.name),
        "label": base_manifest.get("label", task_dir.name),
        "language": str(base_manifest.get("language", "")).lower(),
        "upload_order": int(base_manifest.get("upload_order", 0)),
        "source_bundle": base_manifest.get("source_bundle", ""),
        "contains_shared_comparisons": bool(base_manifest.get("contains_shared_comparisons", False)),
        "shared_comparisons_note": base_manifest.get("shared_comparisons_note", ""),
        "shard_count": len(shard_manifests),
        "package_count": len(package_list),
        "package_list": package_list,
        "shards": shard_manifests,
    }


def update_master_manifest(collection_root: Path) -> dict[str, Any]:
    master_path = collection_root / "master_manifest.json"
    master = load_json(master_path)
    tasks = [load_json(collection_root / task_id / "language_upload_manifest.json") for task_id in master.get("global_upload_order", [])]
    master["task_count"] = len(tasks)
    master["tasks"] = tasks
    write_json(master_path, master)
    return master


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_mapping(mapping: Iterable[tuple[Path, Path]], target_root: Path) -> list[dict[str, str]]:
    copied: list[dict[str, str]] = []
    for src, rel in mapping:
        dst = target_root / rel
        ensure_parent(dst)
        shutil.copy2(src, dst)
        copied.append({"source": str(src), "target": str(dst)})
    return copied
