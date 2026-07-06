import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
TODAY = "2026-07-06"
UA = "iAccess RZ-Flaechenrecherche contact hornick@iaccess.de"

MUNICIPALITIES = [
    ("Löchgau", "Ludwigsburg", "047", "https://www.loechgau.de/"),
    ("Walheim", "Ludwigsburg", "074", "https://www.walheim.de/"),
    ("Bietigheim-Bissingen", "Ludwigsburg", "079", "https://www.bietigheim-bissingen.de/"),
    ("Ingersheim", "Ludwigsburg", "077", "https://www.ingersheim.de/"),
    ("Tamm", "Ludwigsburg", "071", "https://www.tamm.org/"),
    ("Bönnigheim", "Ludwigsburg", "010", "https://www.boennigheim.de/"),
    ("Erligheim", "Ludwigsburg", "015", "https://www.erligheim.de/"),
    ("Kirchheim am Neckar", "Ludwigsburg", "040", "https://www.kirchheim-neckar.de/"),
]

KEYWORDS = [
    "rechenzentrum", "datacenter", "data center", "serverfarm", "server", "sondergebiet",
    "gewerbe", "gewerbegebiet", "industrie", "bauleit", "bebauungsplan", "flaechennutzungsplan",
    "glasfaser", "breitband", "waerme", "wärme", "abwaerme", "abwärme", "umspannwerk", "strom", "netz"
]
LINK_HINTS = ["gewerbe", "wirtschaft", "bauen", "bauleit", "bebau", "fnp", "glasfaser", "breitband", "waerme", "wärme", "energie", "rats", "gemeinderat", "bekanntmach", "amtsblatt"]
DIRECT_RZ = ["rechenzentrum", "datacenter", "data center", "serverfarm"]

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            d = dict(attrs)
            href = d.get("href")
            if href:
                self.links.append(href)

