import plaid
from plaid.api import plaid_api

from .config import Config

_HOSTS = {
    "sandbox": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}


def build_client():
    """Build a PlaidApi from config. Sandbox and Production only."""
    configuration = plaid.Configuration(
        host=_HOSTS[Config.PLAID_ENV],
        api_key={
            "clientId": Config.PLAID_CLIENT_ID,
            "secret": Config.PLAID_SECRET,
        },
    )
    return plaid_api.PlaidApi(plaid.ApiClient(configuration))
