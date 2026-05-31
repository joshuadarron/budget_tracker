import sys
import threading
import webbrowser

from flask import Flask, request, jsonify

from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

from src.template_automation.config import Config
from src.template_automation.plaid_client import build_client
from src.template_automation.plaid_store import PlaidStore

"""One-time interactive Plaid linker.

    python link_accounts.py chase
    python link_accounts.py schoolsfirst

Opens a browser running Plaid Link, exchanges the public token for an access
token, and persists it via PlaidStore. Chase requires OAuth (production only):
Link redirects to Chase, Chase redirects back to the registered /oauth URI, and
the page re-initializes Link with receivedRedirectUri to finish. Credential
banks (e.g. SchoolsFirst, sandbox) complete without leaving the first page.
Sandbox login: user_good / pass_good. This is the consent grant; there is no
headless alternative.

Production OAuth needs an HTTPS redirect URI registered in the Plaid dashboard
(Developers > API > Allowed redirect URIs). This server uses a self-signed cert
(ssl_context="adhoc") so https://localhost:5000/oauth works for local linking.
"""

# Shared Link JS: onSuccess posts the public token to /exchange.
_SUCCESS_JS = """
      const onSuccess = (public_token) => {
        fetch("/exchange", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({public_token})
        }).then(() => {
          document.getElementById("status").innerText = "Linked. You can close this tab.";
        });
      };
      const onExit = () => { document.getElementById("status").innerText = "Cancelled."; };
"""

START_PAGE = """
<!doctype html>
<html>
  <head><script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script></head>
  <body>
    <h2>Linking: {item}</h2>
    <p id="status">Opening Plaid Link...</p>
    <script>
      const linkToken = "{link_token}";
      localStorage.setItem("plaid_link_token", linkToken);
      {success_js}
      const handler = Plaid.create({ token: linkToken, onSuccess, onExit });
      handler.open();
    </script>
  </body>
</html>
"""

OAUTH_PAGE = """
<!doctype html>
<html>
  <head><script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script></head>
  <body>
    <h2>Completing OAuth...</h2>
    <p id="status">Resuming Plaid Link...</p>
    <script>
      const linkToken = localStorage.getItem("plaid_link_token");
      {success_js}
      const handler = Plaid.create({
        token: linkToken,
        receivedRedirectUri: window.location.href,
        onSuccess,
        onExit
      });
      handler.open();
    </script>
  </body>
</html>
"""


def build_link_request(item, redirect_uri=None):
    kwargs = dict(
        user=LinkTokenCreateRequestUser(client_user_id=item),
        client_name="Budget Tracker",
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
    )
    if redirect_uri:
        kwargs["redirect_uri"] = redirect_uri
    return LinkTokenCreateRequest(**kwargs)


def create_app(item):
    app = Flask(__name__)
    client = build_client()
    store = PlaidStore(Config.PLAID_ITEMS_FILE)

    @app.route("/")
    def index():
        link_request = build_link_request(item, Config.PLAID_REDIRECT_URI)
        link_token = client.link_token_create(link_request).link_token
        return (
            START_PAGE
            .replace("{item}", item)
            .replace("{link_token}", link_token)
            .replace("{success_js}", _SUCCESS_JS)
        )

    @app.route("/oauth")
    def oauth():
        return OAUTH_PAGE.replace("{success_js}", _SUCCESS_JS)

    @app.route("/exchange", methods=["POST"])
    def exchange():
        public_token = request.get_json()["public_token"]
        response = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        store.set_access_token(item, response.access_token)
        print(f"Stored access token for '{item}'.")
        return jsonify({"ok": True})

    return app


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in Config.PLAID_ITEMS:
        items = ", ".join(Config.PLAID_ITEMS) or "(none configured)"
        print(f"Usage: python link_accounts.py <item>. Configured items: {items}")
        sys.exit(1)

    if Config.PLAID_ENV == "production" and not Config.PLAID_REDIRECT_URI:
        print(
            "PLAID_ENV=production requires PLAID_REDIRECT_URI in .env (an HTTPS URI "
            "registered in the Plaid dashboard under Developers > API > Allowed "
            "redirect URIs), e.g. https://localhost:5000/oauth"
        )
        sys.exit(1)

    item = sys.argv[1]
    app = create_app(item)
    url = "https://127.0.0.1:5000/"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Open {url} to link '{item}' (accept the self-signed cert warning). Ctrl-C when done.")
    app.run(port=5000, ssl_context="adhoc")


if __name__ == "__main__":
    main()
