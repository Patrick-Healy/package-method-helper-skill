---
name: package-method-helper
description: "Use this skill when an empirical researcher needs package-aware code help, code annotation, workflow guidance, or collection gap handling for quantitative social science work in R, Python, or Stata. It is optimized for verified package documentation collections indexed locally through DuckDB, with safe fallbacks to direct file retrieval and web lookup when a package is missing."
---

# Package Method Helper

Help empirical researchers write and annotate analysis code in R, Python, and Stata using verified package documentation, explicit source labeling, and conservative retrieval rules.

Read only what you need:
- `references/duckdb_usage.md` for build, query, and embedding-export commands.
- `references/operating_rules.md` for language routing, search gates, source labels, and write-vs-annotate behavior.
- `references/collection_inventory.md` when you need to know what the bundled corpus contains.
- `references/embedding_setup.md` when preparing safe chunk exports for GPT embeddings or consuming precomputed embeddings.
- `references/gap_fill_workflow.md` when a package is missing and you need to generate a collection-ready bundle.

## Tool Contract

- Prefer the local DuckDB index over ad hoc grep or web search.
- If the DuckDB database does not exist, build it first with `scripts/build_package_method_helper_duckdb.py`.
- Query the index with `scripts/query_package_method_helper_duckdb.py`.
- When retrieval is ambiguous, require a literal package or primary-function hit before trusting results.
- Use direct file fallback inside the collection root before going to the web.
- Keep source confidence explicit:
  - `🟢 COLLECTION-VERIFIED`
  - `🔶 WEB-SOURCED (verify before use)`
  - `⚠️ DOMAIN KNOWLEDGE (not collection-verified)`
- Do not claim a package is verified unless it comes from the indexed corpus or direct file retrieval from that corpus.
- Treat web fallback as a gap and include an add-to-collection recommendation.

Resolve all bundled paths relative to the directory containing this `SKILL.md`. If the host agent exposes a skill-directory variable such as `${CLAUDE_SKILL_DIR}`, use it. Otherwise set `SKILL_DIR=/path/to/package-method-helper` in commands.

## Suggested Local Paths

These are recommended local paths inside a cloned repository or working directory:
- Collection root: `work/generated/package_methods_top50_language_upload_tasks`
- Shared comparisons root: `work/generated/package_methods_top50_sync_safe/00_comparisons`
- Default DuckDB output: `work/generated/duckdb/package_method_helper.duckdb`

If the user's corpus lives elsewhere, pass explicit paths to the build script and treat those as authoritative.

## Workflow

1. Detect mode: `WRITE` when the user describes what to build; `ANNOTATE` when code is already present.
2. Detect language before searching. If ambiguous, ask.
3. Build or open the DuckDB index.
4. Search the relevant language first, then the package, then the function or task.
5. Prefer this evidence order when available:
   - summary card
   - decision card
   - function card or function documentation
   - documentation chunks
   - raw docs
6. For multi-package workflows, search each package separately and state the workflow order.
7. If the package is missing from the corpus, use the gap-fill workflow and keep any non-collection answer explicitly labeled.

## Output Rules

- For verified package help, cite the collection label inline.
- For generated or annotated code, surface researcher decisions explicitly.
- For out-of-collection packages, recommend whether the package should be added and point to the bundled gap-fill templates.
- When exporting chunks for embeddings, use the safe export script rather than raw file copies so local paths and internal-only metadata stay out of the embedding payload.
