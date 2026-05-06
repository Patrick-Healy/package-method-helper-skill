# Embedding Setup

Official references:
- [OpenAI embeddings guide](https://platform.openai.com/docs/guides/embeddings)
- [OpenAI embeddings API reference](https://platform.openai.com/docs/api-reference/embeddings)
- [OpenAI developer quickstart](https://platform.openai.com/docs/quickstart)
- [OpenAI API key dashboard](https://platform.openai.com/api-keys)
- [OpenAI API key help article](https://help.openai.com/en/articles/4936850-how-to-create-and-use-an-api-key)
- [OpenAI API key safety](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)
- [DuckDB documentation](https://duckdb.org/docs/current/)
- [DuckDB Python client](https://duckdb.org/docs/stable/clients/python/overview)

This skill supports three embedding paths:

1. **Published starter chunk bundle**
   - Download `package_method_helper_starter_embedding_chunks_bundle.zip` from the public Dropbox folder.
   - It contains the curated top-50 package starter set for `r`, `python`, and `stata`.
   - Use the included language-bounded JSONL files directly with `scripts/embed_chunks_openai.py` or another embedding pipeline.

2. **Self-exported chunks from the prebuilt DuckDB**
   - Download the prebuilt DuckDB bundle.
   - Export safe chunk payloads with `scripts/export_embedding_chunks.py`.
   - Create vectors with `scripts/embed_chunks_openai.py` or another embedding pipeline.

3. **Precomputed embeddings**
   - Later, drop published embedding files into `assets/precomputed_embeddings/` using the contract in that folder.
   - Keep the raw chunk JSONL and the embedding vectors versioned separately.

## What DuckDB is doing here

DuckDB is the local query/index layer for this skill.
The embedding workflow does not embed arbitrary repo files directly. It first exports safe, language-bounded retrieval records from the DuckDB index, then sends those records to the embedding API.

## Step-by-step OpenAI key setup

1. Create an API key:
   - [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Read the quickstart and embeddings docs:
   - [Quickstart](https://platform.openai.com/docs/quickstart)
   - [Embeddings guide](https://platform.openai.com/docs/guides/embeddings)
3. Keep the key out of git:
   - never commit `.env`
   - never hard-code the key in scripts
4. Set the key locally.

Current shell only:

### macOS / Linux

```bash
export OPENAI_API_KEY="your_api_key_here"
echo "$OPENAI_API_KEY"
```

### Windows PowerShell

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
echo $env:OPENAI_API_KEY
```

Persistent shell setup on macOS / Linux:

### zsh

```bash
echo 'export OPENAI_API_KEY="your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

### bash

```bash
echo 'export OPENAI_API_KEY="your_api_key_here"' >> ~/.bash_profile
source ~/.bash_profile
```

Local `.env` option:

```bash
cp .env.example .env
# edit .env locally and add:
# OPENAI_API_KEY=your_api_key_here
```

The bundled script checks:
1. `OPENAI_API_KEY` in the environment
2. local `.env` if present

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
python3 skills/package-method-helper/scripts/export_embedding_chunks.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language python \
  --output-jsonl work/generated/duckdb/package_method_helper_python_embedding_chunks.jsonl

python3 skills/package-method-helper/scripts/embed_chunks_openai.py \
  --input-jsonl work/generated/duckdb/package_method_helper_python_embedding_chunks.jsonl \
  --output-jsonl work/generated/embeddings/package_method_helper_python_embeddings.jsonl \
  --model text-embedding-3-small
```

Recommended order:
1. either download the starter chunk bundle or build/download the DuckDB
2. use one language-bounded chunk file
3. confirm `OPENAI_API_KEY` is set locally
4. run the embedding script
5. keep the output vectors separate from the raw chunk export

## Caution

Do not embed raw local paths, local usernames, or agent scratch metadata. Use the export script instead of directly batching files from the repo.
