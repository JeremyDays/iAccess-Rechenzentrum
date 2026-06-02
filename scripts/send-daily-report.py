import argparse
import os
import smtplib
import ssl
from email.message import EmailMessage


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing environment variable: {name}")
    return value


def main():
    parser = argparse.ArgumentParser(description="Send the iAccess daily research report via Gmail SMTP.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--to", default=os.environ.get("IACCESS_REPORT_TO", "hornick@iaccess.de"))
    args = parser.parse_args()

    sender = require_env("GMAIL_SMTP_USER")
    password = require_env("GMAIL_APP_PASSWORD")

    with open(args.body_file, "r", encoding="utf-8") as handle:
        body = handle.read()

    message = EmailMessage()
    message["From"] = sender
    message["To"] = args.to
    message["Subject"] = args.subject
    message.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)

    print(f"Sent report to {args.to}")


if __name__ == "__main__":
    main()
