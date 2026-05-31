from .drive import copy_template_if_needed
from .chase import get_previous_month_transactions as get_chase_txns
from .sheets import write_transactions_to_sheet
import os
from dotenv import load_dotenv

def run():
    load_dotenv()
    parent_folder_id = os.getenv("PARENT_FOLDER_ID")
    if not parent_folder_id:
        raise ValueError("❌ Missing PARENT_FOLDER_ID in .env file")

    spreadsheet_id = copy_template_if_needed(parent_folder_id)

    chase_transactions = get_chase_txns()
    write_transactions_to_sheet(spreadsheet_id, chase_transactions)

