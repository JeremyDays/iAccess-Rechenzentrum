import json
from datetime import date
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else []


def check_url(url):
    if not url:
        return {"ok": False, "status": None, "finalUrl": "", "error": "missing url"}
    headers = {"User-Agent": "iAccess PDF checker contact hornick@iaccess.de"}
    try:
        response = requests.head(url, headers=headers, timeout=20, allow_redirects=True)
        if response.status_code in {403, 405, 406, 429} or response.status_code >= 500:
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True, stream=True)
        return {
            "ok": 200 <= response.status_code < 400,
            "blocked": response.status_code in {403, 429},
            "status": response.status_code,
            "finalUrl": response.url,
            "contentType": response.headers.get("content-type", ""),
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "blocked": False, "status": None, "finalUrl": "", "contentType": "", "error": str(exc)}


def main():
    db = json.loads((ROOT / "database.json").read_text(encoding="utf-8-sig"))
    extracted = load_json(ROOT / "pdf-extracts.json")
    direct_by_title = {item.get("title"): item.get("url") for item in extracted if item.get("title") and item.get("url")}
    direct_by_file = {str(item.get("file", "")).replace("\\", "/"): item.get("url") for item in extracted if item.get("file") and item.get("url")}

    rows = []
    for item in db.get("pdfExtracts", []):
        local_file = (item.get("localFile") or "").replace("\\", "/")
        local_path = ROOT / local_file if local_file else None
        local_ok = bool(local_path and local_path.exists())
        direct_url = direct_by_file.get(local_file) if local_ok else ""
        direct_url = direct_url or direct_by_title.get(item.get("documentTitle")) if local_ok else ""
        public_url = direct_url or item.get("sourceUrl") or ""
        status = check_url(public_url)
        rows.append(
            {
                "municipality": item.get("municipality", ""),
                "documentTitle": item.get("documentTitle", ""),
                "documentType": item.get("documentType", ""),
                "pages": item.get("pages", ""),
                "publicUrl": public_url,
                "currentSourceUrl": item.get("sourceUrl", ""),
                "localFile": local_file,
                "localExists": local_ok,
                "localBytes": local_path.stat().st_size if local_ok else 0,
                **status,
            }
        )

    output = {
        "checkedAt": date.today().isoformat(),
        "total": len(rows),
        "localAvailable": sum(1 for row in rows if row["localExists"]),
        "publicAvailable": sum(1 for row in rows if row["ok"]),
        "publicBlocked": sum(1 for row in rows if row.get("blocked")),
        "publicUnavailable": sum(1 for row in rows if not row["ok"] and not row.get("blocked")),
        "items": rows,
    }
    target = ROOT / "pdf-availability.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: output[k] for k in ["total", "localAvailable", "publicAvailable", "publicBlocked", "publicUnavailable"]}, ensure_ascii=False, indent=2))
    for row in rows:
        if not row["ok"]:
            marker = "blocked" if row.get("blocked") else "unavailable"
            print(f"{marker} | {row['municipality']} | {row['documentTitle']} | {row['status']} | local={row['localExists']} | {row['publicUrl']} | {row['error']}")


if __name__ == "__main__":
    main()
