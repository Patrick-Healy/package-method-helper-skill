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
2. Classify the package role, safety class, task tags, and decision tags.
3. Identify the top 3 to 8 user-facing functions or commands.
4. Generate summary, overview, decision, function, pattern, and chunk files from the templates.
5. If the package is expert-level and a methods paper exists, add the paper layer.
6. Validate that all generated files match the expected schema.

## Recommended sources

- R: CRAN reference index, DESCRIPTION, vignette or pkgdown docs
- Stata: SSC help files, official help pages, package website
- Python: project docs, PyPI, API reference, repository README

## Quality bar

- Do not fabricate missing function details.
- Keep uncertain fields marked for review.
- When in doubt on safety class, choose the more restrictive class.
- Use the current corpus schema, not an improvised one.
