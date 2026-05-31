import calendar
import csv
import io
import os

from plaid.model.transactions_sync_request import TransactionsSyncRequest

"""Headless transaction handling.

sync() pulls everything since the stored cursor into the per-institution
ledger (it does not filter to one month). month_transactions() slices the
ledger by calendar month for sheet/CSV use.

Amount sign (v1): Plaid positive means money leaving the account, which
matches spend-positive in the sheet. Rows with amount <= 0 (credit card
payments, refunds) are excluded from a month's spend.
"""

CSV_COLUMNS = ["date", "amount", "description", "institution"]


def month_bounds(year, month):
    last = calendar.monthrange(year, month)[1]
    return (f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last:02d}")


def _record(txn):
    date = txn.date
    date = date.isoformat() if hasattr(date, "isoformat") else str(date)
    return {
        "transaction_id": txn.transaction_id,
        "date": date,
        "amount": float(txn.amount),
        "name": txn.name,
        "pending": bool(txn.pending),
    }


def sync(client, store, item):
    """Pull /transactions/sync from the stored cursor and write to the ledger."""
    access_token = store.get_access_token(item)
    cursor = store.get_cursor(item) or ""

    added, modified, removed_ids = [], [], []
    has_more = True
    while has_more:
        request = TransactionsSyncRequest(access_token=access_token, cursor=cursor)
        response = client.transactions_sync(request)
        added.extend(response.added)
        modified.extend(response.modified)
        removed_ids.extend(r.transaction_id for r in response.removed)
        cursor = response.next_cursor
        has_more = response.has_more

    store.upsert_transactions(item, [_record(t) for t in added + modified])
    store.remove_transactions(item, removed_ids)
    store.set_cursor(item, cursor)


def month_transactions(store, item, year, month):
    start, end = month_bounds(year, month)
    rows = store.read_range(item, start, end)
    out = []
    for row in rows:
        if row.get("pending"):
            continue
        if row["amount"] <= 0:
            continue
        out.append(
            {
                "date": row["date"],
                "amount": row["amount"],
                "description": row["name"],
                "institution": item,
            }
        )
    return out


def to_csv(rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row[k] for k in CSV_COLUMNS})
    return buffer.getvalue()


def write_export(exports_dir, year, month, rows):
    os.makedirs(exports_dir, exist_ok=True)
    path = os.path.join(exports_dir, f"{year:04d}-{month:02d}.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(to_csv(rows))
    return path
