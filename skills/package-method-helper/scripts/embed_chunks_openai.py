#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI

# Official references used for this script:
# - https://platform.openai.com/docs/api-reference/embeddings
# - https://platform.openai.com/docs/guides/embeddings
# The docs state a max of 8192 input tokens per item for embedding models,
# and a max of 300,000 total tokens across a single request.


DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_MAX_ITEM_TOKENS = 7000
DEFAULT_MAX_BATCH_TOKENS = 200000
DEFAULT_BATCH_SIZE = 128


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create OpenAI embeddings from safe chunk JSONL exports.")
    parser.add_argument("--input-jsonl", type=Path, required=True, help="Safe chunk export created by export_embedding_chunks.py")
    parser.add_argument("--output-jsonl", type=Path, required=True, help="Output JSONL with embeddings")
    parser.add_argument("--output-manifest", type=Path, help="Optional manifest path. Defaults to <output-jsonl>.manifest.json")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Embedding model to use")
    parser.add_argument("--dimensions", type=int, help="Optional output dimension reduction for text-embedding-3 models")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Maximum items per embedding request")
    parser.add_argument("--max-estimated-item-tokens", type=int, default=DEFAULT_MAX_ITEM_TOKENS)
    parser.add_argument("--max-estimated-batch-tokens", type=int, default=DEFAULT_MAX_BATCH_TOKENS)
    parser.add_argument("--env-file", type=Path, default=Path('.env'), help="Optional .env file to read if OPENAI_API_KEY is not already set")
    parser.add_argument("--skip-too-long", action="store_true", help="Skip records that exceed the estimated per-item token budget")
    return parser.parse_args()


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def estimate_tokens(text: str) -> int:
    # Conservative character-based estimate. Good enough for batching and guardrails.
    return max(1, len(text) // 4)


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open('r', encoding='utf-8') as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no} of {path}: {exc}") from exc
            if not record.get('id') or not record.get('text'):
                raise ValueError(f"Missing id or text on line {line_no} of {path}")
            records.append(record)
    return records


def batch_records(records: list[dict[str, Any]], max_batch_items: int, max_batch_tokens: int) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_tokens = 0
    for record in records:
        rec_tokens = int(record['_estimated_tokens'])
        if current and (len(current) >= max_batch_items or current_tokens + rec_tokens > max_batch_tokens):
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(record)
        current_tokens += rec_tokens
    if current:
        batches.append(current)
    return batches


def main() -> int:
    args = parse_args()
    load_env_file(args.env_file)
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print('OPENAI_API_KEY is not set. Provide it in the environment or a local .env file.', file=sys.stderr)
        return 2

    records = load_records(args.input_jsonl)
    kept: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for record in records:
        est = estimate_tokens(record['text'])
        record['_estimated_tokens'] = est
        if est > args.max_estimated_item_tokens:
            if args.skip_too_long:
                skipped.append({
                    'id': record['id'],
                    'reason': 'estimated_item_tokens_exceeded',
                    'estimated_tokens': est,
                })
                continue
            print(
                f"Record {record['id']} estimated at {est} tokens exceeds per-item limit {args.max_estimated_item_tokens}. "
                f"Use --skip-too-long to skip oversized items.",
                file=sys.stderr,
            )
            return 3
        kept.append(record)

    client = OpenAI(api_key=api_key)
    batches = batch_records(kept, args.batch_size, args.max_estimated_batch_tokens)
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_manifest = args.output_manifest or args.output_jsonl.with_suffix(args.output_jsonl.suffix + '.manifest.json')

    written = 0
    total_prompt_tokens = 0
    model_name = args.model
    with args.output_jsonl.open('w', encoding='utf-8') as handle:
        for idx, batch in enumerate(batches, 1):
            inputs = [record['text'] for record in batch]
            request: dict[str, Any] = {
                'model': args.model,
                'input': inputs,
            }
            if args.dimensions is not None:
                request['dimensions'] = args.dimensions
            response = client.embeddings.create(**request)
            model_name = response.model
            usage = getattr(response, 'usage', None)
            if usage is not None:
                total_prompt_tokens += int(getattr(usage, 'total_tokens', 0) or 0)
            data = response.data
            if len(data) != len(batch):
                raise RuntimeError(f"Embedding count mismatch in batch {idx}: expected {len(batch)}, got {len(data)}")
            for record, item in zip(batch, data):
                out = {
                    'id': record['id'],
                    'language': record.get('language'),
                    'package': record.get('package'),
                    'canonical_package_name': record.get('canonical_package_name'),
                    'doc_type': record.get('doc_type'),
                    'chunk_type': record.get('chunk_type'),
                    'importance_tier': record.get('importance_tier'),
                    'title': record.get('title'),
                    'function_or_command': record.get('function_or_command'),
                    'task_tags': record.get('task_tags', []),
                    'retrieval_priority': record.get('retrieval_priority'),
                    'role_class': record.get('role_class'),
                    'agent_safety_class': record.get('agent_safety_class'),
                    'source_kind': record.get('source_kind'),
                    'text_sha256': record.get('text_sha256'),
                    'embedding_model': response.model,
                    'embedding_dimensions': len(item.embedding),
                    'embedding': item.embedding,
                }
                handle.write(json.dumps(out, ensure_ascii=False) + '\n')
                written += 1
            print(f"Embedded batch {idx}/{len(batches)} ({len(batch)} items)", file=sys.stderr)

    manifest = {
        'schema_version': 1,
        'input_jsonl': str(args.input_jsonl),
        'output_jsonl': str(args.output_jsonl),
        'model': model_name,
        'requested_dimensions': args.dimensions,
        'record_count': written,
        'skipped_count': len(skipped),
        'skipped': skipped,
        'batch_count': len(batches),
        'max_batch_size': args.batch_size,
        'max_estimated_item_tokens': args.max_estimated_item_tokens,
        'max_estimated_batch_tokens': args.max_estimated_batch_tokens,
        'total_prompt_tokens_reported': total_prompt_tokens,
        'notes': [
            'Embeddings created from the safe JSONL export rather than raw repository files.',
            'OPENAI_API_KEY was loaded from environment or local .env and is not written to output.',
        ],
    }
    output_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
