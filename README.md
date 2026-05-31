# Budget Tracker

<div align="center">

_A headless monthly automation that turns bank transactions into Google Sheets._

</div>

Budget Tracker is an unattended financial automation. On the 1st of each month it authenticates with Plaid, pulls the previous month's transactions from linked accounts (a Chase credit card and a SchoolsFirst Federal Credit Union checking account), and writes them into a month-named copy of a Google Sheets template inside a year-based Drive folder. It backfills any months it missed, exports a raw CSV per month, and emails a summary with a link to each sheet. The only interactive step is a one-time Plaid Link authorization per institution. It is built to run from cron or launchd on a personal machine.

## Setup

1. Clone the repo.

   ```bash
   git clone https://github.com/joshuadarron/budget_tracker && cd budget_tracker
   ```

2. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

3. Enable Google APIs and add credentials. In the [Google Cloud Console](https://console.cloud.google.com/), create a project, enable the Drive, Sheets, and Gmail APIs, create OAuth 2.0 client credentials, download `credentials.json` to the repo root, and add your account as a test user on the OAuth consent screen.

4. Configure the environment. Copy `.env.example` to `.env` and fill it in.

   ```
   PLAID_CLIENT_ID=...
   PLAID_SECRET=...
   PLAID_ENV=sandbox            # flip to production after sandbox verified
   PLAID_REDIRECT_URI=          # https URI for OAuth banks in production
   PARENT_FOLDER_ID=...         # Drive folder holding the Template
   PLAID_ITEMS=chase,schoolsfirst
   ```

5. Link each institution once (interactive), then run the monthly job (headless).

   ```bash
   python link_accounts.py chase
   python link_accounts.py schoolsfirst
   python run.py
   ```

The link step opens a browser for Plaid Link and persists an access token. It is the consent grant and has no headless alternative. The run step pulls transactions, fills sheets, and sends the email with no browser and no human; this is what goes in cron, scheduled for the 1st.

Common commands:

| Command | Description |
|---|---|
| `python link_accounts.py <chase\|schoolsfirst>` | One-time interactive Plaid Link (sandbox login: `user_good` / `pass_good`) |
| `python run.py` | The recurring monthly job: sync, backfill, fill, notify |
| `python -m pytest tests/ -q` | Run the test suite |

## Requirements

Local prerequisites: Python 3, a Plaid account (sandbox or production keys), and a Google Cloud project with the Drive, Sheets, and Gmail APIs enabled. There is no database; state lives in local files.

| Layer | Technology |
|---|---|
| Language | Python 3 |
| Bank data | [plaid-python](https://github.com/plaid/plaid-python) 39.x, `/transactions/sync` (cursor-based, incremental) |
| Google APIs | google-api-python-client (Drive, Sheets, Gmail) |
| Link flow | Flask (serves the one-time Plaid Link locally) |
| State | `token.pickle` (Google OAuth), `plaid_items.json` (Plaid tokens, cursors, transaction ledger) |

State files hold credentials in the clear and are gitignored. Keep them off shared machines.

## What it does

A run syncs each linked institution through `/transactions/sync`, which is incremental: it returns everything since the stored cursor and advances it. Because sync is cursor-based and the sheet model is calendar-month, the two do not align, so sync writes into a per-institution ledger (upsert on added or modified, delete on removed, keyed by `transaction_id`) and month reads slice the ledger by date range.

Before processing the current previous month, the tool scans the Drive year folders and compares them against the range it should have generated, from the earliest linked month through last month. Any gap is a missed month. It generates sheets for all missed months in chronological order, so if the tool was offline for three months it backfills all three on the next run.

For each month it copies the `Template`, renames it by month number (e.g. `05` for May), clears the boilerplate rows, and fills in the posted transactions. It writes the same data to `exports/YYYY-MM.csv` as a raw record independent of Drive, then sends one summary email covering every month generated, with a transaction count and total spend per institution and a link to each sheet.

## Architecture

The two phases are deliberately separate. Link is interactive and runs once per institution; run is headless and recurring. They share nothing except the persisted access tokens.

Module boundaries are strict. `config.py` is the only reader of environment variables. All persisted state goes behind a repository, `PlaidStore`, so no other module reads or writes `plaid_items.json` directly. Library modules never call `sys.exit`; they return control to `main.py`, which decides flow. This is what makes backfill work: an existing month sheet is skipped silently and the run continues to the next month, rather than exiting.

Chase requires OAuth, which is production-only. The Plaid Link flow handles the OAuth redirect round trip: it creates the link token with a registered HTTPS `redirect_uri`, and an `/oauth` route re-initializes Link with `receivedRedirectUri` to resume after the bank redirect. The local server uses a self-signed certificate so `https://localhost:5000/oauth` is a valid redirect target for testing.

Sign handling is the main domain quirk. Plaid reports spend as positive, which matches the sheet, but a credit card payment to Chase arrives negative. The current build keeps spend-positive rows only and excludes non-positive amounts. Only posted transactions are written; pending ones are skipped.

## Status

In personal use. Sandbox is the default Plaid environment; production is enabled per institution after sandbox is verified. Production bills per call, so the design refreshes on a monthly cadence and no more. The codebase is the source of truth; `.claude/CLAUDE.md` documents the intended architecture in full.

Maintained by [Joshua Phillips](https://github.com/joshuadarron).
