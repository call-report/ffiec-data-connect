"""Build example notebooks as JSON files.

Usage: python examples/_build_notebooks.py

Keeps notebook content in one place, makes review easier than editing JSON directly.
Run from repo root.
"""

import json
from pathlib import Path


def md(*lines: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": ["\n".join(lines)],
    }


def code(*lines: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": ["\n".join(lines)],
    }


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


# ---------------------------------------------------------------------------
# 01_quickstart.ipynb
# ---------------------------------------------------------------------------

quickstart = notebook([
    md(
        "# Quickstart: Your First FFIEC API Call",
        "",
        "Goal: make one API call in under 2 minutes and confirm your credentials work.",
        "",
        "**Prerequisites:**",
        "1. `pip install ffiec-data-connect`",
        "2. A JWT bearer token from https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx (Account Details tab)",
        "3. Token stored in `FFIEC_BEARER_TOKEN` environment variable (safer than hard-coding)",
    ),
    md("## Step 1: Load credentials"),
    code(
        "import os",
        "from ffiec_data_connect import OAuth2Credentials",
        "",
        "creds = OAuth2Credentials(",
        "    username=os.environ['FFIEC_USERNAME'],",
        "    bearer_token=os.environ['FFIEC_BEARER_TOKEN'],",
        ")",
        "",
        "# Token expiry is auto-detected from the JWT payload",
        "print(f'Token expires: {creds.token_expires}')",
        "print(f'Expired? {creds.is_expired}')",
    ),
    md(
        "## Step 2: Fetch available Call Report reporting periods",
        "",
        "This is the lightest-weight endpoint — a great first call to verify your credentials.",
    ),
    code(
        "from ffiec_data_connect import collect_reporting_periods",
        "",
        "periods = collect_reporting_periods(creds, series='call')",
        "",
        "print(f'Got {len(periods)} reporting periods')",
        "print(f'Earliest: {periods[0]}')",
        "print(f'Latest:   {periods[-1]}')",
    ),
    md(
        "## Step 3: Get data for one bank",
        "",
        "We'll use the **second-to-last** reporting period — the very latest period is often a future quarter that institutions haven't filed for yet.",
    ),
    code(
        "from ffiec_data_connect import collect_data",
        "",
        "# Bank of America, N.A. — RSSD 480228",
        "# Use periods[-2] to avoid the (possibly unfiled) latest period",
        "target_period = periods[-2]",
        "print(f'Fetching data for {target_period}...')",
        "",
        "df = collect_data(",
        "    creds,",
        "    reporting_period=target_period,",
        "    rssd_id='480228',",
        "    series='call',",
        "    output_type='pandas',",
        ")",
        "",
        "print(f'Got {len(df):,} data points')",
        "df.head()",
    ),
    md(
        "## That's it!",
        "",
        "You successfully:",
        "- Authenticated with the FFIEC REST API",
        "- Listed available reporting periods",
        "- Downloaded XBRL data for one institution",
        "",
        "**Next steps:**",
        "- [`02_bulk_download_call_reports.ipynb`](02_bulk_download_call_reports.ipynb) — time series for one bank",
        "- [`03_peer_group_analysis.ipynb`](03_peer_group_analysis.ipynb) — compare multiple banks",
        "- [`04_incremental_updates.ipynb`](04_incremental_updates.ipynb) — monitor new filings",
    ),
])


# ---------------------------------------------------------------------------
# 02_bulk_download_call_reports.ipynb
# ---------------------------------------------------------------------------

