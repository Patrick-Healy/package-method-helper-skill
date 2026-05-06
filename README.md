# Package Method Helper Skill

A public installable skill for Codex and Claude Code that helps empirical researchers write and annotate R, Python, and Stata analysis code from a verified package-documentation corpus.

The installable skill lives at:

- `skills/package-method-helper/`

Install the whole folder, not only `SKILL.md`.

## What this repository provides

- a Codex / Claude-style skill bundle
- a local DuckDB index for verified package docs
- safe chunk export for user-managed GPT embeddings
- an OpenAI embeddings script that reads `OPENAI_API_KEY` from your environment or local `.env`
- bundled templates for filling package gaps in the collection
- a stable location for future precomputed embedding downloads

## Quick install

### Codex

```bash
$skill-installer install https://github.com/Patrick-Healy/package-method-helper-skill/tree/main/skills/package-method-helper
```

Manual install:

```bash
mkdir -p ~/.codex/skills

git clone https://github.com/Patrick-Healy/package-method-helper-skill.git /tmp/package-method-helper-skill
rsync -a /tmp/package-method-helper-skill/skills/package-method-helper/ ~/.codex/skills/package-method-helper/
```

### Claude Code

```bash
mkdir -p ~/.claude/skills

git clone https://github.com/Patrick-Healy/package-method-helper-skill.git /tmp/package-method-helper-skill
rsync -a /tmp/package-method-helper-skill/skills/package-method-helper/ ~/.claude/skills/package-method-helper/
```

Restart the agent session after installation so the skill is discovered.

## Build a local DuckDB index

This repo does not need to publish your corpus. It expects you to point the builder at a local package collection folder.

Example:

```bash
python3 skills/package-method-helper/scripts/build_package_method_helper_duckdb.py \
  --collection-root /path/to/package_methods_top50_language_upload_tasks \
  --comparisons-root /path/to/package_methods_top50_sync_safe/00_comparisons \
  --output-db work/generated/duckdb/package_method_helper.duckdb
```

## Build all bundles at once

This creates:
- one DuckDB index
- one safe chunk bundle for `all`
- one safe chunk bundle each for `r`, `python`, and `stata`
- optional embeddings for all four bundles

```bash
python3 skills/package-method-helper/scripts/build_all_bundles.py \
  --collection-root /path/to/package_methods_top50_language_upload_tasks \
  --comparisons-root /path/to/package_methods_top50_sync_safe/00_comparisons
```

With embeddings:

```bash
python3 skills/package-method-helper/scripts/build_all_bundles.py \
  --collection-root /path/to/package_methods_top50_language_upload_tasks \
  --comparisons-root /path/to/package_methods_top50_sync_safe/00_comparisons \
  --embed \
  --model text-embedding-3-small
```

## Query the local corpus

```bash
python3 skills/package-method-helper/scripts/query_package_method_helper_duckdb.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language python \
  --package statsmodels \
  --query "formula OLS clustered inference"
```

## Create safe chunk exports for embeddings

```bash
python3 skills/package-method-helper/scripts/export_embedding_chunks.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --output-jsonl work/generated/duckdb/package_method_helper_embedding_chunks.jsonl
```

The exported JSONL is scrubbed for safe sharing:
- no absolute local paths
- no `_PATH` staging markers
- stable retrieval metadata only
- full raw docs excluded by default, so the output is safer for embedding jobs

## Create your own OpenAI embeddings

Official OpenAI embeddings docs used for this repo:
- [Embeddings API reference](https://platform.openai.com/docs/api-reference/embeddings)
- [Embeddings guide](https://platform.openai.com/docs/guides/embeddings)

Set your API key locally and keep it out of git:

```bash
cp .env.example .env
# then edit .env locally
```

Then run:

```bash
python3 skills/package-method-helper/scripts/embed_chunks_openai.py \
  --input-jsonl work/generated/duckdb/package_method_helper_embedding_chunks.jsonl \
  --output-jsonl work/generated/embeddings/package_method_helper_embeddings.jsonl
```

The script reads `OPENAI_API_KEY` from the environment first, then from `.env` if present.

## Run smoke tests

```bash
python3 tests/run_smoke_tests.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --bundles-root work/generated/bundles
```

## Precomputed embeddings

This repo is also structured so you can later download published precomputed embeddings into:

- `skills/package-method-helper/assets/precomputed_embeddings/`

The expected file contract is documented in:

- `skills/package-method-helper/assets/precomputed_embeddings/README.md`

## Requirements

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Repository safety

This repo is meant to be public.

Ignored by default:
- `.env`
- `.env.*`
- generated DuckDB files
- generated embedding outputs
- local caches and Python bytecode

Do not commit API keys, local corpora, or generated embedding outputs unless you explicitly mean to publish them.
