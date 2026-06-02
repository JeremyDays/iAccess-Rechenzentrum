import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
AVAILABILITY = ROOT / "pdf-availability.json"


def js_quote(value):
    return json.dumps(value, ensure_ascii=False)


def main():
    availability = json.loads(AVAILABILITY.read_text(encoding="utf-8"))
    text = INDEX.read_text(encoding="utf-8")
    replacements = 0

    for row in availability["items"]:
        if not row["localExists"]:
            continue
        old_source = row["currentSourceUrl"]
        public = row["publicUrl"]
        local_file = row["localFile"]
        if not old_source or not public:
            continue
        if row["ok"]:
            # Use the direct public PDF URL as source. The local file remains the save/fallback link.
            old = f'sourceUrl: {js_quote(old_source)},\n          localFile: {js_quote(local_file)},'
            new = f'sourceUrl: {js_quote(public)},\n          localFile: {js_quote(local_file)},'
            if old in text and old != new:
                text = text.replace(old, new, 1)
                replacements += 1
        else:
            # If the public URL is gone, prefer the local save as the primary link.
            old = f'sourceUrl: {js_quote(old_source)},\n          localFile: {js_quote(local_file)},'
            new = f'sourceUrl: {js_quote(local_file)},\n          localFile: {js_quote(local_file)},'
            if old in text and old != new:
                text = text.replace(old, new, 1)
                replacements += 1

    INDEX.write_text(text, encoding="utf-8")
    print(f"updated {replacements} PDF source links")


if __name__ == "__main__":
    main()
