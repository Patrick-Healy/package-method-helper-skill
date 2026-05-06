# Doc Acquisition Workflow

Use this when a package is missing from the verified corpus and you need a clean first-pass official doc bundle before chunking or ingest.

## Goal

Produce a small, provenance-preserving acquisition bundle:
- `acquisition_manifest.json`
- `official_doc.md`
- `official_doc.meta.json`

This is the pre-ingest step. It is not yet a full collection bundle.

## Standard command

```bash
python3 skills/package-method-helper/scripts/acquire_official_package_docs.py \
  --language r \
  --package mediation \
  --output-root work/generated/source_acquisition \
  --json
```

## Source priorities

### R

Default order:
1. `search.r-project.org/CRAN/refmans/<pkg>/html/<pkg>-package.html`
2. `search.r-project.org/CRAN/refmans/<pkg>/html/00Index.html`
3. `cran.r-project.org/web/packages/<pkg>/index.html`
4. `rdrr.io/cran/<pkg>/`

Metadata source:
- `cran.r-project.org/web/packages/<pkg>/DESCRIPTION`

Use `--doc-url` when the best official page is a pkgdown site or a function-specific reference page rather than the package root.

### Python

Default order:
1. project docs discovered from PyPI `project_urls`
2. Read the Docs or `docs.*` pages
3. other official project docs
4. PyPI project page

Metadata source:
- `https://pypi.org/pypi/<pkg>/json`

### Stata

Default order:
1. SSC `.sthlp`
2. SSC `.hlp`
3. SSC `.pkg`

Metadata source:
- `http://fmwww.bc.edu/repec/bocode/<first-letter>/<pkg>.pkg`

Use `--doc-url` when the package is not on SSC and the authoritative docs live on GitHub or a project website.

## Output contract

`acquisition_manifest.json` records:
- language and package
- source resolution candidates
- selected primary doc URL
- selected repository URL when available
- registry metadata
- content stats for the fetched doc

`official_doc.md` contains:
- a simple title line
- the fetched source URL
- normalized markdown from the official doc page

`official_doc.meta.json` contains:
- fetched URL
- content type
- markdown length
- code block count and detected languages
- SHA-256 digest of the normalized markdown

## When to stop here

Stop after acquisition if you only need:
- manual review
- source verification
- a doc bundle to hand off for later chunking

Continue to the gap-fill workflow only when you need:
- package manifest generation
- summary / decision / function cards
- collection-ready chunks
