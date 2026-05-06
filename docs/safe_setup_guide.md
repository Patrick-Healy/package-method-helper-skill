# Safe Setup Guide

This guide is for users who want to get the Package Method Helper working quickly without exposing secrets or getting lost in the maintainer workflows.

Use this guide if you want to:
- install the skill
- get a working DuckDB index
- set up an OpenAI API key safely
- generate embeddings locally
- verify that everything works

## What you need

Minimum:
- Python `3.10+`
- `git`
- a terminal

Repository dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you only want to query the prebuilt DuckDB:
- `duckdb` is the only real runtime dependency you need

If you also want to create embeddings:
- you also need an OpenAI API key

## What DuckDB is doing here

DuckDB is the local index for the package corpus.
This skill does not query loose markdown files directly. It queries a structured DuckDB database built from:
- package manifests
- summary and decision cards
- function cards
- documentation chunks
- raw docs and sidecars

Official references:
- [DuckDB home](https://duckdb.org/)
- [DuckDB docs](https://duckdb.org/docs/current/)
- [DuckDB install](https://duckdb.org/install/)
- [DuckDB Python client](https://duckdb.org/docs/stable/clients/python/overview)

## Choose your setup path

Most users should choose exactly one of these:

### Path A — Use the prebuilt DuckDB from Dropbox

Choose this if:
- you just want to query the curated corpus
- you do not need to ingest new packages yet
- you want the fastest setup

Public folder:
- [Dropbox prebuilt bundle folder](https://www.dropbox.com/scl/fo/f4t4tadtekpdkb93ebfst/AJMXiGDN9Uoz0ziOunY24rA?rlkey=sgn0z08ogppazqiu9nl8s8drb&st=gko1xbo1&dl=0)

You need:
- `package_method_helper.duckdb`
- `package_method_helper.summary.json`

Put them in:
- `work/generated/duckdb/`

There are two ways to get them:

1. Manual download
- open the Dropbox folder
- download the two files above
- place them in `work/generated/duckdb/`

2. Scripted download
- only if the maintainer gives you a direct ZIP URL

```bash
export PACKAGE_METHOD_HELPER_PREBUILT_DUCKDB_URL="https://example.com/package_method_helper_duckdb_bundle.zip"
python3 skills/package-method-helper/scripts/download_prebuilt_duckdb.py --json
```

Important:
- this script needs a direct file or ZIP URL
- a folder-view page is not enough

### Path B — Create your own embeddings from the published starter chunk bundle

Choose this if:
- you want to use your own embedding model or vendor
- you do not want to rebuild the private corpus
- you only need the published starting set of packages

From the same Dropbox folder, download:
- `package_method_helper_starter_embedding_chunks_bundle.zip`

That bundle includes:
- the curated top-50 package starter set for `r`, `python`, and `stata`
- `package_method_helper_r_embedding_chunks.jsonl`
- `package_method_helper_python_embedding_chunks.jsonl`
- `package_method_helper_stata_embedding_chunks.jsonl`
- matching `.manifest.json` files

Current starter set coverage:
- `r`: `1320` retrieval records
- `python`: `2184` retrieval records
- `stata`: `565` retrieval records

Unzip the bundle, then run embeddings against one language file at a time.

Example:

```bash
python3 skills/package-method-helper/scripts/embed_chunks_openai.py \
  --input-jsonl /path/to/package_method_helper_python_embedding_chunks.jsonl \
  --output-jsonl work/generated/embeddings/package_method_helper_python_embeddings.jsonl \
  --model text-embedding-3-small
```

### Path C — Build DuckDB locally

Choose this if:
- you want to ingest new packages
- you want to rebuild after corpus changes
- you want to point the skill at your own collection

Example:

```bash
python3 skills/package-method-helper/scripts/build_package_method_helper_duckdb.py \
  --collection-root /path/to/package_methods_top50_language_upload_tasks \
  --comparisons-root /path/to/package_methods_top50_sync_safe/00_comparisons \
  --output-db work/generated/duckdb/package_method_helper.duckdb
```

## Install the skill

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

Restart the agent session after install.

## Set up your OpenAI API key safely

Official references:
- [OpenAI quickstart](https://platform.openai.com/docs/quickstart)
- [Embeddings guide](https://platform.openai.com/docs/guides/embeddings)
- [Embeddings API reference](https://platform.openai.com/docs/api-reference/embeddings)
- [API key dashboard](https://platform.openai.com/api-keys)
- [How to create/find your API key](https://help.openai.com/en/articles/4936850-how-to-create-and-use-an-api-key)
- [API key safety best practices](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)

Rules:
- never commit the key
- never hard-code it in scripts
- never put it in browser-side code
- prefer environment variables or a local `.env`

### Option 1 — Current shell only

#### macOS / Linux

```bash
export OPENAI_API_KEY="your_api_key_here"
echo "$OPENAI_API_KEY"
```

#### Windows PowerShell

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
echo $env:OPENAI_API_KEY
```

### Option 2 — Persistent local shell setup

#### zsh

```bash
echo 'export OPENAI_API_KEY="your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

#### bash

```bash
echo 'export OPENAI_API_KEY="your_api_key_here"' >> ~/.bash_profile
source ~/.bash_profile
```

### Option 3 — Local `.env`

```bash
cp .env.example .env
```

Then edit `.env` locally and add:

```env
OPENAI_API_KEY=your_api_key_here
```

The bundled embedding script checks:
1. `OPENAI_API_KEY` from the environment
2. local `.env` if present

## Verify the setup

### Verify DuckDB works

```bash
python3 skills/package-method-helper/scripts/query_package_method_helper_duckdb.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --package fixest \
  --query "fixed effects clustered standard errors" \
  --json
```

You should get:
- a package hit for `fixest`
- a language-gated result
- `follow_up` context in the JSON

### Verify embedding setup works

Export a language-bounded chunk file first:

```bash
python3 skills/package-method-helper/scripts/export_embedding_chunks.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language python \
  --output-jsonl work/generated/duckdb/package_method_helper_python_embedding_chunks.jsonl
```

Then embed it:

```bash
python3 skills/package-method-helper/scripts/embed_chunks_openai.py \
  --input-jsonl work/generated/duckdb/package_method_helper_python_embedding_chunks.jsonl \
  --output-jsonl work/generated/embeddings/package_method_helper_python_embeddings.jsonl \
  --model text-embedding-3-small
```

## Common mistakes

### “The download script does not work”

Usually means:
- you passed a folder-view URL, not a direct ZIP/file URL

Fix:
- use a direct release asset URL
- or download the files manually

### “The embedding script says OPENAI_API_KEY is not set”

Fix:
- export the key in your current shell
- or create a local `.env`
- then open a new terminal if you used persistent shell setup

### “The query script returns an error about language”

That is expected behavior when the query is ambiguous.

Fix:
- pass `--language`
- or pass an exact package name

### “I only want to use the packaged corpus”

Do not start with acquisition or ingest workflows.
Use:
1. prebuilt DuckDB
2. or the published starter chunk bundle if you only need your own embeddings
3. query script
4. safe chunk export
5. embedding script

## Recommended safe workflow

For most users:

1. install the skill
2. install Python dependencies
3. get the prebuilt DuckDB
4. verify the query path with `fixest`
5. set `OPENAI_API_KEY` locally
6. export one language-bounded chunk file
7. embed that file

Only move to acquisition, paper, or ingest workflows after the basic query path is working.
