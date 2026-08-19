import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

# Hardcoded SMTP Credentials for Venda Technologies Mail Server
SMTP_HOST = "mail.vendatechnologies.com"
SMTP_PORT = 465
SMTP_USERNAME = "smtp@vendatechnologies.com"
SMTP_PASSWORD = "@Munangwe212"
SMTP_FROM_EMAIL = "smtp@vendatechnologies.com"


async def send_email(
    to: str,
    subject: str,
    body: str,
    smtp_config: Optional[Dict[str, Any]] = None,
    html: Optional[str] = None,
) -> bool:
    host = SMTP_HOST
    port = SMTP_PORT
    username = SMTP_USERNAME
    password = SMTP_PASSWORD
    from_email = SMTP_FROM_EMAIL

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


