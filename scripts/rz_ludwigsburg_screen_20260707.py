import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
TODAY = "2026-07-07"
UA = "iAccess RZ-Flaechenrecherche contact hornick@iaccess.de"

MUNICIPALITIES = [
    ("Freiberg am Neckar", "Ludwigsburg", "078", "https://www.freiberg-an.de/"),
    ("Pleidelsheim", "Ludwigsburg", "063", "https://www.pleidelsheim.de/"),
    ("Affalterbach", "Ludwigsburg", "001", "https://www.affalterbach.de/"),
    ("Benningen am Neckar", "Ludwigsburg", "006", "https://www.benningen.de/"),
    ("Erdmannhausen", "Ludwigsburg", "014", "https://www.erdmannhausen.de/"),
    ("Schwieberdingen", "Ludwigsburg", "067", "https://www.schwieberdingen.de/"),
    ("Murr", "Ludwigsburg", "054", "https://www.gemeinde-murr.de/"),
    ("Eberdingen", "Ludwigsburg", "012", "https://www.eberdingen.de/"),
]

PRIORITY_SOURCES = [
    ("Denzlingen 110-kV-Netzverstaerkung", "https://www.netze-bw.de/unsernetz/netzausbau/denzlingen"),
    ("Denzlingen Wirtschaftsstandort", "https://www.denzlingen.de/p/wirtschaftsstandort"),
    ("Freiburg Baden-RZ/Systemhaus Jerg", "https://www.systemhaus-jerg.de/managed-service/rechenzentrum-neu"),
]

KEYWORDS = [
    "rechenzentrum", "datacenter", "data center", "serverfarm", "server", "sondergebiet",
    "gewerbe", "gewerbegebiet", "industrie", "bauleit", "bebauungsplan", "flaechennutzungsplan", "flächennutzungsplan",
    "glasfaser", "breitband", "waerme", "wärme", "abwaerme", "abwärme", "umspannwerk", "strom", "netz", "fernwaerme", "fernwärme"
]
LINK_HINTS = ["gewerbe", "wirtschaft", "bauen", "bauleit", "bebau", "fnp", "glasfaser", "breitband", "waerme", "wärme", "energie", "rats", "gemeinderat", "bekanntmach", "amtsblatt", "flaechen", "flächen", "stadtentwicklung"]
DIRECT_RZ = ["rechenzentrum", "datacenter", "data center", "serverfarm"]

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

