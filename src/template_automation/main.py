import datetime

from . import drive
from . import email as mail
from . import transactions as txns
from .auth import get_drive_service, get_gmail_service
from .config import Config
from .plaid_client import build_client
from .plaid_store import PlaidStore
from .sheets import write_transactions_to_sheet

"""Orchestration: sync every linked item, backfill any missing months, fill a
sheet per month, and send one summary email covering everything generated.
"""


def previous_month(today):
    year = today.year if today.month > 1 else today.year - 1
    month = today.month - 1 if today.month > 1 else 12
    return (year, month)


def earliest_ledger_month(store, items):
    dates = [d for d in (store.min_date(i) for i in items) if d]
    if not dates:
        return None
    earliest = min(dates)
    return (int(earliest[:4]), int(earliest[5:7]))


def _generate_month(drive_service, store, parent_folder_id, year, month):
    """Create and fill the sheet for one month across all items. Returns a
    summary dict, or None if there is nothing to record.
    """
    year_folder_id = drive.find_or_create_year_folder(
        drive_service, parent_folder_id, year
    )
    file_id = drive.copy_template(
        drive_service, parent_folder_id, year_folder_id, month
    )

    all_rows = []
    institutions = []
    for item in Config.PLAID_ITEMS:
        rows = txns.month_transactions(store, item, year, month)
        if rows:
            write_transactions_to_sheet(file_id, rows)
        all_rows.extend(rows)
        institutions.append(
            {
                "institution": item,
                "count": len(rows),
                "total": round(sum(r["amount"] for r in rows), 2),
            }
        )

    txns.write_export(Config.EXPORTS_DIR, year, month, all_rows)
    return {
        "year": year,
        "month": month,
        "file_id": file_id,
        "institutions": institutions,
    }


def run(today=None):
    today = today or datetime.date.today()
    if not Config.PARENT_FOLDER_ID:
        raise ValueError("Missing PARENT_FOLDER_ID in .env file")

    store = PlaidStore(Config.PLAID_ITEMS_FILE)
    client = build_client()
    for item in Config.PLAID_ITEMS:
        txns.sync(client, store, item)

    earliest = earliest_ledger_month(store, Config.PLAID_ITEMS)
    if not earliest:
        print("No transactions in the ledger yet. Link an account first.")
        return

    last = previous_month(today)
    drive_service = get_drive_service()
    existing = drive.list_existing_months(drive_service, Config.PARENT_FOLDER_ID)
    to_generate = drive.missing_months(existing, earliest, last)

    if not to_generate:
        print("All months up to date. Nothing to generate.")
        return

    generated = []
    for year, month in to_generate:
        summary = _generate_month(
            drive_service, store, Config.PARENT_FOLDER_ID, year, month
        )
        if summary:
            generated.append(summary)

    if not Config.NOTIFY_EMAIL:
        raise ValueError(
            "Missing NOTIFY_EMAIL in .env (recipient for the summary email)"
        )
    gmail = get_gmail_service()
    mail.send_summary(gmail, Config.NOTIFY_EMAIL, Config.NOTIFY_EMAIL, generated)
    months = ", ".join(f"{g['year']:04d}-{g['month']:02d}" for g in generated)
    print(f"Generated and emailed: {months}")
