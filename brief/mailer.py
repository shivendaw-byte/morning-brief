"""Send the brief over Gmail SMTP using an app password."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send(subject: str, text_body: str, html_body: str) -> None:
    sender = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("BRIEF_TO", sender)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"Morning Brief <{sender}>"
    message["To"] = recipient
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=45) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(message)
