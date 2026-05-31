from .auth import get_sheets_service


def delete_sheet_rows(spreadsheet_id):
    sheets_service = get_sheets_service()
    spreadsheet = (
        sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )
    sheets = spreadsheet.get("sheets", [])

    requests = []

    if len(sheets) >= 1:
        sheet_id_1 = sheets[0]["properties"]["sheetId"]
        requests.append(
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id_1,
                        "dimension": "ROWS",
                        "startIndex": 0,
                        "endIndex": 6,
                    }
                }
            }
        )

    if len(sheets) >= 2:
        sheet_id_2 = sheets[1]["properties"]["sheetId"]
        requests.append(
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id_2,
                        "dimension": "ROWS",
                        "startIndex": 0,
                        "endIndex": 1,
                    }
                }
            }
        )

    if requests:
        body = {"requests": requests}
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()
        print("🧹 Deleted rows from the new sheet.")


def write_transactions_to_sheet(spreadsheet_id, transactions):
    sheets_service = get_sheets_service()
    spreadsheet = (
        sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )

    # Get the name of the second sheet
    sheet_name = spreadsheet["sheets"][1]["properties"]["title"]

    # Read existing data from B4:D to determine the next empty row
    read_range = f"{sheet_name}!B4:D"
    existing = (
        sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=read_range)
        .execute()
    )

    existing_values = existing.get("values", [])
    next_row_index = 4 + len(existing_values)  # 1-indexed rows

    # Prepare range to write to
    write_range = f"{sheet_name}!B{next_row_index}:D"

    values = []
    for txn in transactions:
        values.append([txn["date"], txn["amount"], txn["description"]])

    body = {"range": write_range, "majorDimension": "ROWS", "values": values}

    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=write_range,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()

    print(
        f"✅ Appended {len(values)} transactions starting at row {next_row_index} in {sheet_name}."
    )
