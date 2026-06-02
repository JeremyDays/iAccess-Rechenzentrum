import hashlib
import json
import mimetypes
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "assets" / "source-archive"
MANIFEST = ARCHIVE / "manifest.json"
URL_RE = re.compile(r'''https?://[^\s"'<>),;]+''')


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"createdBy": "iAccess source archiver", "items": []}


def save_manifest(manifest):
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    manifest["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_urls():
    db = json.loads((ROOT / "database.json").read_text(encoding="utf-8"))
    rows = []
    for collection, value in db.items():
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                continue
            label = item.get("title") or item.get("name") or item.get("documentTitle") or item.get("planName") or item.get("city") or ""
            for field, field_value in item.items():
                if not isinstance(field_value, str):
                    continue
                for match in URL_RE.finditer(field_value):
                    rows.append({
                        "url": match.group(0).rstrip(".,;"),
                        "collection": collection,
                        "index": index,
                        "field": field,
                        "label": label,
                    })
    unique = {}
    for row in rows:
        unique.setdefault(row["url"], row)
    return list(unique.values())


def extension_for(url, content_type):
    parsed_ext = Path(urlparse(url).path).suffix.lower()
    if parsed_ext in {".pdf", ".html", ".htm", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
        return parsed_ext
    content_type = (content_type or "").split(";")[0].strip().lower()
    if content_type == "application/pdf":
        return ".pdf"
    if content_type in {"text/html", "application/xhtml+xml"}:
        return ".html"
    if content_type.startswith("image/"):
        return mimetypes.guess_extension(content_type) or ".img"
    if content_type == "text/plain":
        return ".txt"
    return ".bin"


def archive_one(row, existing_by_url):
    url = row["url"]
    if url in existing_by_url and Path(existing_by_url[url].get("localPath", "")).exists():
        return {**existing_by_url[url], "skipped": True}

    headers = {"User-Agent": "iAccess source archiver contact hornick@iaccess.de"}
    response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
    response.raise_for_status()
    content = response.content
    digest = hashlib.sha256(content).hexdigest()
    ext = extension_for(response.url, response.headers.get("content-type", ""))
    host = re.sub(r"[^a-zA-Z0-9.-]+", "-", urlparse(response.url).netloc.lower()).strip("-") or "source"
    target_dir = ARCHIVE / host
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{digest[:16]}{ext}"
    target.write_bytes(content)

    item = {
        **row,
        "finalUrl": response.url,
        "status": response.status_code,
        "contentType": response.headers.get("content-type", ""),
        "bytes": len(content),
        "sha256": digest,
        "localPath": str(target.relative_to(ROOT)).replace("\\", "/"),
        "archivedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "skipped": False,
    }
    return item


def main():
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    existing_by_url = {item["url"]: item for item in manifest.get("items", [])}
    archived = []
    failed = []

    for row in collect_urls():
        try:
            item = archive_one(row, existing_by_url)
            existing_by_url[row["url"]] = item
            archived.append(item)
            print(f"{'skip' if item.get('skipped') else 'saved'} {row['url']} -> {item.get('localPath')}")
        except Exception as exc:
            failed.append({**row, "error": str(exc)})
            print(f"failed {row['url']} | {exc}")

    manifest["items"] = sorted(existing_by_url.values(), key=lambda item: item["url"])
    manifest["failed"] = failed
    save_manifest(manifest)
    print(json.dumps({
        "known": len(manifest["items"]),
        "savedOrSkipped": len(archived),
        "failed": len(failed),
        "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
