import pytest

from src.template_automation import plaid_client
from src.template_automation.config import Config


def test_build_client_requires_credentials(monkeypatch):
    monkeypatch.setattr(Config, "PLAID_CLIENT_ID", "")
    monkeypatch.setattr(Config, "PLAID_SECRET", "")
    with pytest.raises(ValueError, match="PLAID_CLIENT_ID"):
        plaid_client.build_client()


def test_build_client_succeeds_with_credentials(monkeypatch):
    monkeypatch.setattr(Config, "PLAID_CLIENT_ID", "id")
    monkeypatch.setattr(Config, "PLAID_SECRET", "secret")
    monkeypatch.setattr(Config, "PLAID_ENV", "sandbox")
    client = plaid_client.build_client()
    assert client is not None
