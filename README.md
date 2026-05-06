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
- a standard official-doc acquisition workflow for CRAN, PyPI, and SSC/Stata packages
- a standard methods-paper acquisition workflow for paper-layer ingestion
- a reviewable approval-and-ingest workflow for adding new package bundles or paper layers into an existing collection
- bundled templates for filling package gaps in the collection
- a stable location for future precomputed embedding downloads

## Before you start

### What is DuckDB?

DuckDB is an in-process analytical SQL database. This skill uses DuckDB as a local searchable index over package manifests, cards, chunks, and raw docs.

Official references:
- [DuckDB home](https://duckdb.org/)
- [DuckDB documentation](https://duckdb.org/docs/current/)
- [DuckDB installation](https://duckdb.org/install/)
- [DuckDB Python client](https://duckdb.org/docs/stable/clients/python/overview)

Use the prebuilt DuckDB if you want a ready-made index.
Build the DuckDB locally if you want to ingest new packages, refresh the corpus, or point the skill at your own collection.

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

## Download a prebuilt DuckDB instead

If you do not want to build the index yourself, you can download the published DuckDB bundle from Dropbox.

Recommended long-term public distribution:
1. GitHub release asset for `package_method_helper_duckdb_bundle.zip`
2. another direct binary URL
3. Dropbox folder link only as manual fallback

Folder link:
- maintainer-provided Dropbox folder link

Manual flow:
- open the Dropbox folder
- download:
  - `package_method_helper.duckdb`
  - `package_method_helper.summary.json`
- place them in:
  - `work/generated/duckdb/`

Scripted download once you have a direct bundle URL:

```bash
export PACKAGE_METHOD_HELPER_PREBUILT_DUCKDB_URL="https://example.com/package_method_helper_duckdb_bundle.zip"
python3 skills/package-method-helper/scripts/download_prebuilt_duckdb.py --json
```

That writes:
- `work/generated/duckdb/package_method_helper.duckdb`
- `work/generated/duckdb/package_method_helper.summary.json`

Important:
- the downloader script expects a direct ZIP URL, not a folder-view page
- use a maintainer-provided Dropbox folder link only for manual fallback
- if you later publish a direct file URL or GitHub release asset, reuse the same script

Maintainer note:
- build the distribution bundle with:

```bash
python3 skills/package-method-helper/scripts/build_prebuilt_duckdb_bundle.py \
  --db-path /absolute/path/to/package_method_helper.duckdb \
  --summary-path /absolute/path/to/package_method_helper.summary.json \
  --output-dir /absolute/path/to/distribution_folder \
  --move-source \
  --include-readme \
  --json
```

Publishing details:
- `docs/publishing_prebuilt_duckdb.md`

Use the prebuilt database when you only need:
- verified package query
- bounded follow-up retrieval
- embedding export from the curated corpus

Build locally instead if you need to:
- ingest new packages or paper layers
- rebuild after collection changes
- point the skill at your own corpus

## Build all bundles at once

This creates:
- one DuckDB index
- one safe chunk bundle each for `r`, `python`, and `stata`
- optional embeddings for all three language bundles

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

The query script treats language as a hard gate:
- pass `--language` explicitly, or
- let it infer the language from the package name or syntax cues

If it cannot resolve one language cleanly, it fails instead of doing a cross-language similarity search. Use `--allow-cross-language` only when you explicitly want that broader behavior.

For exact package queries, the JSON response also includes a bounded `follow_up` payload with:
- package manifest context
- source/version/status sidecar context
- core cards such as summary and decision docs
- function-level edges
- adjacent packages from common pairings and neighbor links when they exist in the same language corpus

## Acquire official docs for a new package

Use the acquisition script before you build a gap-fill bundle. It resolves official sources deterministically and fetches one normalized doc page plus provenance metadata.

Example:

```bash
python3 skills/package-method-helper/scripts/acquire_official_package_docs.py \
  --language r \
  --package mediation \
  --output-root work/generated/source_acquisition \
  --json
```

It writes:
- `acquisition_manifest.json`
- `official_doc.md`
- `official_doc.meta.json`

Language defaults:
- R: CRAN refman / DESCRIPTION first
- Python: PyPI JSON + project docs first
- Stata: SSC `.sthlp` / `.hlp` first

If the best official doc page is not the default registry target, pass `--doc-url`.

## Acquire a methods paper source

Use the paper-acquisition script before generating `paper_note`, `equation`, or `bridge` cards.

Example:

```bash
python3 skills/package-method-helper/scripts/acquire_methods_paper.py \
  --language stata \
  --package boottest \
  --output-root work/generated/paper_acquisition \
  --json
```

It writes:
- `paper_source_manifest.json`
- `paper_source.md`
- `paper_source.meta.json`

For packages outside the small built-in map, pass `--paper-url`.

The paper source bundle also records `capture_scope` so you can tell whether the acquisition captured:
- a landing page
- an abstract page
- a longer HTML article
- a PDF source reference

Then generate the paper-layer cards:

```bash
python3 skills/package-method-helper/scripts/generate_paper_layer_from_source.py \
  --language python \
  --package statsmodels \
  --paper-source-root work/generated/paper_acquisition \
  --output-root work/generated/paper_layers \
  --json
```

## Plan and apply collection ingest

After you have either:
- a full gap-fill package bundle, or
- a generated paper-layer bundle

create an approval plan first:

```bash
python3 skills/package-method-helper/scripts/plan_collection_ingest.py \
  --collection-root /path/to/package_methods_top50_language_upload_tasks \
  --bundle-root work/generated/paper_layers \
  --language r \
  --package fixest \
  --output-root work/generated/ingest_plans \
  --json
```

Then apply it only after review:

```bash
python3 skills/package-method-helper/scripts/ingest_collection_bundle.py \
  --approval-manifest work/generated/ingest_plans/r/fixest/ingest_approval_manifest.json \
  --approve \
  --rebuild-db \
  --output-db work/generated/duckdb/package_method_helper.duckdb \
  --json
```

This updates:
- the target shard files
- `shard_manifest.json`
- `language_upload_manifest.json`
- `master_manifest.json`
- and optionally the DuckDB index

## Create safe chunk exports for embeddings

```bash
python3 skills/package-method-helper/scripts/export_embedding_chunks.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language python \
  --output-jsonl work/generated/duckdb/package_method_helper_embedding_chunks.jsonl
```

The exported JSONL is scrubbed for safe sharing:
- no absolute local paths
- no `_PATH` staging markers
- stable retrieval metadata only
- full raw docs excluded by default, so the output is safer for embedding jobs
- use a language-specific export by default so retrieval stays language-bounded

## Create your own OpenAI embeddings

Official OpenAI embeddings docs used for this repo:
- [Embeddings API reference](https://platform.openai.com/docs/api-reference/embeddings)
- [Embeddings guide](https://platform.openai.com/docs/guides/embeddings)
- [Developer quickstart](https://platform.openai.com/docs/quickstart)
- [API key dashboard](https://platform.openai.com/api-keys)
- [Where to find/create your API key](https://help.openai.com/en/articles/4936850-how-to-create-and-use-an-api-key)
- [API key safety best practices](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)

Step-by-step:

1. Create an OpenAI API key in the dashboard:
   - [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Keep it out of git and out of client-side code.
3. Choose one local setup path:
   - shell environment variable
   - local `.env` file
4. Verify the key is available in your shell.
5. Run the embedding script on the safe chunk export.

Set your API key locally and keep it out of git:

```bash
cp .env.example .env
# then edit .env locally
```

If you want the key only for the current terminal session:

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

If you want a persistent local shell setup on macOS/Linux:

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

Then run:

```bash
python3 skills/package-method-helper/scripts/embed_chunks_openai.py \
  --input-jsonl work/generated/duckdb/package_method_helper_embedding_chunks.jsonl \
  --output-jsonl work/generated/embeddings/package_method_helper_embeddings.jsonl
```

The script reads `OPENAI_API_KEY` from the environment first, then from `.env` if present.

If you are using this repo exactly as designed, the safest local workflow is:
1. install `requirements.txt`
2. export or save `OPENAI_API_KEY` locally
3. export a language-bounded chunk file
4. embed that file with `embed_chunks_openai.py`

## Run smoke tests

```bash
python3 tests/run_smoke_tests.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --bundles-root work/generated/bundles
```

If you are using only the prebuilt DuckDB and not local bundle exports yet, use:

```bash
python3 -m py_compile skills/package-method-helper/scripts/download_prebuilt_duckdb.py
python3 skills/package-method-helper/scripts/query_package_method_helper_duckdb.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --package fixest \
  --query "fixed effects clustered standard errors" \
  --json
```

## Run live doc-acquisition tests

This checks one real package per ecosystem against live official sources:

```bash
python3 tests/run_doc_acquisition_tests.py
```

## Run live methods-paper acquisition tests

```bash
python3 tests/run_methods_paper_acquisition_tests.py
```

## Run paper-layer generation tests

```bash
python3 tests/run_paper_layer_generation_tests.py
```

## Run ingest workflow tests

```bash
python3 tests/run_ingest_workflow_tests.py
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

Current requirements:
- `duckdb>=1.0.0` for query, export, and local index build
- `openai>=1.0.0` only if you want to create embeddings with the bundled OpenAI helper

If you only want to use the prebuilt DuckDB for local query, `duckdb` is the only runtime dependency you need from `requirements.txt`.

## Repository safety

This repo is meant to be public.

Ignored by default:
- `.env`
- `.env.*`
- generated DuckDB files
- generated embedding outputs
- local caches and Python bytecode

Do not commit API keys, local corpora, or generated embedding outputs unless you explicitly mean to publish them.
