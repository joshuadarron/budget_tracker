import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Single reader of environment variables. Add new env vars here as
    class attributes. No other module calls os.getenv.
    """

    PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
    PLAID_SECRET = os.getenv("PLAID_SECRET")
    PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")
    PARENT_FOLDER_ID = os.getenv("PARENT_FOLDER_ID")
    PLAID_ITEMS = [s.strip() for s in os.getenv("PLAID_ITEMS", "").split(",") if s.strip()]

    PLAID_ITEMS_FILE = "plaid_items.json"
    EXPORTS_DIR = "exports"