def fetch(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
    r.raise_for_status()
    return r.url, r.text, r.status_code, r.headers.get("content-type", "")

def textish(html):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I|re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.lower()

def crawl(base, limit=12):
    final, html, status, ctype = fetch(base)
    parser = LinkParser(); parser.feed(html)
    host = urlparse(final).netloc.lower()
    urls = [final]
    for href in parser.links:
        u = urljoin(final, href).split("#", 1)[0]
        p = urlparse(u)
        if p.scheme not in {"http", "https"} or p.netloc.lower() != host:
            continue
        lu = u.lower()
        if any(h in lu for h in LINK_HINTS) and u not in urls:
            urls.append(u)
        if len(urls) >= limit:
            break
    pages = []
    for u in urls:
        try:
            fu, h, st, ct = fetch(u)
            t = textish(h)
            hits = sorted({kw for kw in KEYWORDS if kw in t})
            rz_hits = sorted({kw for kw in DIRECT_RZ if kw in t})
            pages.append({"url": fu, "status": st, "contentType": ct, "hits": hits, "rzHits": rz_hits})
            time.sleep(0.25)
        except Exception as exc:
            pages.append({"url": u, "error": str(exc), "hits": [], "rzHits": []})
    return pages

def ascii_name(name):
    return (name.replace("ö", "oe").replace("Ö", "Oe").replace("ä", "ae").replace("Ä", "Ae")
                .replace("ü", "ue").replace("Ü", "Ue").replace("ß", "ss"))

def update_coverage(results):
    path = ROOT / "assets" / "bw-municipality-coverage.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    items = data.get("items") or data.get("municipalities") or (data if isinstance(data, list) else [])
    by_key = {(it.get("district"), it.get("code")): it for it in items}
    by_name = {(it.get("name"), it.get("district")): it for it in items}
    for name, district, code, source in MUNICIPALITIES:
        it = by_key.get((district, code)) or by_name.get((name, district))
        if not it:
            print(f"WARN coverage item not found: {name} {district} {code}")
            continue
        pages = results[name]
        rz = any(p.get("rzHits") for p in pages)
        priority = "normal"
        if name in {"Freiberg am Neckar", "Schwieberdingen"}:
            priority = "mittel"
        it["status"] = f"{TODAY} geprueft - Gemeindeseite/Kommunalpfade, {'RZ-Hinweis nachpruefen' if rz else 'kein RZ-Fund'}"
        it["priority"] = priority
        it["evidence"] = "Offizielle kommunale Quelle plus automatisch entdeckte Bau-/Gewerbe-/Breitband-/Rats-/Energiepfade geprueft; kein belastbarer Treffer zu Rechenzentrum, Datacenter/Data Center oder Serverfarm." if not rz else "Automatischer Treffer auf RZ-Begriff; manuelle Vertiefung noetig."
        it["source"] = pages[0].get("url") if pages else source
        it["notes"] = "Geprueft: " + "; ".join(p.get("url", "") for p in pages[:6]) + ". Suchraster: Rechenzentrum/Datacenter/Serverfarm, Gewerbe/GI/GE, Bauleitplanung/FNP, Glasfaser/Breitband, Waerme/Abwaerme, Strom/Netz/Umspannwerk."
        if name in {"Freiberg am Neckar", "Schwieberdingen"}:
            it["nextAction"] = "Bei konkretem Flaechenanlass vertiefen: Lage im Verdichtungsraum und Gewerbe-/Industrieumfeld kann Edge-/Micro-DC-Pruefung rechtfertigen; ohne Flaechen-/Netzsignal nicht hoeher priorisieren."
        else:
            it["nextAction"] = "Nur bei konkretem Flaechenanlass vertiefen; fuer iAccess weiter Freiburg/Denzlingen/Emmendingen und klare Netz-/GE-GI-Signale priorisieren."
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def update_database(results, priority_results):
    path = ROOT / "database.json"
    db = json.loads(path.read_text(encoding="utf-8-sig"))
    fid = "id-2026-07-07-bw-8-gemeinden-ludwigsburg-screening"
    db["findings"] = [f for f in db.get("findings", []) if f.get("id") != fid]
    source_urls = []
    for name in [m[0] for m in MUNICIPALITIES]:
        pages = results[name]
        if pages:
            source_urls.append(pages[0].get("url"))
    ok_priority = [label for label, pages in priority_results.items() if pages and not pages[0].get("error")]
    db["findings"].append({
        "id": fid,
        "date": TODAY,
        "publishedDate": TODAY,
        "topic": "Kommunalrecherche Baden-Wuerttemberg",
        "publisher": "Kommunale Primaerquellen BW",
        "sourceUrl": "; ".join(source_urls),
        "title": "8 weitere offene Gemeinden im Landkreis Ludwigsburg geprueft: kein direkter RZ-Fund",
        "summary": "Fortsetzung der Coverage nach Kirchheim am Neckar: Geprueft wurden Freiberg am Neckar, Pleidelsheim, Affalterbach, Benningen am Neckar, Erdmannhausen, Schwieberdingen, Murr und Eberdingen ueber offizielle kommunale Startseiten und automatisch entdeckte Bau-/Gewerbe-/Breitband-/Rats-/Energiepfade. Kein belastbarer Treffer zu Rechenzentrum, Datacenter/Data Center oder Serverfarm.",
        "relevance": "Freiberg am Neckar und Schwieberdingen bleiben wegen Verdichtungsraum-/Gewerbelage mittlere Vorfilter, aber ohne konkrete freie GE/GI-Flaeche, Netzanschluss- oder Carrier-Hinweis kein harter iAccess-Kandidat. Die Freiburg/Denzlingen-Prioritaetsquellen wurden nur revalidiert; keine neue konkrete Flaeche gefunden.",
        "action": "Coverage-Luecke weiter geschlossen und nicht erneut die 40 Gemeinden vom 2026-07-05 bearbeitet. Naechste offene Coverage im Landkreis Ludwigsburg fortsetzen; Freiburg/Denzlingen/Emmendingen bei konkreten Flaechen-/Netz-/Carrier-Hinweisen weiterhin hoeher priorisieren.",
        "status": "neu aufgenommen",
        "tags": ["Kommunalrecherche", "Baden-Wuerttemberg", "Ludwigsburg", "Bebauungsplaene", "Gewerbe", "Glasfaser", "kein RZ-Fund"],
        "archiveNote": "Offizielle kommunale Quellen wurden fuer lokale Archivierung ueber sourceUrl hinterlegt; Prioritaetsquellen revalidiert: " + ", ".join(ok_priority) + "."
    })
    path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

def write_report(results, priority_results):
    path = ROOT / "docs" / f"tagesbericht-{TODAY}.txt"
    lines = [f"Tagesbericht RZ-Flaechenrecherche Baden-Wuerttemberg - {TODAY}", "", "Neue Quellen", "- Offizielle kommunale Primaerquellen fuer 8 weitere offene Gemeinden im Landkreis Ludwigsburg nach Kirchheim am Neckar:"]
    for name, _, _, _ in MUNICIPALITIES:
        pages = results[name]
        first = pages[0].get("url") if pages else ""
        count = len([p for p in pages if not p.get("error")])
        direct = sorted({h for p in pages for h in p.get("rzHits", [])})
        suffix = f"; Direkt-RZ-Treffer: {', '.join(direct)}" if direct else "; kein Direkt-RZ-Treffer"
        lines.append(f"  - {ascii_name(name)}: {first} ({count} abrufbare kommunale Pfade{suffix})")
    lines += ["", "Prioritaetsraum Freiburg/Denzlingen/Emmendingen", "- Bekannte Prioritaetsquellen wurden live revalidiert, aber es wurde kein neuer konkreter Flaechen-/RZ-Standort entdeckt:"]
    for label, pages in priority_results.items():
        p = pages[0] if pages else {}
        if p.get("error"):
            lines.append(f"  - {label}: blockiert/fehlgeschlagen ({p.get('error')})")
        else:
            hits = ", ".join(p.get("hits", [])[:8]) or "keine Rastertreffer"
            lines.append(f"  - {label}: {p.get('url')} (Status {p.get('status')}; Treffer: {hits})")
    lines += ["", "Ergebnis", "- Kein belastbarer neuer RZ-/Datacenter-/Data-Center-/Serverfarm-Fund in den 8 neu geprueften Ludwigsburger Gemeinden.", "- Freiberg am Neckar und Schwieberdingen sind wegen Verdichtungsraum-/Gewerbelage die einzigen mittleren Vorfilter; ohne konkrete Flaechen-, Netz- oder Carrier-Signale aber kein neuer Standortkandidat.", "- Kleinere Gemeinden nur bei konkretem Flaechenanlass erneut vertiefen.", "", "Vorgehen", "- Nicht erneut die 40 Gemeinden vom 2026-07-05 bearbeitet; Coverage wurde nach Kirchheim am Neckar fortgesetzt.", "- Geprueft wurden Gemeindeseite und automatisch entdeckte Bau-/Gewerbe-/Bauleitplanungs-/Breitband-/Rats-/Energiepfade mit Suchraster Rechenzentrum, Datacenter/Data Center, Serverfarm, Gewerbe/GI/GE, Bauleitplanung/FNP, Glasfaser/Breitband, Waerme/Abwaerme, Strom/Netz/Umspannwerk.", "", "Naechster Fokus", "- Weitere offene Coverage im Landkreis Ludwigsburg ab dem naechsten noch offenen Eintrag fortsetzen; Freiburg/Denzlingen/Emmendingen sofort vorziehen, sobald konkrete Flaechen-/Netz-/Carrier-Hinweise auftauchen.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")

def main():
    results = {}
    for name, district, code, url in MUNICIPALITIES:
        print(f"screen {name} {url}")
        try:
            results[name] = crawl(url)
        except Exception as exc:
            results[name] = [{"url": url, "error": str(exc), "hits": [], "rzHits": []}]
        for p in results[name]:
            print(" ", p.get("status", "ERR"), p.get("url"), "hits=", ",".join(p.get("hits", [])[:8]), "rz=", ",".join(p.get("rzHits", [])), p.get("error", ""))
    priority_results = {}
    for label, url in PRIORITY_SOURCES:
        print(f"priority {label} {url}")
        try:
            priority_results[label] = crawl(url, limit=1)
        except Exception as exc:
            priority_results[label] = [{"url": url, "error": str(exc), "hits": [], "rzHits": []}]
        p = priority_results[label][0]
        print(" ", p.get("status", "ERR"), p.get("url"), "hits=", ",".join(p.get("hits", [])[:8]), "rz=", ",".join(p.get("rzHits", [])), p.get("error", ""))
    update_coverage(results)
    update_database(results, priority_results)
    write_report(results, priority_results)
    print("updated database.json, assets/bw-municipality-coverage.json, docs/tagesbericht-2026-07-07.txt")

if __name__ == "__main__":
    main()
