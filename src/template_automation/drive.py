from .sheets import delete_sheet_rows

"""Drive operations: year-folder management, template copy, and backfill gap
detection. No sys.exit. Callers (main.py) decide control flow; an existing
month sheet is skipped silently and the run continues.
"""


def iter_months(earliest, last):
    """Inclusive list of (year, month) tuples from earliest to last."""
    y, m = earliest
    end_y, end_m = last
    out = []
    while (y, m) <= (end_y, end_m):
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def missing_months(existing, earliest, last):
    """(year, month) tuples in the range that are not in `existing`."""
    return [ym for ym in iter_months(earliest, last) if ym not in existing]


def _is_month_name(name):
    return len(name) == 2 and name.isdigit() and 1 <= int(name) <= 12


def list_existing_months(service, parent_folder_id):
    """Scan year folders under the parent and return the set of (year, month)
    sheets that already exist.
    """
    folder_query = (
        f"'{parent_folder_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    folders = (
        service.files()
        .list(q=folder_query, fields="files(id, name)")
        .execute()
        .get("files", [])
    )

    months = set()
    for folder in folders:
        if not (len(folder["name"]) == 4 and folder["name"].isdigit()):
            continue
        year = int(folder["name"])
        file_query = f"'{folder['id']}' in parents and trashed = false"
        files = (
            service.files()
            .list(q=file_query, fields="files(id, name)")
            .execute()
            .get("files", [])
        )
        for f in files:
            if _is_month_name(f["name"]):
                months.add((year, int(f["name"])))
    return months


def find_or_create_year_folder(service, parent_folder_id, year):
    query = (
        f"'{parent_folder_id}' in parents and name = '{year}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    folders = (
        service.files()
        .list(q=query, fields="files(id, name)")
        .execute()
        .get("files", [])
    )
    if folders:
        return folders[0]["id"]
    metadata = {
        "name": str(year),
        "parents": [parent_folder_id],
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    print(f"Created year folder '{year}'")
    return folder["id"]


def _find_template(service, parent_folder_id):
    query = f"'{parent_folder_id}' in parents and name = 'Template' and trashed = false"
    files = (
        service.files()
        .list(q=query, fields="files(id, name)")
        .execute()
        .get("files", [])
    )
    return files[0]["id"] if files else None


def copy_template(service, parent_folder_id, year_folder_id, month):
    """Copy the Template into the year folder, named by month (e.g. '05').
    Returns the new file id with rows cleared. Caller must ensure it does not
    already exist.
    """
    template_id = _find_template(service, parent_folder_id)
    if not template_id:
        raise FileNotFoundError(f"No 'Template' file in folder {parent_folder_id}")

    filename = f"{month:02d}"
    copied = (
        service.files()
        .copy(
            fileId=template_id,
            body={"name": filename, "parents": [year_folder_id]},
            fields="id",
        )
        .execute()
    )
    file_id = copied["id"]
    print(f"Copied 'Template' to '{filename}' (ID: {file_id})")
    delete_sheet_rows(file_id)
    return file_id
