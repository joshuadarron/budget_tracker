import base64

from src.template_automation import email as mail


def test_sheet_url_from_file_id():
    assert mail.sheet_url("abc123") == "https://docs.google.com/spreadsheets/d/abc123"


def test_build_summary_lists_months_institutions_and_links():
    generated = [
        {"year": 2024, "month": 3, "file_id": "f1", "institutions": [
            {"institution": "chase", "count": 12, "total": 345.67},
            {"institution": "schoolsfirst", "count": 4, "total": 88.0},
        ]},
        {"year": 2024, "month": 4, "file_id": "f2", "institutions": [
            {"institution": "chase", "count": 7, "total": 100.0},
        ]},
    ]
    body = mail.build_summary(generated)
    assert "2024-03" in body and "2024-04" in body
    assert "chase: 12 transactions, $345.67" in body
    assert "schoolsfirst: 4 transactions, $88.00" in body
    assert "https://docs.google.com/spreadsheets/d/f1" in body
    assert "https://docs.google.com/spreadsheets/d/f2" in body


def test_build_raw_message_is_base64url_mime():
    raw = mail.build_raw_message("me@example.com", "me@example.com", "Subj", "Body here")
    decoded = base64.urlsafe_b64decode(raw.encode()).decode()
    assert "Subject: Subj" in decoded
    assert "To: me@example.com" in decoded
    assert "Body here" in decoded
