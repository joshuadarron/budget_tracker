import datetime
from types import SimpleNamespace

from src.template_automation import transactions as txns
from src.template_automation.plaid_store import PlaidStore


def test_month_bounds_handles_month_length():
    assert txns.month_bounds(2024, 2) == ("2024-02-01", "2024-02-29")  # leap year
    assert txns.month_bounds(2023, 2) == ("2023-02-01", "2023-02-28")
    assert txns.month_bounds(2024, 12) == ("2024-12-01", "2024-12-31")


def test_month_transactions_excludes_pending_and_non_spend(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    store.upsert_transactions("chase", [
        {"transaction_id": "a", "date": "2024-03-05", "amount": 45.12,
         "name": "Trader Joe's", "pending": False},
        {"transaction_id": "b", "date": "2024-03-06", "amount": 80.0,
         "name": "Pending charge", "pending": True},
        {"transaction_id": "c", "date": "2024-03-07", "amount": -200.0,
         "name": "Payment Thank You", "pending": False},
        {"transaction_id": "d", "date": "2024-02-28", "amount": 9.0,
         "name": "Out of month", "pending": False},
    ])
    rows = txns.month_transactions(store, "chase", 2024, 3)
    assert [r["description"] for r in rows] == ["Trader Joe's"]
    assert rows[0] == {"date": "2024-03-05", "amount": 45.12,
                       "description": "Trader Joe's", "institution": "chase"}


def test_to_csv_has_header_and_rows():
    rows = [
        {"date": "2024-03-05", "amount": 45.12, "description": "Trader Joe's",
         "institution": "chase"},
    ]
    csv_text = txns.to_csv(rows)
    lines = csv_text.splitlines()
    assert lines[0] == "date,amount,description,institution"
    assert lines[1] == "2024-03-05,45.12,Trader Joe's,chase"


def test_write_export_writes_file(tmp_path):
    rows = [{"date": "2024-03-05", "amount": 1.0, "description": "X",
             "institution": "chase"}]
    path = txns.write_export(str(tmp_path), 2024, 3, rows)
    assert path.endswith("2024-03.csv")
    with open(path, encoding="utf-8") as fh:
        assert fh.read().splitlines()[0] == "date,amount,description,institution"


def _txn(tid, date, amount, name, pending=False):
    return SimpleNamespace(transaction_id=tid, date=datetime.date.fromisoformat(date),
                           amount=amount, name=name, pending=pending)


def test_sync_paginates_upserts_removes_and_advances_cursor(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    store.set_access_token("chase", "access-1")

    pages = [
        SimpleNamespace(added=[_txn("t1", "2024-03-01", 10.0, "A")], modified=[],
                        removed=[], next_cursor="c1", has_more=True),
        SimpleNamespace(added=[_txn("t2", "2024-03-02", 20.0, "B")],
                        modified=[_txn("t1", "2024-03-01", 11.0, "A2")],
                        removed=[SimpleNamespace(transaction_id="t0")],
                        next_cursor="c2", has_more=False),
    ]
    calls = {"n": 0, "cursors": []}

    class FakeClient:
        def transactions_sync(self, req):
            calls["cursors"].append(req["cursor"])
            page = pages[calls["n"]]
            calls["n"] += 1
            return page

    txns.sync(FakeClient(), store, "chase")

    assert calls["cursors"] == ["", "c1"]      # starts empty, then advances
    assert store.get_cursor("chase") == "c2"
    rows = store.read_range("chase", "2024-03-01", "2024-03-31")
    by_id = {r["transaction_id"]: r for r in rows}
    assert set(by_id) == {"t1", "t2"}          # t0 removed
    assert by_id["t1"]["amount"] == 11.0       # modified applied
    assert by_id["t1"]["date"] == "2024-03-01"
