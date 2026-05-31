from src.template_automation.plaid_store import PlaidStore


def test_access_token_round_trip(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    store.set_access_token("chase", "access-123")
    assert store.get_access_token("chase") == "access-123"


def test_access_token_missing_returns_none(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    assert store.get_access_token("chase") is None


def test_cursor_round_trip(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    assert store.get_cursor("chase") is None
    store.set_cursor("chase", "cursor-abc")
    assert store.get_cursor("chase") == "cursor-abc"


def test_persists_across_instances(tmp_path):
    path = tmp_path / "items.json"
    PlaidStore(path).set_access_token("chase", "tok")
    assert PlaidStore(path).get_access_token("chase") == "tok"


def test_upsert_adds_and_updates_by_transaction_id(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    store.upsert_transactions("chase", [
        {"transaction_id": "t1", "date": "2024-03-02", "amount": 10.0,
         "name": "A", "pending": False},
    ])
    store.upsert_transactions("chase", [
        {"transaction_id": "t1", "date": "2024-03-02", "amount": 12.5,
         "name": "A updated", "pending": False},
    ])
    rows = store.read_range("chase", "2024-03-01", "2024-03-31")
    assert len(rows) == 1
    assert rows[0]["amount"] == 12.5
    assert rows[0]["name"] == "A updated"


def test_remove_deletes_by_id(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    store.upsert_transactions("chase", [
        {"transaction_id": "t1", "date": "2024-03-02", "amount": 10.0,
         "name": "A", "pending": False},
        {"transaction_id": "t2", "date": "2024-03-03", "amount": 20.0,
         "name": "B", "pending": False},
    ])
    store.remove_transactions("chase", ["t1"])
    rows = store.read_range("chase", "2024-03-01", "2024-03-31")
    assert [r["transaction_id"] for r in rows] == ["t2"]


def test_read_range_filters_by_date_inclusive_and_sorts(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    store.upsert_transactions("chase", [
        {"transaction_id": "t3", "date": "2024-04-01", "amount": 1.0,
         "name": "April", "pending": False},
        {"transaction_id": "t2", "date": "2024-03-31", "amount": 1.0,
         "name": "EndMar", "pending": False},
        {"transaction_id": "t1", "date": "2024-03-01", "amount": 1.0,
         "name": "StartMar", "pending": False},
        {"transaction_id": "t0", "date": "2024-02-28", "amount": 1.0,
         "name": "Feb", "pending": False},
    ])
    rows = store.read_range("chase", "2024-03-01", "2024-03-31")
    assert [r["transaction_id"] for r in rows] == ["t1", "t2"]


def test_min_date_returns_earliest_or_none(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    assert store.min_date("chase") is None
    store.upsert_transactions("chase", [
        {"transaction_id": "a", "date": "2024-03-05", "amount": 1.0,
         "name": "A", "pending": False},
        {"transaction_id": "b", "date": "2024-01-09", "amount": 1.0,
         "name": "B", "pending": False},
    ])
    assert store.min_date("chase") == "2024-01-09"


def test_read_range_isolates_items(tmp_path):
    store = PlaidStore(tmp_path / "items.json")
    store.upsert_transactions("chase", [
        {"transaction_id": "c1", "date": "2024-03-02", "amount": 10.0,
         "name": "A", "pending": False},
    ])
    store.upsert_transactions("schoolsfirst", [
        {"transaction_id": "s1", "date": "2024-03-02", "amount": 99.0,
         "name": "B", "pending": False},
    ])
    rows = store.read_range("chase", "2024-03-01", "2024-03-31")
    assert [r["transaction_id"] for r in rows] == ["c1"]
