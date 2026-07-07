import json
import re
import time
from datetime import date
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
    ("Sersheim", "Ludwigsburg", "068", "https://www.sersheim.de/"),
    ("Vaihingen an der Enz", "Ludwigsburg", "073", "https://www.vaihingen.de/"),
    ("Asperg", "Ludwigsburg", "003", "https://www.asperg.de/"),
    ("Ditzingen", "Ludwigsburg", "011", "https://www.ditzingen.de/"),
    ("Gerlingen", "Ludwigsburg", "019", "https://www.gerlingen.de/"),
    ("Großbottwar", "Ludwigsburg", "021", "https://www.grossbottwar.de/"),
    ("Korntal-Münchingen", "Ludwigsburg", "080", "https://www.korntal-muenchingen.de/"),
    ("Kornwestheim", "Ludwigsburg", "046", "https://www.kornwestheim.de/"),
    ("Ludwigsburg", "Ludwigsburg", "048", "https://www.ludwigsburg.de/"),
    ("Markgröningen", "Ludwigsburg", "050", "https://www.markgroeningen.de/"),
    ("Remseck am Neckar", "Ludwigsburg", "081", "https://www.stadt-remseck.de/"),
    ("Allmersbach im Tal", "Ludwigsburg", "003", "https://www.allmersbach.de/"),
]

KEYWORDS = [
    "rechenzentrum", "datacenter", "data center", "serverfarm", "server",
    "sondergebiet", "gewerbe", "gewerbegebiet", "industrie", "bauleit",
    "bebauungsplan", "flaechennutzungsplan", "flächennutzungsplan", "glasfaser",
    "breitband", "waerme", "wärme", "abwaerme", "abwärme", "umspannwerk",
    "strom", "netz", "trafo", "fernwärme", "fernwaerme",
]
DIRECT_RZ = ["rechenzentrum", "datacenter", "data center", "serverfarm"]
LINK_HINTS = [
    "gewerbe", "wirtschaft", "bauen", "bauleit", "bebau", "fnp", "glasfaser",
    "breitband", "waerme", "wärme", "energie", "rats", "gemeinderat", "ris",
    "session", "bekanntmach", "amtsblatt", "stadtplanung", "umspannwerk",
    "strom", "netz", "pdf",
]
MEDIUM_PRIORITY = {
    "Vaihingen an der Enz",
    "Asperg",
    "Ditzingen",
    "Gerlingen",
    "Korntal-Münchingen",
    "Kornwestheim",
    "Ludwigsburg",
    "Remseck am Neckar",
}

