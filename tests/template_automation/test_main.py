import datetime

from src.template_automation import main
from src.template_automation.plaid_store import PlaidStore


def test_previous_month_within_year():
    assert main.previous_month(datetime.date(2026, 5, 30)) == (2026, 4)


def test_previous_month_crosses_year_boundary():
    assert main.previous_month(datetime.date(2026, 1, 15)) == (2025, 12)


def test_earliest_ledger_month_across_items(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    store.upsert_transactions("chase", [
        {"transaction_id": "a", "date": "2024-03-05", "amount": 1.0,
         "name": "A", "pending": False},
    ])
    store.upsert_transactions("schoolsfirst", [
        {"transaction_id": "b", "date": "2024-01-20", "amount": 1.0,
         "name": "B", "pending": False},
    ])
    assert main.earliest_ledger_month(store, ["chase", "schoolsfirst"]) == (2024, 1)


def test_earliest_ledger_month_none_when_empty(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    assert main.earliest_ledger_month(store, ["chase"]) is None
