import json
import re
import textwrap
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "pdfs"
OUT = ROOT / "pdf-extracts.json"
PDF_DIR.mkdir(exist_ok=True)

PDFS = [
    {
        "municipality": "Ahrensfelde",
        "title": "Planzeichnung B-Plan Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/NTY5MzdiYjJmM2Q2MmM3YzF0T1E4TFpNZG9mRUd2SFk1L05KUnZLZ1hUKzlNang2amJKNGVIUEgvYTdIZGpldkxIVWpNZ1FqMWczcVd0cE1vWTF1WDJCS1c4dkl3eU1mOW5NMmVOYytucks4ZUU3WGMraUxMbGVGTS9EaDAwc09EWDRoMW1ReFpjNGR5SW44dlRMWU1CakNCYjNrdU5FM2cwNHFFVzBBNkY3Qit3RXdzbjY2UkVPYmRBbz0",
    },
    {
        "municipality": "Wustermark",
        "title": "Begründung Bebauungsplan W 49 Rechenzentrum 1 Wustermark Nordwest",
        "url": "https://www.wustermark.de/PDF/W_49_Rechenzentrum_1_Wustermark_Nordwest_Begr%C3%BCndung.PDF?Ext=PDF&ObjID=583&ObjLa=1&ObjSvrID=3847&WTR=1&_ts=1743673153",
    },
    {
        "municipality": "Wustermark",
        "title": "Zusammenfassende Erklärung Bebauungsplan W 49",
        "url": "https://www.wustermark.de/PDF/W_49_Rechenzentrum_Wustermark_Nordwest_zusammenfassende_Erkl%C3%A4rung.PDF?Ext=PDF&ObjID=1057&ObjLa=1&ObjSvrID=3847&WTR=1&_ts=1779361011",
    },
    {
        "municipality": "Wustermark",
        "title": "Vorstudie zur Nutzung der Abwärme des Rechenzentrums Wustermark",
        "url": "https://www.wustermark.de/PDF/Vorstudie_zur_Nutzung_der_Abw%C3%A4rme_des_Rechenzentrums_Wustermark.PDF?Ext=PDF&ObjID=945&ObjLa=1&ObjSvrID=3847&WTR=1&_ts=1771580975",
    },
    {
        "municipality": "Ahrensfelde",
        "title": "Begründung Bebauungsplan Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/NDEyYTJlMTI2ZjI3MWM5NlM4UnNyMXlZNUtSSDFkVjVYQkZOQzZRM2tVQ1drTm1GRENaSVp5Q01FVzFZRFh3bDkvMS9hemtqY1Jib2pYaWU1ZkFFTFFuZDdSczBPeW1KVjV3eGRSUGxZNEdOQWhWSi9YMUsyN2Y1TUlwcFlmTk9wTEtoZ2ZTbFFud0RJb0U2LzB3bU1FZXVCU3pUOGE2RWZ3T1hnVk1QMXlia0wvbjgrZDJUZVpKWGlFWT0",
    },
    {
        "municipality": "Ahrensfelde",
        "title": "Umweltbericht B-Plan Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/MjkzOGFjZjVkNzQzZWYxZmRvTzZlbkZ3cFNuT1loeG5udXVHQXgrUzIrQ285VVhEaGpnM0ZSYzZBcWtiNWdLKzhQaUwrcE05dVZ0cEdRSSsvSFZUd1dEbUU0NFUwVjYxUzJhK3hTOE4xdDRGOWw3V3hIaTVCLzBGbmh3RnFMTG9Wc1I4Uit2WUk4WWhxbXkwcllxRW9RdzF6Vy9TTGxUWlF3cjB0QT09",
    },
    {
        "municipality": "Ahrensfelde",
        "title": "Artenschutzpotentialanalyse Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/MTBmODhkMzIyNTAyNzEzM3E1WE1odnpBWXU4VjVWWTZVK1ZhSWN0UjdrclRDVnQ5Z0c0RDVBY2dLTjhQNE4ra3hxQ1BOZFlNZmtoVUZxaFZ3TDNyUllzTFJhbGhxeVE4emlHNmtnVEtDTDNJT3Rud2NIdHJEcWdMazJ5OUxIVFhhQ2l3Z3UrRld6b0ZUMWlKWlIxMkRXbTQ1c2R3bWFVQlhabU1GQT09",
    },
    {
        "municipality": "Ahrensfelde",
        "title": "Regenwasserkonzept Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/YTViMjQyZjdhNzg3ZDFjZVp3Z2UxM3hLcURNRnEyd2Vkb0M5VjgrUkI4aGExN2F0MjF1ZlgzVUFpSHJhczdvMGsxTy82MU1yRTdPVVRWSm1ZVnA2QjRHaVplSUJxL0padnZKdHFsTENYVjEwait6VjJHOWZOMktGamJnd3pVRTY0eHRMNmRweVJqRU5iWk1R",
    },
    {
        "municipality": "Ahrensfelde",
        "title": "Verkehrsuntersuchung Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/OTE3ZmMyMGVlYzk1NzM5M3NGT25YVy9EeURtOXVvU1NOU1AwWndqR1k0SU43VFRNRk0vUE14OTRrR3Y2bUFSVWs4RTRwdVpEVWY4b2VDemlZOEpHVE80c0hJZzFGdm1Dem5vT0JBSTVpSVhnSFNoYlJkckt0Y0hKVGM5SEdtSUlrMmVKUms3dXBKeUVCcnRBOFAwb04wWS8wWU50Z2dXVzVYV2JtdnlRdk55VGw4YlcwYUhDNVg2TnVLZz0",
    },
    {
        "municipality": "Ahrensfelde",
        "title": "Schalltechnische Untersuchung Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/ZGE1MDg3NGVlMWZiZTg0MFdaVWJpTC9JTFl4Z0lHWGRDQjF5MGlNWmJwLzZFdVY3NEFxRWZRNXg1blR2OE9BeXVVeE5PMHJ5WWw3Yjh3dFd5VmlkNUlhV1c5aW5aVXVaREpqNHd5WXh0SWI3S0FTWjN2em9oRlAvdE94Zy94R2pLSUg2QkpMek9sTE11cmxsN3h2aEdJZGI0aHRycGZmd2FCc1plOXB3b243b2RNRHJhU1M2dGRvMk1UWT0",
    },
    {
        "municipality": "Ahrensfelde",
        "title": "Geotechnischer Bericht Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/MDljMGI4ZDNjODdkZjdlZUtzRnIvRENZRW56MmVyTjZLUVdPTWdLdmtmRXlVM2ZQZFBGY3NZelhzdVdSaGVkSzVjRVFyVmltVENLSmN6ei9WZG16ZjMyYUs4d2RCaEthWHB6QUl5WnFzbWZsdm9yd0VtdjRkdlZZTGxGY0YwSUxaczJIMUEydVRmcU9LWEQ5R1N3Qk9RcHA5S3NDaEo0WjcyT1NJUT09",
    },
    {
        "municipality": "Ahrensfelde",
        "title": "Altlastengutachten Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/NzZlMjBhOTQ3ZTMzY2YwMm9YVFZsMmFKMXQwT3Q3NUpKWERaYzA1dGhlNjBkNVREaUZGTk9peXAySjVmNVhBKzREMUlvTUhQNWd4eWMxS0lJeUxmcmlBWkdmblRSSnYrOXNqbW1MajNhOHFNeWhXMUFpdkFSUEpQdHZMVlJkYWVLcnoydXY3dVhhdGxORUQxUTZXQTgyNUMrcXhuaVNoY1JldmVwZz09",
    },
    {
        "municipality": "Ahrensfelde",
        "title": "Abwärmenutzung Rechenzentrum Eiche",
        "url": "https://www.ahrensfelde.de/downloads/datei/ODAwOTY2MDFiY2VhNmQ4OHpoTS9ZSTQxQUxvakJtTmxEN1dkVURPdHZwRHQ2Vmh4NXo3blZXLzF4YlNROHRydVQrMFlhUTBFNWpLWmM0R0hhWU01R09DdmZ2MlN4RTRxdkFRNXlKbnR3RWx6MkVDelRrVmNHMjZZd1YyT2kvSTJ0ZEx6djJ6c3U2NE9WWVVub3NDYWV6SCtDKzcrSENRNSs5WStNZz09",
    },
    {
        "municipality": "Babenhausen",
        "title": "Begründung Bebauungsplan Aschaffenburger Straße 50-58",
        "url": "https://www.babenhausen.de/bauen-planen-und-umwelt/bebauungsplaene/bestandskraeftige-bebauungsplaene/google-aschaffenburger-strasse/20210819-bp-begruendung-sb-pb90082-p.pdf?cid=bkz",
    },
    {
        "municipality": "Brieselang",
        "title": "UVPG-Vorprüfung Bebauungsplan Nr. 117 Rechenzentrum",
        "url": "https://www.gemeindebrieselang.de/city_info/display/dokument/show.cfm?id=421319&region_id=342",
    },
    {
        "municipality": "Ankum",
        "title": "Kurzerläuterung Bebauungsplan Nr. 66 Sondergebiet Rechenzentrum am Lordsee",
        "url": "https://sgbsb.de/wp-content/uploads/2024/09/66_Kurzerlaeuterung.pdf",
    },
    {
        "municipality": "Heusenstamm",
        "title": "RP Darmstadt Bescheid EdgeConneX Rechenzentrum Heusenstamm",
        "url": "https://rp-darmstadt.hessen.de/sites/rp-darmstadt.hessen.de/files/2026-04/besch_ie-rl-rz_heusenstamm_edgeconnex_2026_02_16.pdf",
    },
    {
        "municipality": "Werneuchen",
        "title": "Bebauungsplan Rechenzentrum Seefeld PDF",
        "url": "https://www.werneuchen-barnim.de/downloads/datei/MDA5NzkzOGYyNzAwMDJkMnlmK0x3MktFNnN2aytCWnRqNSticXVHR1NtRUY3TXBUcDlwNFlhWEs4cDNOcjFJOW1xUFNndjFDTlR6a3NxdGdYRTlxQURhYWI0NUdQeTRublBLT09mTjQ1MkxIZ25NaHVkNlJ0VnRta2RSc2d4UWp6OWNadEM2RDJLTHFvUitTeVhNbG1GcTAwc3BsVGN6MWowSEVyNi9XVFFyR3c5NXozNGg0WlF6dzJycz0",
    },
]

