import argparse
import base64
import json
import os
import threading
import webbrowser
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


ROOT = Path(__file__).resolve().parents[1]
SECRETS = ROOT / "secrets"
CREDENTIALS_FILE = SECRETS / "gmail-credentials.json"
TOKEN_FILE = SECRETS / "gmail-token.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def load_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise SystemExit(f"Missing credentials file: {CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def authorize_manual(port=8080, open_browser=False):
    if not CREDENTIALS_FILE.exists():
        raise SystemExit(f"Missing credentials file: {CREDENTIALS_FILE}")

    redirect_uri = f"http://localhost:{port}/"
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        SCOPES,
        redirect_uri=redirect_uri,
    )
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    url_file = SECRETS / "gmail-auth-url.txt"
    url_file.write_text(auth_url, encoding="utf-8")

    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            if "code" in query:
                result["code"] = query["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Gmail authorization complete.</h1><p>You can close this window.</p></body></html>")
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                result["error"] = query.get("error", ["Missing code"])[0]
                self.send_response(400)
                self.end_headers()

        def log_message(self, _format, *_args):
            return

    if open_browser:
        webbrowser.open(auth_url)

    print(f"Open this URL in your browser: {auth_url}")
    print(f"URL also written to: {url_file}")

    server = HTTPServer(("localhost", port), CallbackHandler)
    server.serve_forever()

    if "code" not in result:
        raise SystemExit(f"Authorization failed: {result.get('error', 'unknown error')}")

    flow.fetch_token(code=result["code"])
    TOKEN_FILE.write_text(flow.credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=flow.credentials)


def command_auth(_args):
    if getattr(_args, "manual", False):
        service = authorize_manual(port=_args.port, open_browser=_args.open_browser)
    else:
        service = load_service()
    profile = service.users().getProfile(userId="me").execute()
    print(json.dumps({
        "emailAddress": profile.get("emailAddress"),
        "messagesTotal": profile.get("messagesTotal"),
        "threadsTotal": profile.get("threadsTotal"),
    }, indent=2))


def command_send(args):
    service = load_service()
    body = Path(args.body_file).read_text(encoding="utf-8")

    message = EmailMessage()
    message["To"] = args.to
    message["From"] = "me"
    message["Subject"] = args.subject
    message.set_content(body)

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    result = service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    print(json.dumps({"sent": True, "id": result.get("id"), "to": args.to}, indent=2))


def command_search(args):
    service = load_service()
    response = service.users().messages().list(userId="me", q=args.query, maxResults=args.limit).execute()
    messages = response.get("messages", [])
    rows = []
    for item in messages:
        msg = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        rows.append({
            "id": msg.get("id"),
            "threadId": msg.get("threadId"),
            "date": headers.get("date", ""),
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "snippet": msg.get("snippet", ""),
        })
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def ensure_label(service, name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label.get("name") == name:
            return label["id"]
    created = service.users().labels().create(userId="me", body={
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }).execute()
    return created["id"]


def command_label(args):
    service = load_service()
    response = service.users().messages().list(userId="me", q=args.query, maxResults=args.limit).execute()
    messages = response.get("messages", [])
    label_id = ensure_label(service, args.label)
    ids = [m["id"] for m in messages]

    if args.dry_run:
        print(json.dumps({"dryRun": True, "matches": len(ids), "label": args.label, "ids": ids}, indent=2))
        return

    if ids:
        service.users().messages().batchModify(userId="me", body={
            "ids": ids,
            "addLabelIds": [label_id],
        }).execute()
    print(json.dumps({"labeled": len(ids), "label": args.label}, indent=2))


def command_archive(args):
    service = load_service()
    response = service.users().messages().list(userId="me", q=args.query, maxResults=args.limit).execute()
    ids = [m["id"] for m in response.get("messages", [])]

    if args.dry_run:
        print(json.dumps({"dryRun": True, "matches": len(ids), "ids": ids}, indent=2))
        return

    if ids:
        service.users().messages().batchModify(userId="me", body={
            "ids": ids,
            "removeLabelIds": ["INBOX"],
        }).execute()
    print(json.dumps({"archived": len(ids)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Local Gmail API helper for iAccess/Codex.")
    sub = parser.add_subparsers(required=True)

    auth = sub.add_parser("auth", help="Authorize Gmail and print profile summary.")
    auth.add_argument("--manual", action="store_true", help="Write auth URL and wait on localhost.")
    auth.add_argument("--port", type=int, default=8080)
    auth.add_argument("--open-browser", action="store_true")
    auth.set_defaults(func=command_auth)

    send = sub.add_parser("send", help="Send a plaintext email.")
    send.add_argument("--to", default=os.environ.get("IACCESS_REPORT_TO", "hornick@iaccess.de"))
    send.add_argument("--subject", required=True)
    send.add_argument("--body-file", required=True)
    send.set_defaults(func=command_send)

    search = sub.add_parser("search", help="Search Gmail and print metadata.")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=10)
    search.set_defaults(func=command_search)

    label = sub.add_parser("label", help="Add a Gmail label to matching messages.")
    label.add_argument("--query", required=True)
    label.add_argument("--label", required=True)
    label.add_argument("--limit", type=int, default=10)
    label.add_argument("--dry-run", action="store_true")
    label.set_defaults(func=command_label)

    archive = sub.add_parser("archive", help="Archive matching messages by removing INBOX.")
    archive.add_argument("--query", required=True)
    archive.add_argument("--limit", type=int, default=10)
    archive.add_argument("--dry-run", action="store_true")
    archive.set_defaults(func=command_archive)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
