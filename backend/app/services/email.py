import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional


async def send_email(
    to: str,
    subject: str,
    body: str,
    smtp_config: Dict[str, Any],
    html: Optional[str] = None,
) -> bool:
    host = smtp_config.get("host", "")
    port = int(smtp_config.get("port", 587))
    username = smtp_config.get("username", "")
    password = smtp_config.get("password", "")
    from_email = smtp_config.get("from_email", "")

    if not host or not from_email:
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
            server = smtplib.SMTP_SSL(host, port)
        else:
            server = smtplib.SMTP(host, port)
            server.starttls()
        if username and password:
            server.login(username, password)
        server.sendmail(from_email, [to], msg.as_string())
        server.quit()
        return True
    except Exception:
        return False