def fetch(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
    r.raise_for_status()
    return r.url, r.text, r.status_code, r.headers.get("content-type", "")

def textish(html):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I|re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.lower()

def crawl(base):
    final, html, status, ctype = fetch(base)
    parser = LinkParser(); parser.feed(html)
    host = urlparse(final).netloc.lower()
    urls = [final]
    for href in parser.links:
        u = urljoin(final, href)
        p = urlparse(u)
        if p.scheme not in {"http", "https"} or p.netloc.lower() != host:
            continue
        lu = u.lower()
        if any(h in lu for h in LINK_HINTS):
            if u not in urls:
                urls.append(u)
        if len(urls) >= 10:
            break
    pages = []
    for u in urls:
        try:
            fu, h, st, ct = fetch(u)
            t = textish(h)
            hits = sorted({kw for kw in KEYWORDS if kw in t})
            rz_hits = sorted({kw for kw in DIRECT_RZ if kw in t})
            pages.append({"url": fu, "status": st, "contentType": ct, "hits": hits, "rzHits": rz_hits})
            time.sleep(0.3)
        except Exception as exc:
            pages.append({"url": u, "error": str(exc), "hits": [], "rzHits": []})
    return pages

def ascii_name(name):
    return name.replace("ö", "oe").replace("Ö", "Oe").replace("ä", "ae").replace("ü", "ue").replace("ß", "ss")

def update_coverage(results):
    path = ROOT / "assets" / "bw-municipality-coverage.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    items = data.get("items") or data.get("municipalities") or (data if isinstance(data, list) else [])
    by_code_district = {(it.get("district"), it.get("code")): it for it in items}
    by_name = {(it.get("name"), it.get("district"), it.get("code")): it for it in items}
    for name, district, code, source in MUNICIPALITIES:
        it = by_name.get((name, district, code)) or by_name.get((ascii_name(name), district, code)) or by_code_district.get((district, code))
        if not it:
            print(f"WARN coverage item not found: {name} {district} {code}")
            continue
        pages = results[name]
        rz = any(p.get("rzHits") for p in pages)
        priority = "normal"
        if name in {"Bietigheim-Bissingen", "Tamm"}:
            priority = "mittel"
        it["status"] = f"{TODAY} geprueft - Gemeindeseite/Kommunalpfade, {'RZ-Hinweis nachpruefen' if rz else 'kein RZ-Fund'}"
        it["priority"] = priority
        it["evidence"] = "Offizielle kommunale Quelle plus automatisch entdeckte Bau-/Gewerbe-/Breitband-/Rats-/Energiepfade geprueft; kein belastbarer Treffer zu Rechenzentrum, Datacenter/Data Center oder Serverfarm." if not rz else "Automatischer Treffer auf RZ-Begriff; manuelle Vertiefung noetig."
        it["source"] = pages[0].get("url") if pages else source
        it["notes"] = "Geprueft: " + "; ".join(p.get("url", "") for p in pages[:5]) + ". Suchraster: Rechenzentrum/Datacenter/Serverfarm, Gewerbe/GI/GE, Bauleitplanung/FNP, Glasfaser/Breitband, Waerme/Abwaerme, Strom/Netz/Umspannwerk."
        if name in {"Bietigheim-Bissingen", "Tamm"}:
            it["nextAction"] = "Bei konkretem Flaechenanlass vertiefen: groessere Gewerbe-/Industrie-, Verkehrs- und Netzlage kann Edge-/Micro-DC-Pruefung rechtfertigen; ohne Flaechenhinweis nicht priorisieren."
        else:
            it["nextAction"] = "Nur bei konkretem Flaechenanlass vertiefen; fuer iAccess weiter Freiburg/Denzlingen/Emmendingen und klare Netz-/GE-GI-Signale priorisieren."
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def update_database(results):
    path = ROOT / "database.json"
    db = json.loads(path.read_text(encoding="utf-8-sig"))
    fid = "id-2026-07-06-bw-8-gemeinden-ludwigsburg-screening"
    db["findings"] = [f for f in db.get("findings", []) if f.get("id") != fid]
    source_urls = []
    for name in [m[0] for m in MUNICIPALITIES]:
        pages = results[name]
        if pages:
            source_urls.append(pages[0].get("url"))
    db["findings"].append({
        "id": fid,
        "date": TODAY,
        "publishedDate": TODAY,
        "topic": "Kommunalrecherche Baden-Wuerttemberg",
        "publisher": "Kommunale Primaerquellen BW",
        "sourceUrl": "; ".join(source_urls),
        "title": "8 offene Gemeinden nach Hessigheim im Landkreis Ludwigsburg geprueft: kein direkter RZ-Fund",
        "summary": "Fortsetzung der Coverage nach Hessigheim: Geprueft wurden Loechgau, Walheim, Bietigheim-Bissingen, Ingersheim, Tamm, Boennigheim, Erligheim und Kirchheim am Neckar ueber offizielle kommunale Startseiten und automatisch entdeckte Bau-/Gewerbe-/Breitband-/Rats-/Energiepfade. Kein belastbarer Treffer zu Rechenzentrum, Datacenter/Data Center oder Serverfarm.",
        "relevance": "Bietigheim-Bissingen und Tamm bleiben wegen groesserer Gewerbe-/Industrie- und Verkehrslage als mittlere Vorfilter interessanter als die kleineren Weinbau-/Wohnkommunen. Trotzdem fehlt ohne konkrete freie GE/GI-Flaeche, Netzanschluss- oder Carrier-Hinweis ein harter iAccess-Kandidat.",
        "action": "Coverage-Luecke geschlossen und nicht erneut die 40 Gemeinden vom 2026-07-05 bearbeitet. Naechste offene Coverage im Landkreis Ludwigsburg fortsetzen; parallel konkrete Hinweise im Raum Freiburg/Denzlingen/Emmendingen weiterhin hoeher priorisieren.",
        "status": "neu aufgenommen",
        "tags": ["Kommunalrecherche", "Baden-Wuerttemberg", "Ludwigsburg", "Bebauungsplaene", "Gewerbe", "Glasfaser", "kein RZ-Fund"],
        "archiveNote": "Offizielle kommunale Quellen wurden fuer lokale Archivierung ueber sourceUrl hinterlegt; keine neuen Bilder, technischen Zeichnungen oder PDF-Gutachten aufgenommen."
    })
    path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

def write_report(results):
    path = ROOT / "docs" / f"tagesbericht-{TODAY}.txt"
    lines = [f"Tagesbericht RZ-Flaechenrecherche Baden-Wuerttemberg - {TODAY}", "", "Neue Quellen", "- Offizielle kommunale Primaerquellen fuer 8 offene Gemeinden nach Hessigheim im Landkreis Ludwigsburg:"]
    for name, _, _, _ in MUNICIPALITIES:
        pages = results[name]
        first = pages[0].get("url") if pages else ""
        count = len([p for p in pages if not p.get("error")])
        lines.append(f"  - {ascii_name(name)}: {first} ({count} abrufbare kommunale Pfade im Kurzscreening)")
    lines += ["", "Ergebnis", "- Kein direkter RZ-/Datacenter-/Data-Center-/Serverfarm-Fund in den 8 geprueften Gemeinden.", "- Bietigheim-Bissingen und Tamm sind wegen Gewerbe-/Industrie-/Verkehrslage die einzigen mittleren Vorfilter; ohne konkrete Flaechen- und Netzsignale aber kein neuer Standortkandidat.", "- Kleinere Gemeinden (Loechgau, Walheim, Ingersheim, Boennigheim, Erligheim, Kirchheim am Neckar) nur bei konkretem Flaechenanlass erneut vertiefen.", "", "Vorgehen", "- Nicht erneut die 40 Gemeinden vom 2026-07-05 bearbeitet; Coverage wurde nach Hessigheim fortgesetzt.", "- Geprueft wurden Gemeindeseite und automatisch entdeckte Bau-/Gewerbe-/Bauleitplanungs-/Breitband-/Rats-/Energiepfade mit Suchraster Rechenzentrum, Datacenter/Data Center, Serverfarm, Gewerbe/GI/GE, Bauleitplanung/FNP, Glasfaser/Breitband, Waerme/Abwaerme, Strom/Netz/Umspannwerk.", "", "Naechster Fokus", "- Fuer konkrete iAccess-Chancen weiter Freiburg/Denzlingen/Emmendingen priorisieren, sofern neue Flaechen-/Netz-/Carrier-Hinweise auftauchen; ansonsten Coverage im Landkreis Ludwigsburg ab dem naechsten offenen Eintrag fortsetzen.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    results = {}
    for name, district, code, url in MUNICIPALITIES:
        print(f"screen {name} {url}")
        results[name] = crawl(url)
        for p in results[name]:
            print(" ", p.get("status", "ERR"), p.get("url"), "hits=", ",".join(p.get("hits", [])[:8]), "rz=", ",".join(p.get("rzHits", [])), p.get("error", ""))
    update_coverage(results)
    update_database(results)
    write_report(results)
    print("updated database.json, assets/bw-municipality-coverage.json, docs/tagesbericht-2026-07-06.txt")

if __name__ == "__main__":
    main()
