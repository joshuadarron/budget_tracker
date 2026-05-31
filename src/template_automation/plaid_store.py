import json
from pathlib import Path

"""File-backed repository over plaid_items.json.

Sole owner of the JSON file. No other module reads or writes it directly.
Schema:

    {
      "<item>": {
        "access_token": str | null,
        "cursor": str | null,
        "transactions": { "<transaction_id>": {date, amount, name, pending, ...} }
      }
    }
"""


class PlaidStore:
    def __init__(self, path):
        self._path = Path(path)

    def _load(self):
        if not self._path.exists():
            return {}
        with open(self._path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self, data):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _item(self, data, item):
        return data.setdefault(
            item, {"access_token": None, "cursor": None, "transactions": {}}
        )

    def get_access_token(self, item):
        return self._load().get(item, {}).get("access_token")

    def set_access_token(self, item, token):
        data = self._load()
        self._item(data, item)["access_token"] = token
        self._save(data)

    def get_cursor(self, item):
        return self._load().get(item, {}).get("cursor")

    def set_cursor(self, item, cursor):
        data = self._load()
        self._item(data, item)["cursor"] = cursor
        self._save(data)

    def upsert_transactions(self, item, txns):
        data = self._load()
        ledger = self._item(data, item)["transactions"]
        for txn in txns:
            ledger[txn["transaction_id"]] = txn
        self._save(data)

    def remove_transactions(self, item, ids):
        data = self._load()
        ledger = self._item(data, item)["transactions"]
        for txn_id in ids:
            ledger.pop(txn_id, None)
        self._save(data)

    def min_date(self, item):
        ledger = self._load().get(item, {}).get("transactions", {})
        dates = [t["date"] for t in ledger.values()]
        return min(dates) if dates else None

    def read_range(self, item, start_date, end_date):
        ledger = self._load().get(item, {}).get("transactions", {})
        rows = [t for t in ledger.values() if start_date <= t["date"] <= end_date]
        return sorted(rows, key=lambda t: t["date"])
