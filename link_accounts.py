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
token, and persists it via PlaidStore. Chase links via OAuth, SchoolsFirst via
credentials. Sandbox login: user_good / pass_good. This is the consent grant;
there is no headless alternative.
"""

PAGE = """
<!doctype html>
<html>
  <head><script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script></head>
  <body>
    <h2>Linking: {item}</h2>
    <p id="status">Opening Plaid Link...</p>
    <script>
      const handler = Plaid.create({
        token: "{link_token}",
        onSuccess: (public_token) => {
          fetch("/exchange", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({public_token})
          }).then(() => {
            document.getElementById("status").innerText =
              "Linked. You can close this tab.";
          });
        },
        onExit: () => { document.getElementById("status").innerText = "Cancelled."; }
      });
      handler.open();
    </script>
  </body>
</html>
"""


def create_app(item):
    app = Flask(__name__)
    client = build_client()
    store = PlaidStore(Config.PLAID_ITEMS_FILE)

    @app.route("/")
    def index():
        link_request = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id=item),
            client_name="Budget Tracker",
            products=[Products("transactions")],
            country_codes=[CountryCode("US")],
            language="en",
        )
        link_token = client.link_token_create(link_request).link_token
        return PAGE.replace("{item}", item).replace("{link_token}", link_token)

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

    item = sys.argv[1]
    app = create_app(item)
    url = "http://127.0.0.1:5000/"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Open {url} to link '{item}'. Ctrl-C when done.")
    app.run(port=5000)


if __name__ == "__main__":
    main()
