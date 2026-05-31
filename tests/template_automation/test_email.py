import base64

from src.template_automation import email as mail


GENERATED = [
    {"year": 2024, "month": 3, "file_id": "f1", "institutions": [
        {"institution": "chase", "count": 12, "total": 345.67},
        {"institution": "schoolsfirst", "count": 4, "total": 88.0},
    ]},
    {"year": 2024, "month": 4, "file_id": "f2", "institutions": [
        {"institution": "chase", "count": 7, "total": 100.0},
    ]},
]


def test_sheet_url_from_file_id():
    assert mail.sheet_url("abc123") == "https://docs.google.com/spreadsheets/d/abc123"


def test_institution_name_maps_known_and_titlecases_unknown():
    assert mail._institution_name("chase") == "Chase"
    assert mail._institution_name("schoolsfirst") == "SchoolsFirst"
    assert mail._institution_name("jpmorgan") == "JPMorgan"
    assert mail._institution_name("wellsfargo") == "Wellsfargo"


def test_build_summary_lists_months_institutions_and_links():
    body = mail.build_summary(GENERATED)
    assert "2024-03" in body and "2024-04" in body
    assert "Chase: 12 transactions, $345.67" in body
    assert "SchoolsFirst: 4 transactions, $88.00" in body
    assert "https://docs.google.com/spreadsheets/d/f1" in body
    assert "https://docs.google.com/spreadsheets/d/f2" in body


def test_build_html_has_branding_months_stats_and_buttons():
    html = mail.build_html(GENERATED)
    assert "<html" in html.lower()
    assert "Budget Tracker" in html
    # months and per-institution stats
    assert "2024-03" in html and "2024-04" in html
    assert "Chase" in html and "$345.67" in html
    assert "$88.00" in html
    # a button linking to each sheet
    assert mail.sheet_url("f1") in html
    assert mail.sheet_url("f2") in html
    assert "Open" in html  # CTA label


def test_build_raw_message_is_multipart_with_plain_and_html():
    raw = mail.build_raw_message("me@example.com", "me@example.com", "Subj",
                                 "<html><body>hi html</body></html>", "hi plain")
    decoded = base64.urlsafe_b64decode(raw.encode()).decode()
    assert "Subject: Subj" in decoded
    assert "To: me@example.com" in decoded
    assert "multipart/alternative" in decoded
    assert "hi plain" in decoded
    assert "hi html" in decoded
