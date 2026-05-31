import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

"""Notification email sent once after all sheets (current month plus any
backfilled months) are generated. Sent via the Gmail API using the shared
Google OAuth credentials (gmail.send scope added in auth.py).

The email is multipart/alternative: a plaintext fallback (build_summary) and a
branded HTML version (build_html) styled after a clean transactional template
(centered card, logo, hero badge, heading, body, a button per sheet, footer) on
the project's soft sage/teal/amber palette.
"""

# Soft palette (matches assets/icon.svg and assets/banner.svg).
INK = "#2c4a3e"
SAGE = "#7fb89a"
TEAL = "#5aa39b"
AMBER = "#c28a3a"
MUTED = "#6a8a7c"
PANEL = "#eaf3ee"
PAGE_BG = "#f3f6f4"


def sheet_url(file_id):
    return f"https://docs.google.com/spreadsheets/d/{file_id}"


def _month_label(month):
    return f"{month['year']:04d}-{month['month']:02d}"


def build_summary(generated):
    """Plaintext body (fallback): each generated month, per-institution count
    and total spend, and a link to the sheet.
    """
    lines = ["Budget sheets generated:", ""]
    for month in generated:
        lines.append(_month_label(month))
        for inst in month["institutions"]:
            lines.append(
                f"  {inst['institution']}: {inst['count']} transactions, "
                f"${inst['total']:.2f}"
            )
        lines.append(f"  Sheet: {sheet_url(month['file_id'])}")
        lines.append("")
    return "\n".join(lines)


def _month_block(month):
    label = _month_label(month)
    rows = ""
    for inst in month["institutions"]:
        rows += (
            f'<tr>'
            f'<td style="padding:2px 0;color:{INK};font-size:14px;">{inst["institution"]}</td>'
            f'<td align="right" style="padding:2px 0;color:{MUTED};font-size:14px;">'
            f'{inst["count"]} txns &nbsp;&middot;&nbsp; '
            f'<strong style="color:{INK};">${inst["total"]:.2f}</strong></td>'
            f'</tr>'
        )
    return f"""
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="margin:0 0 16px 0;background:{PANEL};border-radius:14px;">
        <tr><td style="padding:20px 22px;">
          <div style="font-size:13px;font-weight:700;letter-spacing:2px;
                      text-transform:uppercase;color:{TEAL};margin-bottom:10px;">{label}</div>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            {rows}
          </table>
          <div style="text-align:center;margin-top:16px;">
            <a href="{sheet_url(month['file_id'])}"
               style="display:inline-block;background:{TEAL};color:#ffffff;
                      text-decoration:none;font-size:15px;font-weight:700;
                      padding:12px 28px;border-radius:24px;">Open {label} sheet</a>
          </div>
        </td></tr>
      </table>"""


def build_html(generated):
    labels = ", ".join(_month_label(m) for m in generated)
    plural = "sheet" if len(generated) == 1 else "sheets"
    blocks = "".join(_month_block(m) for m in generated)
    font = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
            "'Helvetica Neue',Arial,sans-serif")
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{PAGE_BG};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAGE_BG};">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background:#ffffff;border-radius:18px;
                    font-family:{font};">
        <tr><td style="padding:36px 40px 8px 40px;" align="center">
          <!-- wordmark -->
          <table role="presentation" cellpadding="0" cellspacing="0"><tr>
            <td style="width:22px;height:22px;background:{SAGE};border-radius:50%;
                       color:#ffffff;font-weight:700;font-size:13px;text-align:center;
                       line-height:22px;">$</td>
            <td style="padding-left:10px;font-size:20px;font-weight:700;color:{INK};
                       letter-spacing:-0.3px;">Budget Tracker</td>
          </tr></table>
        </td></tr>

        <tr><td style="padding:24px 40px 0 40px;" align="center">
          <!-- hero badge -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:{PANEL};border-radius:16px;"><tr>
            <td align="center" style="padding:34px 0;">
              <div style="width:72px;height:72px;background:{SAGE};border-radius:50%;
                          color:#ffffff;font-size:34px;font-weight:700;line-height:72px;
                          text-align:center;">$</div>
            </td>
          </tr></table>
        </td></tr>

        <tr><td style="padding:28px 48px 0 48px;" align="center">
          <h1 style="margin:0;font-size:30px;line-height:1.25;font-weight:800;color:{INK};">
            Your budget {plural}<br>{'is' if len(generated)==1 else 'are'} ready</h1>
        </td></tr>

        <tr><td style="padding:16px 48px 8px 48px;" align="center">
          <p style="margin:0;font-size:16px;line-height:1.6;color:{MUTED};">
            Generated {len(generated)} {plural} ({labels}). Per-institution totals are
            below. Open any month with its button.</p>
        </td></tr>

        <tr><td style="padding:24px 40px 8px 40px;">
          {blocks}
        </td></tr>

        <tr><td style="padding:8px 48px 0 48px;" align="center">
          <hr style="border:none;border-top:1px solid #e4ece8;margin:24px 0;">
          <p style="margin:0;font-size:13px;line-height:1.6;color:{MUTED};">
            This is an automated message from your Budget Tracker job. It runs monthly,
            pulls the previous month's transactions via Plaid, and fills your Google
            Sheets template.</p>
        </td></tr>

        <tr><td style="padding:16px 40px 36px 40px;" align="center">
          <p style="margin:0;font-size:12px;color:#9fb3aa;">Budget Tracker &middot; headless monthly financial automation</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def build_raw_message(sender, to, subject, html, plain):
    message = MIMEMultipart("alternative")
    message["To"] = to
    message["From"] = sender
    message["Subject"] = subject
    message.attach(MIMEText(plain, "plain"))
    message.attach(MIMEText(html, "html"))
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def send_summary(service, sender, to, generated):
    subject = "Your budget sheets are ready"
    raw = build_raw_message(
        sender, to, subject, build_html(generated), build_summary(generated)
    )
    return service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
