# Paper Acquisition Workflow

Use this when a package needs a methods-paper layer before you generate `paper_note`, `equation`, or `bridge` cards.

## Goal

Produce a small paper-source bundle:
- `paper_source_manifest.json`
- `paper_source.md`
- `paper_source.meta.json`

This is the pre-synthesis paper step. It is not yet a final paper card.

## Standard command

```bash
python3 skills/package-method-helper/scripts/acquire_methods_paper.py \
  --language stata \
  --package boottest \
  --output-root work/generated/paper_acquisition \
  --json
```

## Resolution rules

The script supports two paths:

1. **Known-paper map**
   - for a small set of stable packages with strong canonical paper URLs
2. **Manual override**
   - pass `--paper-url` for any package not in the known map

Manual override is the default fallback because paper discovery is less deterministic than package-doc discovery.

## Preferred source types

Prefer HTML landing pages or abstract pages over raw PDFs for the first pass:
- JSS article pages
- JMLR article pages
- JOSS paper pages
- IDEAS/RePEc abstract pages
- arXiv abstract pages

Those are easier to normalize to markdown safely than PDFs.

## Output contract

`paper_source_manifest.json` records:
- language and package
- candidate paper URLs
- selected paper URL
- paper source type
- content stats

`paper_source.md` contains:
- title
- source URL
- normalized markdown from the paper landing page

`paper_source.meta.json` contains:
- fetched URL
- content type
- source type
- capture scope
- markdown length
- code block count and detected languages
- SHA-256 digest

`capture_scope` distinguishes:
- `landing_page`
- `abstract_page`
- `long_form_html`
- `pdf_source`

Do not assume journal landing pages contain full paper text. Many high-quality sources only expose abstracts and article metadata in HTML.

## When to continue

Continue to paper-card generation when you need:
- `paper_note`
- `equation`
- `bridge`

## Generate the paper layer

After acquisition, generate the paper cards with:

```bash
python3 skills/package-method-helper/scripts/generate_paper_layer_from_source.py \
  --language r \
  --package fixest \
  --paper-source-root work/generated/paper_acquisition \
  --output-root work/generated/paper_layers \
  --json
```

If you already have a package manifest, pass `--package-manifest` and the generator will also emit an `updated_package_manifest.json` copy with:
- `content_presence.paper_card_count = 3`
- `status.has_paper_layer = true`

Stop at acquisition when you only need:
- source verification
- a reusable paper bundle for later synthesis
- a stress test of the paper-source workflow
