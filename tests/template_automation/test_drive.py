from src.template_automation import drive


def test_iter_months_inclusive_across_year_boundary():
    assert drive.iter_months((2023, 11), (2024, 2)) == [
        (2023, 11), (2023, 12), (2024, 1), (2024, 2),
    ]


def test_iter_months_single_month():
    assert drive.iter_months((2024, 5), (2024, 5)) == [(2024, 5)]


def test_missing_months_returns_gaps_sorted():
    existing = {(2024, 1), (2024, 3)}
    assert drive.missing_months(existing, (2024, 1), (2024, 4)) == [
        (2024, 2), (2024, 4),
    ]


def test_missing_months_none_when_complete():
    existing = {(2024, 1), (2024, 2)}
    assert drive.missing_months(existing, (2024, 1), (2024, 2)) == []


class _FakeFiles:
    """Routes files().list() by inspecting the query string."""

    def __init__(self, folders, files_by_folder):
        self._folders = folders            # {year_str: folder_id}
        self._files = files_by_folder      # {folder_id: [names]}
        self._q = None

    def list(self, q=None, fields=None):
        self._q = q
        return self

    def execute(self):
        q = self._q
        if "mimeType = 'application/vnd.google-apps.folder'" in q:
            return {"files": [{"id": fid, "name": name}
                              for name, fid in self._folders.items()]}
        for fid, names in self._files.items():
            if f"'{fid}' in parents" in q:
                return {"files": [{"id": f"{fid}-{n}", "name": n} for n in names]}
        return {"files": []}


class _FakeService:
    def __init__(self, files):
        self._files = files

    def files(self):
        return self._files


def test_list_existing_months_scans_year_folders():
    service = _FakeService(_FakeFiles(
        folders={"2023": "f2023", "2024": "f2024"},
        files_by_folder={"f2023": ["12"], "f2024": ["01", "Template", "03"]},
    ))
    months = drive.list_existing_months(service, "parent")
    assert months == {(2023, 12), (2024, 1), (2024, 3)}