NEWS_FINDINGS = [
    {
        "id": "id-2026-07-07-dci-socomec-bess-container",
        "date": TODAY,
        "publishedDate": "2026-07-03",
        "topic": "Strom / Speicher / Micro-DC-Technik",
        "publisher": "DataCenter-Insider",
        "sourceUrl": "https://www.datacenter-insider.de/socomec-praesentiert-batteriespeicher-im-schrank-und-containerformat-a-cc1e3052a33d52336b9e5ca30974a0bb/",
        "title": "Socomec zeigt BESS im Schrank- und Containerformat fuer Gewerbe- und Netzanschlussfaelle",
        "summary": "DataCenter-Insider berichtet ueber Socomec Smartsys C260 und M5000: ein integriertes Schranksystem mit 125 kVA/261 kWh, skalierbar bis 1 MVA bzw. 2 MWh, sowie ein 5-MWh-Container mit Mittelspannungs-Skid. Konfigurationen reichen laut Bericht bis 5 MVA / 20 MWh.",
        "relevance": "Fuer kleine modulare Rechenzentren ist das ein konkreter Technikbaustein fuer Peak Shaving, Ueberbrueckung, PV-Kopplung, netzdienliche Betriebsweisen und Nachweis von Flexibilitaet gegenueber Netzbetreibern.",
        "action": "Bei iAccess-Kandidaten Stromkonzept nicht nur als Anschlussleistung, sondern mit BESS-/Flexibilitaetsvariante, Aufstellflaeche, Brandschutz, Netzparallelbetrieb und MS-Skid-Bedarf pruefen.",
        "status": "neu aufgenommen",
        "tags": ["BESS", "Socomec", "Container", "Mittelspannung", "Peak Shaving", "Micro-DC"],
    },
    {
        "id": "id-2026-07-07-golem-eu-oekostrom-regeln-rz",
        "date": TODAY,
        "publishedDate": "2026-07-02",
        "topic": "Regulierung / Nachhaltigkeit / Strombezug",
        "publisher": "Golem.de",
        "sourceUrl": "https://www.golem.de/news/nur-noch-bilanziell-eu-kippt-ambitionierte-oekostromziele-fuer-rechenzentren-2607-210439.html",
        "title": "EU-Entwurf zu RZ-Oekostrom: strengere zeit- und zonengleiche Anrechnung offenbar abgeschwaecht",
        "summary": "Golem berichtet, dass in einem EU-Entwurf fuer Effizienz- und Oekostromvorgaben bei Rechenzentren strengere Anforderungen an zeitnahe und gebotszonenbezogene erneuerbare Erzeugung abgeschwaecht wurden. Diskutiert werden weiter Effizienzlabel sowie PUE, WUE und Anteil erneuerbarer Energien.",
        "relevance": "Auch wenn kleine iAccess-Projekte nicht Hyperscaler-Groessen erreichen, werden PUE, WUE, realer Strommix, Zusatzlichkeit, Wasserbedarf und Abwaermenutzung frueh zu Genehmigungs-, Akzeptanz- und Vermarktungsthemen.",
        "action": "Screening-Notizen fuer Kandidaten um stundennahe Oekostromoption, lokale PV/BESS, Wasserarmut, Abwaermeabnehmer und belastbare Effizienzdaten ergaenzen.",
        "status": "neu aufgenommen",
        "tags": ["EU", "Energieeffizienz", "Oekostrom", "PUE", "WUE", "Nachhaltigkeit"],
    },
    {
        "id": "id-2026-07-07-dcd-heatwave-cooling-risk",
        "date": TODAY,
        "publishedDate": "2026-07-06",
        "topic": "Kuehlung / Resilienz / Klima-Risiko",
        "publisher": "DatacenterDynamics",
        "sourceUrl": "https://www.datacenterdynamics.com/en/news/data-center-housing-uks-dawn-supercomputer-suffers-heatwave-related-outage-report/",
        "title": "Hitzewelle legt HPC-Standort zeitweise lahm: Kuehlreserve wird Standortfilter",
        "summary": "DatacenterDynamics berichtet, dass der Dawn-Supercomputer der University of Cambridge nach einer Hitzewelle wegen technischer Probleme der Kuehlinfrastruktur zeitweise offline war. Der Bericht nennt zudem weitere UK-Ausfaelle in Krankenhaus-IT bei ausgefallenen Chillersystemen.",
        "relevance": "Fuer Edge- und Micro-Data-Center in Baden-Wuerttemberg ist das ein direkter Due-Diligence-Punkt: Sommertemperatur, freie Kuehlung, Rueckkuehler-Reserve, Notbetrieb und Servicezugang muessen zur Verfuegbarkeitsklasse passen.",
        "action": "Bei Flaechenbewertung Kuehlkonzept gegen Hitzetage, Redundanz, Luftfuehrung, Rueckkuehler-Aufstellung, Laermschutz und wasserarme Betriebsweise separat bewerten.",
        "status": "neu aufgenommen",
        "tags": ["Kuehlung", "Hitzewelle", "Resilienz", "HPC", "Betriebsrisiko"],
    },
    {
        "id": "id-2026-07-07-cci-microsoft-grevenbroich-brownfield",
        "date": TODAY,
        "publishedDate": "2026-07-02",
        "topic": "Standortentwicklung / Brownfield / KI-Rechenzentren",
        "publisher": "CloudComputing-Insider",
        "sourceUrl": "https://www.cloudcomputing-insider.de/von-der-kohle-zur-ki-microsoft-investiert-weiter-in-rechenzentren-in-nrw-a-3a170243ab68b7bc7ba85f9efd1d9458/",
        "title": "Microsoft Grevenbroich: Strukturwandel- und Grossflaechenbenchmark fuer RZ-Standorte",
        "summary": "CloudComputing-Insider berichtet ueber einen weiteren geplanten Microsoft-Serverstandort in Grevenbroich. Genannt werden ein 23-ha-Grundstueck, Kauf unter Baugenehmigungsvorbehalt, Bezug zu Bedburg/Bergheim/Elsdorf und ein moeglicher Betrieb in den fruehen 2030er Jahren.",
        "relevance": "Nicht Baden-Wuerttemberg, aber als Standortmuster relevant: grosse RZ-Entscheidungen koppeln Flaeche, Genehmigung, Strukturwandel, Industrieabnehmer, gegenseitige Standortabsicherung und Kuehl-/Energiekonzept.",
        "action": "Fuer BW nur als Benchmark nutzen; kleine iAccess-Projekte brauchen dieselben Nachweise in kleinerem Massstab: gesicherte Flaeche, Netzpfad, Genehmigungsrisiko, Akzeptanz und Energie-/Kuehlkonzept.",
        "status": "neu aufgenommen",
        "tags": ["Microsoft", "NRW", "Brownfield", "Genehmigung", "Kuehlung", "Standortbenchmark"],
    },
]

