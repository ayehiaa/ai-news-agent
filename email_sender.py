import re
import smtplib
import ssl
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from config import SMTP_HOST, SMTP_PORT

_EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


class EmailSendError(Exception):
    pass


def validate_email(address: str) -> bool:
    return bool(_EMAIL_REGEX.match(address))


def _plain_to_html(plain: str) -> str:
    lines = plain.splitlines()
    html_lines = ["<html><body style='font-family:sans-serif;max-width:680px;margin:auto'>"]
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br>")
        elif stripped.startswith("- ") or stripped.startswith("• "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{stripped[2:]}</li>")
        elif set(stripped) == {"-"} or set(stripped) == {"="}:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
        elif stripped.endswith("---") or stripped.endswith("==="):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
        elif stripped and lines.index(line) > 0 and set(lines[lines.index(line)].strip()) <= {"-", " "}:
            pass
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{stripped}</p>")

    if in_list:
        html_lines.append("</ul>")
    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def build_message(sender: str, recipient: str, subject: str, plain_body: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = f"<{uuid.uuid4()}@ainewsagent>"

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(_plain_to_html(plain_body), "html", "utf-8"))
    return msg


def send_email(sender: str, recipient: str, subject: str, body: str, smtp_password: str) -> None:
    if not validate_email(sender):
        raise EmailSendError(f"Invalid sender address: {sender!r}")
    if not validate_email(recipient):
        raise EmailSendError(f"Invalid recipient address: {recipient!r}")

    msg = build_message(sender, recipient, subject, body)
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(sender, smtp_password)
            server.sendmail(sender, recipient, msg.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailSendError(
            "Gmail authentication failed. Ensure 2FA is enabled and you are using a Gmail App Password "
            "(not your main password). Generate one at https://myaccount.google.com/apppasswords"
        ) from exc
    except smtplib.SMTPException as exc:
        raise EmailSendError(f"SMTP error: {exc}") from exc