bulk_download = notebook([
    md(
        "# Bulk Download: Time Series for One Bank",
        "",
        "Goal: pull Call Report XBRL data for one bank across several quarters, combine it into a single DataFrame, and plot a metric over time.",
        "",
        "**Use case:** You're tracking how a bank's total assets, loans, or deposits have evolved quarter-over-quarter.",
        "",
        "**Tip:** The library's built-in rate limiter (2500 req/hr) means you can safely pull dozens of quarters in sequence without worrying about throttling.",
    ),
    md("## Setup"),
    code(
        "import os",
        "import pandas as pd",
        "from ffiec_data_connect import (",
        "    OAuth2Credentials,",
        "    collect_data,",
        "    collect_reporting_periods,",
        ")",
        "",
        "creds = OAuth2Credentials(",
        "    username=os.environ['FFIEC_USERNAME'],",
        "    bearer_token=os.environ['FFIEC_BEARER_TOKEN'],",
        ")",
    ),
    md(
        "## Pick a bank and a date range",
        "",
        "For this example: Bank of America (RSSD 480228), last 8 quarters.",
    ),
    code(
        "RSSD_ID = '480228'  # Bank of America, N.A.",
        "NUM_QUARTERS = 8",
        "",
        "all_periods = collect_reporting_periods(creds, series='call')",
        "# Skip the latest period — it may be a future quarter not yet filed",
        "target_periods = all_periods[-(NUM_QUARTERS + 1):-1]",
        "",
        "print(f'Fetching {len(target_periods)} quarters:')",
        "for p in target_periods:",
        "    print(f'  {p}')",
    ),
    md(
        "## Fetch each quarter",
        "",
        "Each call returns the full XBRL filing. We tag each row with its reporting period so we can concatenate into a long-format DataFrame.",
    ),
    code(
        "quarterly_data = []",
        "",
        "for period in target_periods:",
        "    print(f'Fetching {period}...', end=' ')",
        "    df = collect_data(",
        "        creds,",
        "        reporting_period=period,",
        "        rssd_id=RSSD_ID,",
        "        series='call',",
        "        output_type='pandas',",
        "    )",
        "    df['reporting_period'] = period",
        "    quarterly_data.append(df)",
        "    print(f'{len(df)} items')",
        "",
        "combined = pd.concat(quarterly_data, ignore_index=True)",
        "print(f'\\nCombined: {len(combined):,} rows')",
    ),
    md(
        "## Extract one metric across time",
        "",
        "Call Report data uses MDRM codes to identify individual data points. For example:",
        "- `RCFD2170` — Total assets (consolidated)",
        "- `RCFD2200` — Total deposits",
        "- `RCFD2122` — Total loans and leases, net",
        "",
        "See the [Call Report MDRM Data Dictionary](https://cdr.ffiec.gov/public/ManageFacsimiles.aspx) for the full list.",
    ),
    code(
        "# Extract total assets over time",
        "MDRM_TOTAL_ASSETS = 'RCFD2170'",
        "",
        "time_series = (",
        "    combined[combined['mdrm'] == MDRM_TOTAL_ASSETS]",
        "    [['reporting_period', 'int_data']]",
        "    .rename(columns={'int_data': 'total_assets_thousands'})",
        "    .sort_values('reporting_period')",
        "    .reset_index(drop=True)",
        ")",
        "",
        "time_series",
    ),
    md("## Plot it"),
    code(
        "import matplotlib.pyplot as plt",
        "",
        "fig, ax = plt.subplots(figsize=(10, 5))",
        "ax.plot(time_series['reporting_period'], time_series['total_assets_thousands'] / 1e6, marker='o')",
        "ax.set_title(f'Total Assets Over Time — RSSD {RSSD_ID}')",
        "ax.set_xlabel('Reporting Period')",
        "ax.set_ylabel('Total Assets ($B)')",
        "ax.grid(True, alpha=0.3)",
        "plt.xticks(rotation=45)",
        "plt.tight_layout()",
        "plt.show()",
    ),
    md(
        "## Save for later analysis",
        "",
        "For production pipelines, save the combined DataFrame to Parquet — efficient, preserves dtypes, and fast to reload.",
    ),
    code(
        "combined.to_parquet('bank_480228_8q.parquet', index=False)",
        "print(f'Saved {len(combined):,} rows')",
    ),
])


# ---------------------------------------------------------------------------
# 03_peer_group_analysis.ipynb
# ---------------------------------------------------------------------------

