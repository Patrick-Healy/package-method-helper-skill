# Collection Inventory

This skill expects a staged package corpus shaped like language upload tasks produced from the verified package collection.

## Suggested corpus root
- `work/generated/package_methods_top50_language_upload_tasks`

## Expected language tasks
- `01_r_upload`
- `02_python_upload`
- `03_stata_upload`

## Shared comparisons source
- `work/generated/package_methods_top50_sync_safe/00_comparisons`

## Current package budget in this repository
- R: 50
- Python: 50
- Stata: 50

## Indexed file types
- package manifests (`package_manifests/.../*.json`)
- raw docs (`raw_docs/.../*.md`)
- raw metadata sidecars (`raw_docs/.../*.meta.json`)
- cards (`package_doc_collection/cards/...`)
- chunks (`package_doc_collection/chunks/...`)
- optional shared comparisons

## Priority retrieval layers
1. `summary_card`
2. `decision_card`
3. `function_card`
4. `function_documentation`
5. `documentation`
6. raw docs

## Notes
- The DuckDB build is meant to be regenerated from local files, not treated as the source of truth.
- Package manifests carry the strongest structured metadata for task tags, safety classes, pairings, and top functions.
