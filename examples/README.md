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

1. **Install**: `pip install ffiec-data-connect` (Python 3.11+)
2. **Get a token**: Register at [https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx](https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx) and generate a 90-day JWT bearer token from the Account Details tab
3. **Supply it** to the notebooks in whichever way is most convenient (see below)

## Supplying credentials

Each notebook's Step 0 defines a `get_credentials()` helper that checks three sources, in order, and uses the first one that has both a username and a token. Later cells just call `creds = get_credentials()`.

**Option A — Environment variables (best for automation / CI):**

```bash
export FFIEC_USERNAME='your_username'
export FFIEC_BEARER_TOKEN='eyJ...'
jupyter lab
```

**Option B — `.env` file (best for recurring local work):**

Create a `.env` file in the notebook's directory:

```dotenv
FFIEC_USERNAME=your_username
FFIEC_BEARER_TOKEN=eyJ...
```

Install the optional dep once: `pip install python-dotenv`. Add `.env` to your `.gitignore` — the file contains a live secret.

**Option C — Interactive form (best for quick one-off sessions):**

Leave both unset. Step 1 of each notebook calls `show_credentials_form()`, which renders an ipywidgets form right in the notebook — a username field, a masked password field, and a Submit button. Clicking Submit sets `creds` in the notebook namespace so downstream cells can use it.

```bash
pip install ipywidgets  # optional, but recommended for the form UI
```

If `ipywidgets` isn't installed, `show_credentials_form()` transparently falls back to terminal-style text prompts (`input()` + `getpass.getpass()`). You'll have to re-enter credentials when the kernel restarts — env vars or `.env` avoid that.

For fully scripted notebooks (no UI at all), call `creds = get_credentials()` instead — same resolution cascade, no widget rendered.

## Step 0: Dev setup & environment check

Every notebook (including [`ffiec_data_connect_rest_demo.ipynb`](../ffiec_data_connect_rest_demo.ipynb)) now starts with a **Step 0** cell that:

- Verifies Python >= 3.11 and that all required dependencies are importable (fails fast with a clear message if anything is missing).
- Warns on missing optional deps (`matplotlib`, `polars`, `pyarrow`) that some notebooks use for plotting or alternate output formats.
- Prints the resolved library version and path so you can confirm which copy of `ffiec_data_connect` you're actually running.
- Defines `get_credentials()` (see "Supplying credentials" above).

**Contributors** iterating on the library source can flip one variable to run the notebooks against the repo's `src/` tree instead of the pip-installed package — no `pip install -e .` required:

```python
# In Step 0:
USE_LOCAL_SRC = True   # prepends repo's src/ to sys.path
```

The cell walks upward from the notebook's CWD to locate `src/ffiec_data_connect/`, so it works whether you launched Jupyter from the repo root or from `examples/`. Restart the kernel when toggling this flag.

## Regenerating the example notebooks

Notebooks 01–04 are generated from [`_build_notebooks.py`](_build_notebooks.py) — **edit that file, not the `.ipynb` JSON**, then re-run:

```bash
python examples/_build_notebooks.py
```

The root `ffiec_data_connect_rest_demo.ipynb` is not generated; edit it directly.

## Common RSSD IDs (for testing)

| Bank | RSSD ID |
|---|---|
| JPMorgan Chase Bank, N.A. | 852218 |
| Bank of America, N.A. | 480228 |
| Wells Fargo Bank, N.A. | 451965 |
| Citibank, N.A. | 476810 |
| U.S. Bank N.A. | 504713 |

Find more at [FFIEC NIC Search](https://www.ffiec.gov/npw/).
