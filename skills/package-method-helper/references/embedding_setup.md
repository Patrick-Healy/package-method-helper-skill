# Embedding Setup

This skill supports two embedding paths:

1. **Self-embedded chunks**
   - Build the DuckDB index.
   - Export safe chunk payloads with `scripts/export_embedding_chunks.py`.
   - Create vectors with `scripts/embed_chunks_openai.py` or another embedding pipeline.

2. **Precomputed embeddings**
   - Later, drop published embedding files into `assets/precomputed_embeddings/` using the contract in that folder.
   - Keep the raw chunk JSONL and the embedding vectors versioned separately.

## Safe export principles

The export script is designed to keep embedding payloads safe to share:
- no absolute local filesystem paths
- no `_PATH` markers from staging
- only stable identifiers and retrieval metadata
- one text payload per chunk or card
- no full raw docs unless you explicitly opt in

## Recommended embedding payload fields

Each record should contain:
- `id`
- `language`
- `package`
- `canonical_package_name`
- `doc_type`
- `chunk_type`
- `title`
- `function_or_command`
- `task_tags`
- `importance_tier`
- `text`

## Recommended OpenAI embedding workflow

Use a current text-embedding model and keep these controls stable:
- one record per chunk
- preserve stable IDs
- write a manifest with model name, embedding dimension, creation date, and source DB digest
- keep vectors and metadata in a machine-readable format such as Parquet

Example:

```bash
python3 skills/package-method-helper/scripts/embed_chunks_openai.py \
  --input-jsonl work/generated/duckdb/package_method_helper_embedding_chunks.jsonl \
  --output-jsonl work/generated/embeddings/package_method_helper_embeddings.jsonl \
  --model text-embedding-3-small
```

## Caution

Do not embed raw local paths, local usernames, or agent scratch metadata. Use the export script instead of directly batching files from the repo.