peer_group = notebook([
    md(
        "# Peer Group Analysis",
        "",
        "Goal: identify a peer group of banks (e.g., all banks in a single state) and pull comparable metrics across the group for one reporting period.",
        "",
        "**Use case:** Comparing your institution's ratios against peers, benchmarking, regulatory analysis.",
    ),
    md("## Setup"),
    code(
        "import os",
        "import pandas as pd",
        "from ffiec_data_connect import (",
        "    OAuth2Credentials,",
        "    collect_data,",
        "    collect_filers_on_reporting_period,",
        "    collect_reporting_periods,",
        ")",
        "",
        "creds = OAuth2Credentials(",
        "    username=os.environ['FFIEC_USERNAME'],",
        "    bearer_token=os.environ['FFIEC_BEARER_TOKEN'],",
        ")",
    ),
    md("## Step 1: Get the panel of reporters for a period"),
    code(
        "periods = collect_reporting_periods(creds, series='call')",
        "# Use second-to-last period — latest may be a future quarter not yet filed",
        "latest = periods[-2]",
        "print(f'Using reporting period: {latest}')",
        "",
        "panel = collect_filers_on_reporting_period(",
        "    creds,",
        "    reporting_period=latest,",
        "    output_type='pandas',",
        ")",
        "",
        "print(f'Panel has {len(panel):,} institutions')",
        "panel.head()",
    ),
    md("## Step 2: Filter to your peer group"),
    code(
        "# Example: all banks in Rhode Island",
        "TARGET_STATE = 'RI'",
        "",
        "peers = panel[panel['state'] == TARGET_STATE].copy()",
        "print(f'Found {len(peers)} banks in {TARGET_STATE}')",
        "peers[['rssd', 'name', 'city', 'state']].head(10)",
    ),
    md(
        "## Step 3: Pull Call Report data for each peer",
        "",
        "This makes N API calls — one per peer. With the built-in rate limiter (2500 req/hr), you can comfortably handle a few hundred peers. For larger groups, consider running overnight or splitting the work.",
    ),
    code(
        "import time",
        "",
        "peer_data = []",
        "",
        "for idx, row in peers.iterrows():",
        "    rssd = row['rssd']",
        "    name = row['name']",
        "    print(f'[{idx+1}/{len(peers)}] {rssd} — {name[:50]}', end=' ')",
        "    try:",
        "        df = collect_data(",
        "            creds,",
        "            reporting_period=latest,",
        "            rssd_id=rssd,",
        "            series='call',",
        "            output_type='pandas',",
        "        )",
        "        df['rssd'] = rssd",
        "        df['name'] = name",
        "        peer_data.append(df)",
        "        print(f'OK ({len(df)} items)')",
        "    except Exception as e:",
        "        print(f'FAIL: {type(e).__name__}')",
        "",
        "all_peer_data = pd.concat(peer_data, ignore_index=True)",
        "print(f'\\nTotal rows: {len(all_peer_data):,}')",
    ),
    md(
        "## Step 4: Extract comparable metrics",
        "",
        "Pivot the long-format data into a wide comparison table. Each row is a bank, each column is a metric.",
    ),
    code(
        "# Common Call Report MDRM codes",
        "METRICS = {",
        "    'RCFD2170': 'total_assets',",
        "    'RCFD2200': 'total_deposits',",
        "    'RCFD2122': 'net_loans_leases',",
        "    'RCFD3210': 'total_equity',",
        "}",
        "",
        "subset = all_peer_data[all_peer_data['mdrm'].isin(METRICS.keys())].copy()",
        "subset['metric'] = subset['mdrm'].map(METRICS)",
        "",
        "comparison = (",
        "    subset.pivot_table(",
        "        index=['rssd', 'name'],",
        "        columns='metric',",
        "        values='int_data',",
        "        aggfunc='first',",
        "    )",
        "    .reset_index()",
        "    .sort_values('total_assets', ascending=False)",
        ")",
        "",
        "# Convert from thousands to millions for readability",
        "for col in METRICS.values():",
        "    if col in comparison.columns:",
        "        comparison[col] = comparison[col] / 1_000",
        "",
        "comparison.head(10)",
    ),
    md("## Step 5: Compute derived ratios"),
    code(
        "comparison['loans_to_deposits'] = (",
        "    comparison['net_loans_leases'] / comparison['total_deposits']",
        ")",
        "comparison['equity_to_assets'] = (",
        "    comparison['total_equity'] / comparison['total_assets']",
        ")",
        "",
        "comparison[['name', 'total_assets', 'loans_to_deposits', 'equity_to_assets']].head(10)",
    ),
    md(
        "## Tips for larger peer groups",
        "",
        "- **Hundreds of banks**: use `AsyncCompatibleClient` for parallel fetches (see the REST demo notebook)",
        "- **Thousands of banks**: split the work into batches, checkpoint to disk, handle failures gracefully",
        "- **State subsets**: the `panel` DataFrame has `state`, `city`, `fdic_cert_number`, and more — filter however you need",
    ),
])


# ---------------------------------------------------------------------------
# 04_incremental_updates.ipynb
# ---------------------------------------------------------------------------

