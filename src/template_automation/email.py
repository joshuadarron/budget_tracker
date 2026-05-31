import base64
from email.mime.text import MIMEText

"""Notification email sent once after all sheets (current month plus any
backfilled months) are generated. Uses the Gmail API via the shared Google
OAuth credentials (gmail.send scope added in auth.py).
"""


def sheet_url(file_id):
    return f"https://docs.google.com/spreadsheets/d/{file_id}"


def build_summary(generated):
    """Plaintext body: each generated month, per-institution count and total
    spend, and a link to the sheet.
    """
    lines = ["Budget sheets generated:", ""]
    for month in generated:
        label = f"{month['year']:04d}-{month['month']:02d}"
        lines.append(label)
        for inst in month["institutions"]:
            lines.append(
                f"  {inst['institution']}: {inst['count']} transactions, "
                f"${inst['total']:.2f}"
            )
        lines.append(f"  Sheet: {sheet_url(month['file_id'])}")
        lines.append("")
    return "\n".join(lines)


def build_raw_message(sender, to, subject, body):
    message = MIMEText(body)
    message["To"] = to
    message["From"] = sender
    message["Subject"] = subject
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def send_summary(service, sender, to, generated):
    subject = "Budget sheets generated"
    raw = build_raw_message(sender, to, subject, build_summary(generated))
    return service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
