import base64
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

import requests
from core.models import EmailAccount
from dotenv import load_dotenv

from backend.settings import BASE_DIR

load_dotenv(os.path.join(BASE_DIR, ".env"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


def refresh_access_token(refresh_token: str) -> str:
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def send_email(
    from_email: str,
    to_emails: List[str],
    subject: str,
    body: str,
    body_type: str = "html",
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None,
    attachments: Optional[List[Path]] = None,
):
    accounts = EmailAccount.objects.filter(email=from_email)
    if not accounts.exists():
        raise ValueError("Credentials not found. Please setup your email first.")
    account = accounts.first()
    access_token = account.credentials["access_token"]
    refresh_token = account.credentials["refresh_token"]

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)

    if body_type.lower() not in ("plain", "html"):
        raise ValueError("body_type must be 'plain' or 'html'")
    msg.attach(MIMEText(body, body_type.lower()))

    if attachments:
        for file_path in attachments:
            if not Path(file_path).is_file():
                continue
            with open(file_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{Path(file_path).name}"',
            )
            msg.attach(part)

    all_recipients = to_emails.copy()
    if cc_emails:
        all_recipients += cc_emails
    if bcc_emails:
        all_recipients += bcc_emails

    def _send(access_token):
        auth_string = f"user={from_email}\1auth=Bearer {access_token}\1\1"
        auth_string_encoded = base64.b64encode(auth_string.encode()).decode()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.docmd("AUTH", f"XOAUTH2 {auth_string_encoded}")
            server.sendmail(from_email, all_recipients, msg.as_string())

    try:
        _send(access_token)
    except Exception as e:
        try:
            access_token = refresh_access_token(refresh_token)
            account.credentials["access_token"] = access_token
            account.save()
            _send(access_token)
        except Exception as e:
            raise e
