# CLAUDE.md

Context for working in this repo. Read before making changes.

## What this is

A headless monthly financial automation. On the 1st of each month (or on any
run), it:

1. Authenticates with Plaid to pull the previous month's transactions from
   linked bank accounts (Chase credit card, SchoolsFirst Federal Credit Union
   checking).
2. Exports those transactions as CSV (or converts Plaid's response into one).
3. Copies a Google Sheets `Template` into a year-based Drive folder structure,
   renames it by month (e.g. `05` for May), and fills it with the transaction
   data.
4. Checks the Drive directory for missing months and backfills any gaps. If the
   tool was offline for three months, it generates all three on the next run.
5. Sends the user an email with a summary and a prominent link/button to open
   the completed sheet.

Built to run unattended (cron / launchd) on a personal machine. The only
interactive step is the one-time Plaid Link authorization per institution.

## Stack

- Python 3
- `plaid-python` 39.x: transaction pull via `/transactions/sync` (cursor-based,
  incremental). Sandbox and Production envs only (no Development).
- `google-api-python-client`: Drive API (folder/file ops), Sheets API (template
  fill), Gmail API (notification email).
- `flask`: serves the one-time Plaid Link flow locally.
- No database. State lives in local files: `token.pickle` (Google OAuth),
  `plaid_items.json` (Plaid access tokens, sync cursors, transaction ledger).

## Module map

```
run.py                          entrypoint -> main.run()
link_accounts.py                one-time interactive Plaid linker
src/template_automation/
  config.py                     single env reader. nothing else calls os.getenv
  auth.py                       Google OAuth + service builders (Drive, Sheets, Gmail)
  drive.py                      template copy, rename, folder creation, gap detection
  sheets.py                     row deletion + transaction fill into the template
  plaid_client.py               builds PlaidApi from config
  plaid_store.py                file-backed repository: access tokens, cursors, txn ledger
  transactions.py               sync (headless pull), month extraction, CSV export
  email.py                      notification email with sheet link
  main.py                       orchestration: sync, backfill, fill, notify
tests/template_automation/      mirrors src tree
```

## Two-phase model

1. **Link (once per institution, interactive):**
   `python link_accounts.py chase` then `python link_accounts.py schoolsfirst`.
   Opens a browser for Plaid Link (Chase via OAuth, SchoolsFirst via
   credentials). Persists the access token. There is no headless alternative;
   this is the consent grant.
2. **Run (recurring, headless):** `python run.py`. Pulls transactions, fills
   sheets, sends email. No browser, no human. This is what goes in cron,
   scheduled for the 1st of each month.

## Backfill logic

On every run, before processing the current previous month, the tool scans the
Drive year folders under `PARENT_FOLDER_ID` and compares them against the range
of months it should have generated (from the earliest linked month through last
month). Any gap is a missed month. The tool generates sheets for all missed
months in chronological order, pulling the corresponding date range from the
Plaid ledger, filling each template, and sending one summary email at the end
covering everything that was generated.

Do not `sys.exit` or skip when a month's sheet already exists. Check, skip
silently, and continue to the next month. The old `drive.py` called
`sys.exit(0)` on an existing file. That must be replaced with a continue so
backfill works.

## The ledger

`/transactions/sync` is incremental: it returns everything since the stored
cursor and advances it. The sheet model is calendar-month. These do not align.
Sync writes into a per-institution ledger in `plaid_items.json` (upsert on
added/modified, delete on removed, keyed by `transaction_id`), and month reads
slice the ledger by date range. Do not filter sync output directly to one month
and discard the rest. That silently drops data outside the window while still
advancing the cursor, and mishandles pending-to-posted transitions.

## CSV export

After extracting a month's posted transactions from the ledger, convert them
to CSV with columns: `date`, `amount`, `description`, `institution`. This CSV
is intermediate (used to populate the sheet), but also write it to a local
`exports/` directory as `YYYY-MM.csv` so there is always a raw record
independent of Google Drive.

## Email notification

After all sheets (current month and any backfilled months) are generated, send
one email via the Gmail API to the authenticated user. The email should include:

- Which months were generated.
- Transaction count and total spend per institution per month.
- A prominent link to each sheet (the Google Sheets URL from the file id).

Use the same Google OAuth credentials already in `auth.py`. Add the
`https://www.googleapis.com/auth/gmail.send` scope.

## Conventions

- `config.py` is the only reader of environment variables. Add new env vars
  there as class attributes. Never scatter `os.getenv` calls.
- Data access goes behind a repository (`PlaidStore`). Do not read or write
  `plaid_items.json` directly from other modules.
- Tests mirror the source tree under `tests/`.
- Minimal-first: smallest working version, then extend. Do not add abstraction
  speculatively.
- No em-dashes anywhere, including code comments and docs. Use commas, colons,
  periods, or parentheses instead.
- Builder tone for any docs or copy. No marketing language.

## Commands

```
pip install -r requirements.txt
python link_accounts.py <chase|schoolsfirst>   # one-time, sandbox: user_good / pass_good
python run.py                                   # the monthly job
python -m pytest tests/ -q
```

## Config (.env)

```
PLAID_CLIENT_ID=...
PLAID_SECRET=...
PLAID_ENV=sandbox            # flip to production after sandbox verified
PARENT_FOLDER_ID=...         # Drive folder holding the Template
PLAID_ITEMS=chase,schoolsfirst
```

## Known gotchas

- **Amount sign.** Plaid positive = money leaving the account, matching
  spend-positive in the sheet. But a credit card payment to Chase arrives
  negative. Decide whether to exclude or categorize those.
- **Posted-only.** Only write transactions where `pending` is false. Running on
  the 1st, previous month's charges should be posted. If stragglers post late,
  the next run's backfill check will see the sheet exists and skip, so those
  late posts land in the ledger but not the sheet. Acceptable for v1.
- **Plaintext tokens.** `plaid_items.json` and `token.pickle` hold credentials
  in the clear. Both are gitignored. Keep off shared machines.
- **Gmail scope change.** Adding `gmail.send` to the existing scopes will
  invalidate the cached `token.pickle` on first run. The user will need to
  re-authorize once.

## Do not

- Scrape or automate logins against chase.com or schoolsfirstfcu.org. Plaid is
  the only sanctioned path.
- Commit `credentials.json`, `token.pickle`, `.env`, or `plaid_items.json`.
- Call `sys.exit()` from library modules. Return control to `main.py` and let
  it decide.
- Refresh Plaid data more than needed. Production bills per call. Monthly
  cadence is the design.
