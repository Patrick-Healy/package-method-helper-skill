# DuckDB Usage

## Build the local index

From the repository root:

```bash
python3 skills/package-method-helper/scripts/build_package_method_helper_duckdb.py
```

Explicit paths:

```bash
python3 skills/package-method-helper/scripts/build_package_method_helper_duckdb.py \
  --collection-root work/generated/package_methods_top50_language_upload_tasks \
  --comparisons-root work/generated/package_methods_top50_sync_safe/00_comparisons \
  --output-db work/generated/duckdb/package_method_helper.duckdb
```

## Query the index

Package-focused lookup:

```bash
python3 skills/package-method-helper/scripts/query_package_method_helper_duckdb.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language r \
  --package fixest \
  --query "fixed effects clustered standard errors" \
  --limit 8
```

Document search:

```bash
python3 skills/package-method-helper/scripts/query_package_method_helper_duckdb.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language stata \
  --query "event study coefficient plot" \
  --mode documents \
  --limit 10
```

JSON output:

```bash
python3 skills/package-method-helper/scripts/query_package_method_helper_duckdb.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language python \
  --package statsmodels \
  --json
```

## Export safe chunk payloads for GPT embeddings

```bash
python3 skills/package-method-helper/scripts/export_embedding_chunks.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --output-jsonl work/generated/duckdb/package_method_helper_embedding_chunks.jsonl
```

Language filter:

```bash
python3 skills/package-method-helper/scripts/export_embedding_chunks.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language stata \
  --output-jsonl work/generated/duckdb/package_method_helper_stata_embedding_chunks.jsonl
```

The export script removes absolute local paths, keeps only safe retrieval metadata plus the chunk text, and excludes full raw docs by default.

## Create OpenAI embeddings from the safe export

Official references:
- https://platform.openai.com/docs/api-reference/embeddings
- https://platform.openai.com/docs/guides/embeddings

```bash
python3 skills/package-method-helper/scripts/embed_chunks_openai.py \
  --input-jsonl work/generated/duckdb/package_method_helper_embedding_chunks.jsonl \
  --output-jsonl work/generated/embeddings/package_method_helper_embeddings.jsonl
```

The script reads `OPENAI_API_KEY` from the environment first, then from a local `.env` file if present.