KEYWORDS = [
    "Sondergebiet", "Rechenzentrum", "Data Center", "Datacenter", "Abwärme",
    "Strom", "Anschlussleistung", "MW", "MVA", "Wasser", "Löschwasser",
    "Brandschutz", "Niederschlagswasser", "Schall", "Lärm", "Kühlung",
    "Bebauungsplan", "Flächennutzungsplan", "Umspannwerk", "Generator",
]


def slug(value):
    value = re.sub(r"[^a-zA-Z0-9äöüÄÖÜß]+", "-", value.lower()).strip("-")
    return value[:80] or "document"


def download(item):
    target = PDF_DIR / f"{slug(item['municipality'] + '-' + item['title'])}.pdf"
    if target.exists() and target.stat().st_size > 1000:
        return target
    req = Request(item["url"], headers={"User-Agent": "iaccess-pdf-extractor"})
    with urlopen(req, timeout=45) as response:
        target.write_bytes(response.read())
    return target


def read_pdf(path):
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append((i, re.sub(r"\s+", " ", text).strip()))
    return pages


def snippets(pages):
    results = []
    seen = set()
    pattern = re.compile("|".join(re.escape(k) for k in KEYWORDS), re.I)
    for page_no, text in pages:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 380)
            end = min(len(text), match.end() + 520)
            snippet = text[start:end].strip()
            snippet = textwrap.shorten(snippet, width=900, placeholder=" ...")
            marker = (page_no, snippet[:120])
            if marker not in seen:
                results.append({"page": page_no, "text": snippet})
                seen.add(marker)
            if len(results) >= 18:
                return results
    return results


def main():
    extracted = []
    for item in PDFS:
        record = dict(item)
        try:
            path = download(item)
            pages = read_pdf(path)
            text = "\n".join(page_text for _, page_text in pages)
            record.update({
                "file": str(path.relative_to(ROOT)),
                "pages": len(pages),
                "characters": len(text),
                "snippets": snippets(pages),
            })
        except Exception as exc:
            record.update({"error": str(exc), "snippets": []})
        extracted.append(record)
    OUT.write_text(json.dumps(extracted, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT.name}: {len(extracted)} PDFs")
    for item in extracted:
        status = "error" if item.get("error") else f"{item.get('pages', 0)} pages"
        print(f"- {item['municipality']}: {status}, {len(item.get('snippets', []))} snippets")


if __name__ == "__main__":
    main()
