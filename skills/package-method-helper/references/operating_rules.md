# Operating Rules

## Source Labels

Every substantive claim should be labeled:
- `🟢 COLLECTION-VERIFIED` for DuckDB or direct file retrieval from the local corpus
- `🔶 WEB-SOURCED (verify before use)` for web fallback
- `⚠️ DOMAIN KNOWLEDGE (not collection-verified)` for uncited background reasoning

## Language Gate

Priority order:
1. Explicit user statement
2. Package names
3. Syntax cues
4. File extensions

If still ambiguous, ask the user before searching.

## Search Gates

1. Route to one language first.
1a. Do not do cross-language similarity search unless the user explicitly asks for it.
2. For multi-package workflows, search packages separately and state the workflow order.
3. Require a literal package name or primary-function hit before trusting retrieval.
4. Prefer summary, decision, and function layers before general documentation.
5. If the local index misses, use direct file fallback under the collection root.
6. Only then use web fallback.
7. For an add-to-collection path, run the official-doc acquisition workflow before building cards or chunks.
8. For a paper layer, acquire the paper landing page first; do not synthesize paper cards from memory.
9. Before modifying a collection, create a reviewable ingest plan.
10. Only apply collection changes after explicit approval and then rebuild the local index if the new material should be searchable immediately.

## Write Mode

Use when the researcher describes what to build.
- Gather: goal, language, data structure, outputs.
- Search the relevant packages.
- Write code using verified syntax when available.
- Surface researcher decisions explicitly.

## Annotate Mode

Use when code is already present.
- Parse packages and major functions first.
- Search package-by-package.
- Insert or report decision annotations with source labels.
- Flag expert-only packages and out-of-collection gaps.

## Common Pairings

Treat these as pre-validated default pairings, not automatic requirements:
- `reghdfe` → `esttab` → `coefplot`
- `csdid` → `coefplot`
- `MatchIt` → `fixest::feols`
- `ebalance` → `reghdfe`
- `psych::alpha` → `lavaan::cfa`
- `bacondecomp` → `csdid`
- `winsor2` → `reghdfe` → `esttab`
- `did_imputation` → `event_plot`
- `DoubleMLPLR` + `sklearn`
- `linearmodels.FamaMacBeth`

## Web Fallback

When a package is not verified locally:
1. State that the package is missing from the verified corpus.
2. Search official documentation first.
3. Keep all web-derived syntax marked `🔶`.
4. End with an add-to-collection recommendation.
5. If the package is important, use the bundled gap-fill workflow.
