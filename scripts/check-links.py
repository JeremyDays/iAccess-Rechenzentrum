import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
URL_RE = re.compile(r'''https?://[^\s"'<>),;]+''')


def collect_urls():
    db = json.loads((ROOT / "database.json").read_text(encoding="utf-8-sig"))
    rows = []
    for collection, value in db.items():
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name") or item.get("documentTitle") or item.get("planName") or item.get("city") or ""
            for field, field_value in item.items():
                if not isinstance(field_value, str):
                    continue
                for match in URL_RE.finditer(field_value):
                    rows.append(
                        {
                            "collection": collection,
                            "index": index,
                            "field": field,
                            "title": title,
                            "url": match.group(0).rstrip(".,;"),
                        }
                    )
    unique = {}
    for row in rows:
        unique.setdefault(row["url"], row)
    return list(unique.values())


def check(row):
    url = row["url"]
    headers = {"User-Agent": "iAccess link checker contact hornick@iaccess.de"}
    result = {**row, "status": None, "finalUrl": "", "ok": False, "blocked": False, "error": ""}
    try:
        response = requests.head(url, headers=headers, timeout=25, allow_redirects=True)
        if response.status_code in {403, 405, 406, 429} or response.status_code >= 500:
            response = requests.get(url, headers=headers, timeout=45, allow_redirects=True, stream=True)
        result["status"] = response.status_code
        result["finalUrl"] = response.url
        result["ok"] = 200 <= response.status_code < 400
        result["blocked"] = response.status_code in {403, 429}
    except Exception as exc:
        result["error"] = str(exc)
    return result


def main():
    rows = collect_urls()
    print(f"checking {len(rows)} unique URLs", file=sys.stderr)
    results = []
    workers = min(12, max(4, len(rows) // 8))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(check, row) for row in rows]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: (item["ok"], item["collection"], item["title"], item["url"]))
    output = {
        "checked": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "blocked": sum(1 for item in results if item.get("blocked")),
        "broken": sum(1 for item in results if not item["ok"] and not item.get("blocked")),
        "results": results,
    }
    target = ROOT / "link-check-results.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: output[k] for k in ["checked", "ok", "blocked", "broken"]}, ensure_ascii=False, indent=2))
    for item in results:
        if not item["ok"] and not item.get("blocked"):
            print(f"{item['collection']} | {item['field']} | {item['status']} | {item['title']} | {item['url']} | {item['error']}")


if __name__ == "__main__":
    main()