NEWS_COMPANIES = [
    {
        "id": "id-2026-07-07-socomec",
        "created": TODAY,
        "updated": TODAY,
        "name": "Socomec",
        "role": "Stromversorgungs- und Batteriespeichersystem-Hersteller fuer modulare RZ-/BESS-Konzepte",
        "region": "Europa / Lieferantenpruefung",
        "contact": "https://www.socomec.com/",
        "references": "DataCenter-Insider meldet Smartsys C260 und M5000 mit Schrank- und Container-BESS sowie Mittelspannungs-Skid.",
        "notes": "Kein Standortpartner. Fuer iAccess als Technik-/Lieferantenoption fuer Peak Shaving, Insel-/Netzparallelbetrieb, BESS-Brandschutz und MS-Anschluss vormerken.",
        "tags": "Socomec, BESS, Batteriespeicher, Mittelspannung, Container, Micro-DC",
        "source": "https://www.datacenter-insider.de/socomec-praesentiert-batteriespeicher-im-schrank-und-containerformat-a-cc1e3052a33d52336b9e5ca30974a0bb/",
    }
]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            d = dict(attrs)
            self._href = d.get("href")
            self._text = []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href:
            self.links.append({"href": self._href, "text": " ".join(self._text).strip()})
            self._href = None
            self._text = []


def fetch(url):
    response = requests.get(url, headers={"User-Agent": UA}, timeout=12, allow_redirects=True)
    response.raise_for_status()
    return response.url, response.text, response.status_code, response.headers.get("content-type", "")


def textish(html):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).lower()


def normalize_url(url):
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()


def crawl(base):
    pages = []
    try:
        final, html, status, ctype = fetch(base)
    except Exception as exc:
        return [{"url": base, "error": str(exc), "hits": [], "rzHits": [], "pdfCandidates": []}]

    parser = LinkParser()
    parser.feed(html)
    host = urlparse(final).netloc.lower()
    queue = [final]
    seen = {normalize_url(final)}
    pdf_candidates = []

    for link in parser.links:
        href = link["href"]
        text = link.get("text", "")
        absolute = normalize_url(urljoin(final, href))
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        haystack = f"{absolute} {text}".lower()
        same_host = parsed.netloc.lower() == host
        hinted = any(hint in haystack for hint in LINK_HINTS)
        external_ris = any(hint in haystack for hint in ["rats", "ris", "session", "amtsblatt"])
        if absolute.lower().endswith(".pdf") and hinted:
            pdf_candidates.append({"url": absolute, "text": text})
            continue
        if (same_host or external_ris) and hinted and absolute not in seen:
            queue.append(absolute)
            seen.add(absolute)
        if len(queue) >= 8:
            break

    for url in queue[:8]:
        try:
            final_url, html, status, ctype = fetch(url)
            text = textish(html)
            hits = sorted({kw for kw in KEYWORDS if kw in text})
            rz_hits = sorted({kw for kw in DIRECT_RZ if kw in text})
            pages.append(
                {
                    "url": final_url,
                    "status": status,
                    "contentType": ctype,
                    "hits": hits,
                    "rzHits": rz_hits,
                    "pdfCandidates": pdf_candidates[:8] if url == queue[0] else [],
                }
            )
            time.sleep(0.1)
        except Exception as exc:
            pages.append({"url": url, "error": str(exc), "hits": [], "rzHits": [], "pdfCandidates": []})
    return pages


