# Publishing The Prebuilt DuckDB

This repository is designed so the DuckDB artifact stays out of git and is distributed as a separate binary download.

## Recommended distribution model

Use this priority order:
1. GitHub release asset for `package_method_helper_duckdb_bundle.zip`
2. direct file URL from another binary host
3. Dropbox folder link only for manual fallback

Reason:
- GitHub release assets are stable and scriptable
- direct file URLs work with the bundled downloader
- Dropbox folder-view links are not reliable automation targets

## Build the bundle

From the repo root:

```bash
python3 skills/package-method-helper/scripts/build_prebuilt_duckdb_bundle.py \
  --db-path /absolute/path/to/package_method_helper.duckdb \
  --summary-path /absolute/path/to/package_method_helper.summary.json \
  --output-dir /absolute/path/to/distribution_folder \
  --move-source \
  --include-readme \
  --json
```

This writes:
- `package_method_helper.duckdb`
- `package_method_helper.summary.json`
- `package_method_helper_duckdb_bundle.zip`
- `prebuilt_duckdb_manifest.json`
- optional `README.txt`

Use `--move-source` when you want the distribution folder to become the canonical artifact location.

## Publish to GitHub Releases

Recommended asset name:
- `package_method_helper_duckdb_bundle.zip`

Recommended direct URL shape after release:
- `https://github.com/Patrick-Healy/package-method-helper-skill/releases/download/<tag>/package_method_helper_duckdb_bundle.zip`

Then users can install with:

### macOS / Linux

```bash
export PACKAGE_METHOD_HELPER_PREBUILT_DUCKDB_URL="https://github.com/Patrick-Healy/package-method-helper-skill/releases/download/<tag>/package_method_helper_duckdb_bundle.zip"
python3 skills/package-method-helper/scripts/download_prebuilt_duckdb.py --json
```

### Windows PowerShell

```powershell
$env:PACKAGE_METHOD_HELPER_PREBUILT_DUCKDB_URL = "https://github.com/Patrick-Healy/package-method-helper-skill/releases/download/<tag>/package_method_helper_duckdb_bundle.zip"
python skills/package-method-helper/scripts/download_prebuilt_duckdb.py --json
```

## Manual Dropbox fallback

If there is no direct asset URL yet, provide the Dropbox folder link for manual download and tell users to place:
- `package_method_helper.duckdb`
- `package_method_helper.summary.json`

into:
- `work/generated/duckdb/`

## Minimum user requirements

For prebuilt DB use only:
- Python 3.10+
- `duckdb>=1.0.0`

For embedding creation too:
- `openai>=1.0.0`
- local `OPENAI_API_KEY`
