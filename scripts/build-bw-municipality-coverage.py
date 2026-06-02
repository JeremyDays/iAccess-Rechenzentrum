import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://de.wikipedia.org/wiki/Liste_der_Gemeinden_in_Baden-W%C3%BCrttemberg_nach_Amtlichen_Gemeindeschl%C3%BCsseln"


def norm(value):
    value = (value or "").replace("–", "-").replace(" / ", "/").strip()
    value = re.sub(r",.*$", "", value)
    value = re.sub(r"\s+-\s+.*$", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


def load_municipalities():
    html = requests.get(
        SOURCE_URL,
        headers={"User-Agent": "iAccess research bot contact hornick@iaccess.de"},
        timeout=30,
    ).text
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    district = ""
    for element in soup.select("h4, li"):
        text = element.get_text(" ", strip=True)
        if element.name == "h4":
            match = re.search(r"Landkreis\s+(.+?)\s*\(|Stadtkreis\s+(.+?)\s*\(", text)
            if match:
                district = (match.group(1) or match.group(2)).strip()
            continue

        match = re.match(r"^(\d{3})\s+(.+)$", text)
        if not match:
            continue
        link = element.find("a")
        raw_name = (link.get_text(" ", strip=True) if link else match.group(2)).strip()
        name = re.sub(r"\s*,.*$", "", raw_name).strip()
        rows.append({"name": name, "district": district, "code": match.group(1), "key": norm(name)})
    return rows


def add_known(known, keys, raw_name, kind, evidence, source="", notes=""):
    key = norm(raw_name)
    if key not in keys:
        for candidate in keys:
            if key.startswith(candidate + "-") or key.startswith(candidate + "/"):
                key = candidate
                break
    if key not in keys:
        return
    known.setdefault(key, {"evidence": [], "sources": [], "notes": []})
    known[key]["evidence"].append(f"{kind}: {evidence}")
    if source:
        known[key]["sources"].append(source)
    if notes:
        known[key]["notes"].append(notes)


def main():
    db = json.loads((ROOT / "database.json").read_text(encoding="utf-8"))
    municipalities = load_municipalities()
    keys = {row["key"] for row in municipalities}
    known = {}

    for site in db.get("sites", []):
        for part in re.split(r"\s*/\s*|\s+und\s+", site.get("city", "")):
            if part.strip():
                add_known(
                    known,
                    keys,
                    part.strip(),
                    "Standortliste",
                    site.get("name", ""),
                    site.get("link", ""),
                    site.get("tags", ""),
                )

    for plan in db.get("zoningPlans", []):
        if str(plan.get("state", "")).startswith("Baden"):
            add_known(
                known,
                keys,
                plan.get("municipality", ""),
                "Bebauungsplan",
                plan.get("planName", ""),
                plan.get("documents", ""),
                plan.get("notes", ""),
            )

    priority = {
        norm(name)
        for name in [
            "Denzlingen",
            "Freiburg im Breisgau",
            "Vörstetten",
            "Gundelfingen",
            "Emmendingen",
            "Waldkirch",
            "March",
            "Umkirch",
            "Bötzingen",
            "Gottenheim",
            "Teningen",
            "Sexau",
            "Reute",
            "Glottertal",
            "Kirchzarten",
            "Breisach am Rhein",
            "Bad Krozingen",
            "Lahr/Schwarzwald",
            "Appenweier",
            "Offenburg",
            "Kehl",
            "Karlsruhe",
            "Stuttgart",
            "Mannheim",
            "Heidelberg",
            "Ulm",
            "Tübingen",
        ]
    }

    items = []
    for municipality in municipalities:
        evidence = known.get(municipality["key"])
        if evidence:
            status = "RZ gefunden"
            next_action = "Detailquellen, Betreiberangaben, Strom-/Glasfaser- und Bauleitplanungsdaten vertiefen."
        else:
            status = "noch nicht systematisch geprüft"
            next_action = "Gemeindeseite, Ratsinformationssystem, Bebauungspläne/FNP, Gewerbeflächen, Netzbetreiber und Glasfaser prüfen."
        if municipality["key"] in priority:
            next_action = f"Priorität Raum Freiburg/BW: {next_action}"
        items.append(
            {
                "name": municipality["name"],
                "district": municipality["district"],
                "code": municipality["code"],
                "status": status,
                "priority": "hoch" if municipality["key"] in priority else "normal",
                "evidence": "; ".join(dict.fromkeys(evidence["evidence"])) if evidence else "",
                "source": "; ".join(dict.fromkeys(evidence["sources"])) if evidence else "",
                "notes": "; ".join(dict.fromkeys(evidence["notes"])) if evidence else "",
                "nextAction": next_action,
            }
        )

    output = {
        "generatedAt": "2026-06-02",
        "source": "Wikipedia: Liste der Gemeinden in Baden-Württemberg nach Amtlichen Gemeindeschlüsseln; Abgleich mit iAccess database.json",
        "total": len(items),
        "found": sum(1 for row in items if row["status"] == "RZ gefunden"),
        "notSystematicallyChecked": sum(1 for row in items if row["status"] != "RZ gefunden"),
        "items": items,
    }
    target = ROOT / "assets" / "bw-municipality-coverage.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: output[k] for k in ["total", "found", "notSystematicallyChecked"]}, ensure_ascii=False, indent=2))
    print("\n".join(row["name"] for row in items if row["status"] == "RZ gefunden"))


if __name__ == "__main__":
    main()
