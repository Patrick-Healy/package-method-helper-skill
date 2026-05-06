# Gap Fill Workflow

When the verified corpus does not contain a package, use the bundled templates in `assets/gap_fill_templates/` to generate a collection-ready bundle.

## Goal

Produce a package bundle with:
- `raw_docs/{lang}/{package}.md`
- `raw_docs/{lang}/{package}.meta.json`
- `package_manifests/{lang}/{package}.json`
- `package_doc_collection/cards/...`
- `package_doc_collection/chunks/...`

## Minimum workflow

1. Discover official docs and version metadata.
   - Start with `scripts/acquire_official_package_docs.py`.
   - Prefer registry-driven acquisition over ad hoc browsing:
     - R: CRAN refman / DESCRIPTION
     - Python: PyPI JSON + project docs
     - Stata: SSC `.pkg` + `.sthlp` / `.hlp`
2. Classify the package role, safety class, task tags, and decision tags.
3. Identify the top 3 to 8 user-facing functions or commands.
4. Generate summary, overview, decision, function, pattern, and chunk files from the templates.
5. If the package is expert-level and a methods paper exists, add the paper layer.
   - Fetch the source first with `scripts/acquire_methods_paper.py`.
   - Use `scripts/generate_paper_layer_from_source.py` to turn the paper source bundle into `paper_note`, `equation`, and `bridge` cards.
6. Create a reviewable ingest plan with `scripts/plan_collection_ingest.py`.
7. Apply the approved ingest with `scripts/ingest_collection_bundle.py` and rebuild DuckDB if the collection should be searchable immediately.
8. Validate that all generated files match the expected schema.

## Standard acquisition command

```bash
python3 skills/package-method-helper/scripts/acquire_official_package_docs.py \
  --language r \
  --package mediation \
  --output-root work/generated/source_acquisition \
  --json
```

Outputs:
- `acquisition_manifest.json`
- `official_doc.md`
- `official_doc.meta.json`

If the deterministic registry path is not enough, pass `--doc-url` with the exact official doc page you want to use.

## Recommended sources

- R: CRAN reference index, DESCRIPTION, vignette or pkgdown docs
- Stata: SSC help files, official help pages, package website
- Python: project docs, PyPI, API reference, repository README

## Quality bar

- Do not fabricate missing function details.
- Keep uncertain fields marked for review.
- When in doubt on safety class, choose the more restrictive class.
- Use the current corpus schema, not an improvised one.