incremental = notebook([
    md(
        "# Incremental Updates: Monitor New Filings",
        "",
        "Goal: for an ETL or monitoring workflow, find banks that have filed (or amended their filing) since your last check.",
        "",
        "**Use case:**",
        "- Nightly cron job that pulls only new/amended filings",
        "- Regulatory dashboard that refreshes as institutions file",
        "- Audit trail of filing timestamps",
        "",
        "The FFIEC REST API exposes two endpoints that support this pattern:",
        "- `collect_filers_since_date` — just the RSSD IDs that filed after a given date",
        "- `collect_filers_submission_date_time` — RSSD IDs **plus** the exact submission timestamp",
    ),
    md("## Setup"),
    code(
        "import os",
        "from datetime import datetime, timedelta",
        "import pandas as pd",
        "from ffiec_data_connect import (",
        "    OAuth2Credentials,",
        "    collect_data,",
        "    collect_filers_since_date,",
        "    collect_filers_submission_date_time,",
        ")",
        "",
        "creds = OAuth2Credentials(",
        "    username=os.environ['FFIEC_USERNAME'],",
        "    bearer_token=os.environ['FFIEC_BEARER_TOKEN'],",
        ")",
    ),
    md(
        "## Pattern 1: Which RSSD IDs filed since last run?",
        "",
        "In a real ETL job, you'd persist `last_run_date` to a database or file between runs. Here we'll simulate it as 30 days ago.",
    ),
    code(
        "# Your current reporting period (the quarter you're pulling)",
        "REPORTING_PERIOD = '12/31/2024'",
        "",
        "# Last time your ETL ran",
        "last_run = (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y')",
        "print(f'Looking for filings since: {last_run}')",
        "",
        "new_filers = collect_filers_since_date(",
        "    creds,",
        "    reporting_period=REPORTING_PERIOD,",
        "    since_date=last_run,",
        ")",
        "",
        "print(f'{len(new_filers)} institutions filed since {last_run}')",
        "print(f'First 5: {new_filers[:5]}')",
    ),
    md(
        "## Pattern 2: Get the submission timestamps",
        "",
        "When you need to know **exactly when** each institution filed (for SLA monitoring, audit trails, or ordering by recency).",
    ),
    code(
        "submissions = collect_filers_submission_date_time(",
        "    creds,",
        "    since_date=last_run,",
        "    reporting_period=REPORTING_PERIOD,",
        "    output_type='pandas',",
        ")",
        "",
        "print(f'Got {len(submissions)} submissions')",
        "submissions.head()",
    ),
    md("## Find the most recent filers"),
    code(
        "# Sort by submission time, newest first",
        "submissions['datetime'] = pd.to_datetime(submissions['datetime'])",
        "recent = submissions.sort_values('datetime', ascending=False).head(20)",
        "",
        "print('Most recent filings:')",
        "recent[['rssd', 'datetime']]",
    ),
    md(
        "## ETL pattern: fetch data only for new filers",
        "",
        "Instead of re-downloading every bank's XBRL every night, only pull the ones that filed or amended since your last run.",
    ),
    code(
        "# Simulated ETL loop — in production you'd persist results to a database",
        "updated_records = []",
        "",
        "# Take first 5 for the example; in production you'd iterate all new_filers",
        "for rssd in new_filers[:5]:",
        "    print(f'Fetching {rssd}...', end=' ')",
        "    try:",
        "        df = collect_data(",
        "            creds,",
        "            reporting_period=REPORTING_PERIOD,",
        "            rssd_id=rssd,",
        "            series='call',",
        "            output_type='pandas',",
        "        )",
        "        df['rssd'] = rssd",
        "        updated_records.append(df)",
        "        print(f'OK ({len(df)} items)')",
        "    except Exception as e:",
        "        print(f'FAIL: {e}')",
        "",
        "updated = pd.concat(updated_records, ignore_index=True) if updated_records else pd.DataFrame()",
        "print(f'\\nUpdated {len(updated_records)} institutions, {len(updated):,} total data points')",
    ),
    md(
        "## Production checklist",
        "",
        "For a real scheduled job:",
        "",
        "1. **Persist `last_run_date`** — store it in your database or a small state file",
        "2. **Handle failures** — if one bank errors, don't fail the whole run (wrap in try/except, log failures)",
        "3. **Idempotency** — upsert by `(rssd, reporting_period, mdrm)` so re-runs are safe",
        "4. **Token rotation** — JWT tokens expire every 90 days; `creds.is_expired` is your friend",
        "5. **Rate limiting** — built-in limiter handles the 2500/hr cap, but for very large panels consider async + batching",
        "6. **Monitoring** — log counts of fetched banks, record durations, alert on anomalies",
    ),
])


# ---------------------------------------------------------------------------
# Write all notebooks
# ---------------------------------------------------------------------------

NOTEBOOKS = {
    "01_quickstart.ipynb": quickstart,
    "02_bulk_download_call_reports.ipynb": bulk_download,
    "03_peer_group_analysis.ipynb": peer_group,
    "04_incremental_updates.ipynb": incremental,
}


def main() -> None:
    out_dir = Path(__file__).parent
    for name, nb in NOTEBOOKS.items():
        path = out_dir / name
        with open(path, "w") as f:
            json.dump(nb, f, indent=1)
            f.write("\n")
        print(f"Wrote {path.relative_to(Path.cwd())} ({len(nb['cells'])} cells)")


if __name__ == "__main__":
    main()