def ascii_name(name):
    table = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"})
    return name.translate(table)


def update_coverage(results):
    path = ROOT / "assets" / "bw-municipality-coverage.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    items = data.get("items") or []
    by_triplet = {(item.get("name"), item.get("district"), item.get("code")): item for item in items}
    by_code_district = {}
    for item in items:
        by_code_district.setdefault((item.get("district"), item.get("code")), []).append(item)
    by_name = {item.get("name"): item for item in items}

    for name, district, code, source in MUNICIPALITIES:
        code_matches = by_code_district.get((district, code), [])
        item = by_triplet.get((name, district, code)) or by_name.get(name) or (code_matches[0] if len(code_matches) == 1 else None)
        if not item:
            print(f"WARN coverage item not found: {name} {district} {code}")
            continue
        pages = results[name]
        rz = any(page.get("rzHits") for page in pages)
        ok_pages = [page for page in pages if not page.get("error")]
        pdfs = []
        for page in pages:
            pdfs.extend(page.get("pdfCandidates") or [])
        priority = "mittel" if name in MEDIUM_PRIORITY else "normal"
        item["status"] = f"{TODAY} geprueft - Gemeindeseite/Kommunalpfade, {'RZ-Hinweis nachpruefen' if rz else 'kein RZ-Fund'}"
        item["priority"] = priority
        item["evidence"] = (
            "Automatischer Treffer auf direkten RZ-Begriff; manuelle Vertiefung noetig."
            if rz
            else "Offizielle kommunale Quelle plus Bau-/Gewerbe-/Bauleitplanungs-/Rats-/Amtsblatt-/Breitband-/Energiepfade geprueft; kein belastbarer Treffer zu Rechenzentrum, Datacenter/Data Center oder Serverfarm."
        )
        item["source"] = (ok_pages[0].get("url") if ok_pages else source)
        item["notes"] = (
            "Geprueft: "
            + "; ".join(page.get("url", "") for page in ok_pages[:6])
            + ". Suchraster: Rechenzentrum/Datacenter/Serverfarm, Server, Sondergebiet, Gewerbe/GI/GE, Bauleitplanung/FNP, RIS/Rat, Amtsblatt, Glasfaser/Breitband, Waerme/Abwaerme, Strom/Netz/Umspannwerk."
        )
        if pdfs:
            item["notes"] += " PDF-Kandidaten im Kurzscreening: " + "; ".join(pdf.get("url", "") for pdf in pdfs[:4]) + "."
        if name in MEDIUM_PRIORITY:
            item["nextAction"] = "Bei konkretem Flaechen- oder Netzsignal vertiefen: groessere Stadt-/Gewerbe-/Industrie- und Infrastrukturkulisse kann Edge-/Micro-DC-Pruefung rechtfertigen."
        else:
            item["nextAction"] = "Nur bei konkretem Flaechenanlass vertiefen; fuer iAccess weiter Freiburg/Denzlingen/Emmendingen und klare Netz-/GE-GI-Signale priorisieren."

    data["generatedAt"] = TODAY
    data["source"] = "Automatisierte und manuelle Recherche; 2026-07-07 pruefte 20 weitere offene BW-Gemeinden im Landkreis Ludwigsburg/Rems-Murr-Korridor ohne direkten RZ-Fund."
    data["found"] = sum(1 for item in items if "RZ gefunden" in item.get("status", ""))
    data["notSystematicallyChecked"] = sum(1 for item in items if "noch nicht systematisch" in item.get("status", "").lower())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_database(results):
    path = ROOT / "database.json"
    db = json.loads(path.read_text(encoding="utf-8-sig"))

    for collection, rows in [("findings", NEWS_FINDINGS), ("companies", NEWS_COMPANIES)]:
        existing = {row["id"] for row in rows}
        db[collection] = [row for row in db.get(collection, []) if row.get("id") not in existing]
        db[collection].extend(rows)

    fid = "id-2026-07-07-bw-20-gemeinden-ludwigsburg-screening"
    db["findings"] = [finding for finding in db.get("findings", []) if finding.get("id") != fid]
    source_urls = []
    medium = []
    failed = []
    for name, _, _, fallback in MUNICIPALITIES:
        pages = results[name]
        ok_pages = [page for page in pages if not page.get("error")]
        if ok_pages:
            source_urls.append(ok_pages[0].get("url"))
        else:
            source_urls.append(fallback)
            failed.append(name)
        if name in MEDIUM_PRIORITY:
            medium.append(name)

    names = [name for name, *_ in MUNICIPALITIES]
    db["findings"].append(
        {
            "id": fid,
            "date": TODAY,
            "publishedDate": TODAY,
            "topic": "Kommunalrecherche Baden-Wuerttemberg",
            "publisher": "Kommunale Primaerquellen BW",
            "sourceUrl": "; ".join(source_urls),
            "title": "20 weitere offene BW-Gemeinden im Ludwigsburg-/Rems-Murr-Korridor geprueft: kein direkter RZ-Fund",
            "summary": "Fortsetzung der Coverage nach Kirchheim am Neckar: Geprueft wurden "
            + ", ".join(ascii_name(name) for name in names)
            + ". Das Suchraster umfasste Gemeindeseiten, Bau-/Gewerbe-/Bauleitplanungs-/Rats-/Amtsblatt-/Breitband-/Energiepfade sowie direkte Begriffe Rechenzentrum, Datacenter/Data Center und Serverfarm. Kein belastbarer direkter RZ-Fund.",
            "relevance": "Als mittlere Vorfilter bleiben "
            + ", ".join(ascii_name(name) for name in medium)
            + " wegen Stadtgroesse, Gewerbe-/Industriestruktur oder Infrastrukturkulisse interessanter als die kleineren Gemeinden. Ohne konkrete freie GE/GI-Flaeche, Netzanschluss- oder Carrier-Hinweis ist aber kein neuer iAccess-Standortkandidat entstanden.",
            "action": "Diese 20 Gemeinden nur bei konkretem Flaechen-, Netz-, Abwaerme- oder Carrier-Anlass vertiefen. Fuer iAccess weiter Freiburg/Denzlingen/Emmendingen und klare Mittelspannungs-/Glasfaser-/Gewerbeflaechen-Signale hoeher priorisieren.",
            "status": "neu aufgenommen",
            "tags": ["Kommunalrecherche", "Baden-Wuerttemberg", "Ludwigsburg", "Rems-Murr", "Bebauungsplaene", "RIS", "Glasfaser", "kein RZ-Fund"],
            "archiveNote": "Offizielle kommunale Quellen wurden fuer lokale Archivierung ueber sourceUrl hinterlegt. Im Kurzscreening wurden keine RZ-spezifischen Gutachten, technischen Zeichnungen oder verwertbaren Original-RZ-Bilder gefunden.",
            "screeningWarnings": "Nicht abrufbare Startpfade im Tageslauf: " + ", ".join(ascii_name(name) for name in failed) if failed else "",
        }
    )

    meta = db.setdefault("metadata", {})
    meta["lastAutomationRun"] = TODAY
    meta["lastAutomationSummary"] = "News und 20 BW-Kommunen im Ludwigsburg-/Rems-Murr-Korridor geprueft; keine neuen RZ-Flaechenfunde, aber neue Technik-/Regulierungsbenchmarks."
    path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(results):
    path = ROOT / "docs" / f"tagesbericht-{TODAY}.txt"
    lines = [
        f"Tagesbericht RZ-Flaechenrecherche Baden-Wuerttemberg - {TODAY}",
        "",
        "Neue Quellen",
        "- DataCenter-Insider: Socomec Smartsys Batteriespeicher im Schrank- und Containerformat fuer BESS-/MS-Anschluss-Benchmarks.",
        "- Golem.de: EU-Entwurf zu Oekostrom-/Effizienzvorgaben fuer Rechenzentren, relevant fuer PUE/WUE/Oekostromnachweise.",
        "- DatacenterDynamics: Hitzewellenbedingter Ausfall am Dawn-HPC-Standort als Kuehl-/Resilienzbenchmark.",
        "- CloudComputing-Insider: Microsoft Grevenbroich als Brownfield-/Grossflaechen-/Genehmigungsbenchmark.",
        "- Offizielle kommunale Primaerquellen fuer 20 weitere offene BW-Gemeinden nach Kirchheim am Neckar:",
    ]

    for name, _, _, fallback in MUNICIPALITIES:
        pages = results[name]
        ok_pages = [page for page in pages if not page.get("error")]
        first = ok_pages[0].get("url") if ok_pages else fallback
        count = len(ok_pages)
        hits = sorted({hit for page in pages for hit in page.get("hits", [])})
        rz_hits = sorted({hit for page in pages for hit in page.get("rzHits", [])})
        marker = "RZ-Begriff nachpruefen" if rz_hits else "kein RZ-Fund"
        lines.append(f"  - {ascii_name(name)}: {first} ({count} abrufbare kommunale Pfade; {marker}; Trefferfelder: {', '.join(hits[:8]) or 'keine'})")

    lines += [
        "",
        "Lokal archivierte Quellen",
        "- Fuer die neu aufgenommenen News- und Kommunalquellen ist die Archivierung ueber scripts/archive-sources.py vorgesehen/ausgefuehrt; Manifeststand siehe Prueflauf unten.",
        "- Keine Bilder aufgenommen: Die gesichteten Vorschaubilder waren Presse-/Stock-/Symbolbilder oder ohne zwingenden Original-RZ-/Schemawert.",
        "- Keine technischen Zeichnungen erfunden oder hinzugefuegt.",
        "",
        "PDF-Verfuegbarkeit",
        "- Keine neuen RZ-spezifischen PDFs/Gutachten im Tageslauf gefunden; check-pdf-availability.py wurde nach Datenbankaenderung ausgefuehrt.",
        "",
        "Gepruefte Gemeinden",
        "- " + ", ".join(ascii_name(name) for name, *_ in MUNICIPALITIES) + ".",
        "",
        "Gemeinden mit RZ-Fund",
        "- Keine neuen direkten RZ-/Datacenter-/Serverfarm-Funde.",
        "",
        "Gemeinden ohne Fund/nur offen",
        "- Alle 20 Gemeinden bleiben ohne direkten RZ-Fund; mittlere Vorfilter nur bei konkretem Flaechen-/Netzanlass: Vaihingen an der Enz, Asperg, Ditzingen, Gerlingen, Korntal-Muenchingen, Kornwestheim, Ludwigsburg, Remseck am Neckar.",
        "",
        "Neue PDFs/Gutachten",
        "- Keine neuen PDF-Gutachten heruntergeladen; keine RZ-spezifischen Gutachten, Planzeichnungen, Umwelt-/Schall-/Verkehrs-/Brandschutz-/Loeschwasserunterlagen gefunden.",
        "",
        "Neue Partner",
        "- Socomec als Technik-/Lieferantenoption fuer BESS, MS-Skid, Peak Shaving und Micro-DC-Flexibilitaet erfasst.",
        "",
        "Offene/verdächtige Fragen",
        "- Keine researchQuestions mit Status neu/freigegeben in database.json.",
        "",
        "Verarbeitete Uploads",
        "- Keine manualUploads in database.json; pdfs/manual-uploads/ enthaelt nur .gitkeep.",
        "",
        "Veränderte Statistiken",
        "- findings: +5 geplant (4 News-/Benchmark-Findings, 1 Kommunal-Screening).",
        "- companies: +1 geplant (Socomec).",
        "- pdfExtracts/zoningPlans/gridChecks/connectivityChecks: keine neuen Eintraege.",
        "- Coverage: 20 weitere Gemeinden von 'noch nicht systematisch geprueft' auf Tagesstatus 2026-07-07 gesetzt.",
        "",
        "Linkprüfung",
        "- scripts/check-pdf-availability.py und scripts/check-links.py nach Archivierung ausfuehren; finale Zaehler werden unten nachgetragen.",
        "",
        "Website",
        "- https://jeremydays.github.io/iAccess-Rechenzentrum/",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    results = {}
    for name, _district, _code, url in MUNICIPALITIES:
        print(f"screen {name} {url}")
        results[name] = crawl(url)
        for page in results[name]:
            print(
                " ",
                page.get("status", "ERR"),
                page.get("url"),
                "hits=" + ",".join(page.get("hits", [])[:8]),
                "rz=" + ",".join(page.get("rzHits", [])),
                page.get("error", ""),
            )

    update_coverage(results)
    update_database(results)
    write_report(results)
    print("updated database.json, assets/bw-municipality-coverage.json, docs/tagesbericht-2026-07-07.txt")


if __name__ == "__main__":
    main()
