# Ingest Workflow

Use this after you have already created either:
- a full package gap-fill bundle, or
- a paper-layer bundle for an existing package.

The workflow is intentionally split into two commands:
1. create a reviewable approval plan
2. apply the approved ingest and optionally rebuild DuckDB

## 1. Create an approval plan

This does not modify the collection. It resolves the target task and shard, checks whether the package already exists, and writes a reviewable manifest.

Example: add a new R package bundle

```bash
python3 skills/package-method-helper/scripts/plan_collection_ingest.py \
  --collection-root /path/to/package_methods_top50_language_upload_tasks \
  --bundle-root /path/to/generated_gap_fill_bundle \
  --language r \
  --package mediation \
  --output-root work/generated/ingest_plans \
  --json
```

Example: add a methods-paper layer to an existing package

```bash
python3 skills/package-method-helper/scripts/plan_collection_ingest.py \
  --collection-root /path/to/package_methods_top50_language_upload_tasks \
  --bundle-root /path/to/generated_paper_layers \
  --language r \
  --package fixest \
  --output-root work/generated/ingest_plans \
  --json
```

Outputs:
- `ingest_approval_manifest.json`
- `ingest_approval.md`

The plan includes:
- detected action type
- target task and shard
- whether the package already exists
- every source-to-target file mapping
- the follow-up ingest command

## 2. Apply the approved ingest

The apply step requires `--approve` so it cannot run accidentally.

```bash
python3 skills/package-method-helper/scripts/ingest_collection_bundle.py \
  --approval-manifest work/generated/ingest_plans/r/fixest/ingest_approval_manifest.json \
  --approve \
  --rebuild-db \
  --output-db work/generated/duckdb/package_method_helper.duckdb \
  --json
```

What it does:
- copies the approved files into the target shard
- refreshes `shard_manifest.json`
- refreshes `language_upload_manifest.json`
- refreshes `master_manifest.json`
- optionally rebuilds DuckDB so the new files are immediately queryable

## Supported ingest modes

### Package addition

Expected source bundle shape:
- `raw_docs/{lang}/{package}.md`
- `raw_docs/{lang}/{package}.meta.json`
- `package_manifests/{lang}/{package}.json`
- `package_doc_collection/cards/...`
- `package_doc_collection/chunks/...`

The planner chooses the least-loaded shard in the language task.

### Paper-layer update

Expected source bundle shape:
- `{lang}/{package}/paper_layer_manifest.json`
- `{lang}/{package}/paper_{lang}_{package}.md`
- `{lang}/{package}/equation_{lang}_{package}.md`
- `{lang}/{package}/bridge_{lang}_{package}.md`
- optional `{lang}/{package}/updated_package_manifest.json`

The planner requires the package to already exist and targets the shard that already contains that package.

## Safety notes

- Always review the approval markdown before running the apply step.
- The planner refuses to treat an already-present package as a fresh package addition.
- The paper-layer workflow refuses to target a package that does not already exist.
- Rebuild the DuckDB index after ingest if you expect the new material to be searchable immediately.
