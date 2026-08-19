import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

DEFAULT_SMTP_HOST = os.getenv("SMTP_HOST", "mail.vendatechnologies.com")
DEFAULT_SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
DEFAULT_SMTP_USER = os.getenv("SMTP_USERNAME", "smtp@vendatechnologies.com")
DEFAULT_SMTP_PASS = os.getenv("SMTP_PASSWORD", "@Munangwe212")
DEFAULT_SMTP_FROM = os.getenv("SMTP_FROM_EMAIL", "smtp@vendatechnologies.com")


async def send_email(
    to: str,
    subject: str,
    body: str,
    smtp_config: Optional[Dict[str, Any]] = None,
    html: Optional[str] = None,
) -> bool:
    config = smtp_config or {}
    host = config.get("host") or DEFAULT_SMTP_HOST
    port = int(config.get("port") or DEFAULT_SMTP_PORT)
    username = config.get("username") or DEFAULT_SMTP_USER
    password = config.get("password") or DEFAULT_SMTP_PASS
    from_email = config.get("from_email") or DEFAULT_SMTP_FROM

    if not host or not from_email:
        print("[EMAIL] Error: Missing SMTP host or from_email.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to

    msg.attach(MIMEText(body, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.starttls()

        if username and password:
            server.login(username, password)

        server.sendmail(from_email, [to], msg.as_string())
        server.quit()
        print(f"[EMAIL] Successfully sent email to {to}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send email to {to}: {e}")
        return False

