# Language Gate Test Report

This repo now treats language as a hard retrieval gate.

## Contract

- build and publish three language-specific bundles only:
  - `r`
  - `python`
  - `stata`
- do not generate or rely on an `all` embedding bundle
- infer language from package names or syntax cues when possible
- fail closed when language is ambiguous
- reject explicit package/language mismatches
- allow cross-language similarity search only with `--allow-cross-language`
- attach follow-up edges after an exact package hit so agents can read sidecars, core cards, function docs, and adjacent packages without trusting a single top chunk

## Tests run

Automated smoke test:

```bash
python3 tests/run_smoke_tests.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --bundles-root work/generated/bundles
```

Checks:
- `fixest` resolves to `r`
- `fixest` follow-up includes summary, decision, and raw-meta edges
- `statsmodels` resolves to `python`
- `scikit-learn` alias resolves to `sklearn` in `python`
- `reghdfe` resolves to `stata`
- `reghdfe` follow-up includes adjacent package edges
- R syntax cue query resolves to `r`
- ambiguous no-language query fails the gate
- only `r/python/stata` bundle artifacts exist
- `all` bundle artifacts are absent

## Manual probes

Alias resolution:

```bash
python3 skills/package-method-helper/scripts/query_package_method_helper_duckdb.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --package scikit-learn \
  --query "classification pipeline cross validation" \
  --json
```

Observed:
- `effective_language = python`
- top package = `sklearn`

Ambiguous query rejection:

```bash
python3 skills/package-method-helper/scripts/query_package_method_helper_duckdb.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --query "fixed effects clustered standard errors" \
  --json
```

Observed:
- exit code `2`
- error `language_gate_failed`

Explicit mismatch rejection:

```bash
python3 skills/package-method-helper/scripts/query_package_method_helper_duckdb.py \
  --db work/generated/duckdb/package_method_helper.duckdb \
  --language stata \
  --package fixest \
  --query "fixed effects clustered standard errors" \
  --json
```

Observed:
- exit code `2`
- error `language_package_mismatch`

## Remaining tradeoff

Within a correctly gated language, ranking can still favor a strong function card over the package summary card for some task-heavy queries. That is acceptable for now because the cross-language false-positive problem is the higher-risk failure mode.
