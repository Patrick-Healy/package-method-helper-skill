# DuckDB Usage

Official DuckDB references:
- [DuckDB home](https://duckdb.org/)
- [DuckDB documentation](https://duckdb.org/docs/current/)
- [DuckDB installation](https://duckdb.org/install/)
- [DuckDB Python client](https://duckdb.org/docs/stable/clients/python/overview)

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

## Download the published prebuilt DuckDB

If you only need the curated published corpus, you can skip the local build and download the prebuilt bundle.

Dropbox folder:
- maintainer-provided Dropbox folder link

Manual install:
- download `package_method_helper.duckdb`
- download `package_method_helper.summary.json`
- place both in `work/generated/duckdb/`

If you later publish a direct ZIP URL or release asset, the helper script can install it:

```bash
export PACKAGE_METHOD_HELPER_PREBUILT_DUCKDB_URL="https://example.com/package_method_helper_duckdb_bundle.zip"
python3 skills/package-method-helper/scripts/download_prebuilt_duckdb.py --json
```

This installs:
- `work/generated/duckdb/package_method_helper.duckdb`
- `work/generated/duckdb/package_method_helper.summary.json`

Use the prebuilt DB for query and export workflows.
Build locally when the collection has changed or you need to index your own corpus.

## Build a publishable prebuilt bundle

For maintainers publishing a new binary artifact:

```bash
python3 skills/package-method-helper/scripts/build_prebuilt_duckdb_bundle.py \
  --db-path /absolute/path/to/package_method_helper.duckdb \
  --summary-path /absolute/path/to/package_method_helper.summary.json \
  --output-dir /absolute/path/to/distribution_folder \
  --move-source \
  --include-readme \
  --json
```

This creates:
- `package_method_helper_duckdb_bundle.zip`
- `prebuilt_duckdb_manifest.json`

Recommended publish target:
- GitHub release asset first
- Dropbox folder link only as manual fallback

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
  --package statsmodels \
  --json
```

For exact package queries, inspect the `follow_up` object as well as the top-ranked documents. It carries:
- package-manifest context
- sidecar version/source/status context
- core summary/decision/overview docs
- function-level edges
- adjacent package edges from common pairings and neighbor packages

Language gate behavior:
- the query tool searches one language at a time
- if `--language` is omitted, it tries to infer the language from the package name or syntax cues
- if inference is ambiguous, it fails and asks you to be explicit
- use `--allow-cross-language` only when you intentionally want broad similarity search

## Export safe chunk payloads for GPT embeddings

```bash
python3 skills/package-method-helper/scripts/export_embedding_chunks.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language python \
  --output-jsonl work/generated/duckdb/package_method_helper_python_embedding_chunks.jsonl
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
