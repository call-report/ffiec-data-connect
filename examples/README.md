# Examples

Practical, task-focused examples for common FFIEC Data Connect workflows.

Each notebook solves one specific problem. For a full tour of every API method, see [`ffiec_data_connect_rest_demo.ipynb`](../ffiec_data_connect_rest_demo.ipynb) at the repository root.

## Notebooks

| Notebook | Use case |
|---|---|
| [`01_quickstart.ipynb`](01_quickstart.ipynb) | First API call in under 2 minutes |
| [`02_bulk_download_call_reports.ipynb`](02_bulk_download_call_reports.ipynb) | Download Call Reports for one bank across many quarters (time series) |
| [`03_peer_group_analysis.ipynb`](03_peer_group_analysis.ipynb) | Identify peer banks and pull comparable metrics |
| [`04_incremental_updates.ipynb`](04_incremental_updates.ipynb) | Track new filings since a date (ETL / monitoring pattern) |

## Before You Start

1. **Install**: `pip install ffiec-data-connect` (Python 3.10+)
2. **Get a token**: Register at [https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx](https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx) and generate a 90-day JWT bearer token from the Account Details tab
3. **Store it safely**: Set `FFIEC_USERNAME` and `FFIEC_BEARER_TOKEN` as environment variables — never hard-code tokens in notebooks

```bash
export FFIEC_USERNAME='your_username'
export FFIEC_BEARER_TOKEN='eyJ...'
jupyter lab
```

## Common RSSD IDs (for testing)

| Bank | RSSD ID |
|---|---|
| JPMorgan Chase Bank, N.A. | 852218 |
| Bank of America, N.A. | 480228 |
| Wells Fargo Bank, N.A. | 451965 |
| Citibank, N.A. | 476810 |
| U.S. Bank N.A. | 504713 |

Find more at [FFIEC NIC Search](https://www.ffiec.gov/npw/).
