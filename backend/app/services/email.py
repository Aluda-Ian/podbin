import smtplib
import ssl
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
    host = (smtp_config and smtp_config.get("host")) or SMTP_HOST
    username = (smtp_config and smtp_config.get("username")) or SMTP_USERNAME
    password = (smtp_config and smtp_config.get("password")) or SMTP_PASSWORD
    from_email = (smtp_config and smtp_config.get("from_email")) or SMTP_FROM_EMAIL

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to

    msg.attach(MIMEText(body, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))

    primary_port = int((smtp_config and smtp_config.get("port")) or SMTP_PORT)
    ports_to_try = [primary_port]
    for p in [465, 587, 25]:
        if p not in ports_to_try:
            ports_to_try.append(p)

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    for port in ports_to_try:
        try:
            print(f"[EMAIL] Attempting email to {to} via {host}:{port}...")
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=10, context=ssl_context)
            else:
                server = smtplib.SMTP(host, port, timeout=10)
                try:
                    server.starttls(context=ssl_context)
                except Exception as tls_err:
                    print(f"[EMAIL] TLS warning on port {port}: {tls_err}")

            if username and password:
                server.login(username, password)

            server.sendmail(from_email, [to], msg.as_string())
            server.quit()
            print(f"[EMAIL] SUCCESS! Sent email to {to} via {host}:{port}")
            return True
        except Exception as e:
            print(f"[EMAIL] Port {port} failed for {to}: {e}")
            continue

    print(f"[EMAIL] All SMTP ports failed for {to}")
    return False


