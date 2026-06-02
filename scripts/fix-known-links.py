from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "index.html"
text = path.read_text(encoding="utf-8")

replacements = {
    "https://azure.microsoft.com/en-us//en-us/": "https://azure.microsoft.com/en-us/",
    "https://www.nrel.gov/computational-science/data-center-cooling-system.html": "https://www.nrel.gov/computational-science/data-center-cooling-system",
    "https://www.nrel.gov/computational-science/data-center-cooling-system": "https://www.nlr.gov/computational-science/data-center-cooling-system",
    "https://www.parker.com/content/dam/parker/fcg/group/data-centers/Form-5-593-Data-Center-Cooling-Diagram.pdf": "https://www.parker.com/content/dam/Parker-com/Literature/Sporlan/Sporlan-pdf-files/Sporlan-pdf-Miscellanous/Form-5-593-Data-Center-Cooling-Piping-Diagram.pdf",
    "https://rp-darmstadt.hessen.de/sites/rp-darmstadt.hessen.de/files/2026-04/besch_ie-rl-rz_heusenstamm_edgeconnex_2026_02_16.pdf": "https://rp-darmstadt.hessen.de/veroeffentlichungen-und-digitales/oeffentliche-bekanntmachungen/umweltrecht/18032026-edgeconnex-heusenstamm-gmbh-errichtung-und-betrieb-von-42-notstromdieselmotoranlagen",
    "https://www.planegg.de/rathaus-and-buergerservice/bauen-planen/bauleitplanung/bebauungsplaene/aktuelle-bekanntmachungen/bebauungsplan-nr-83": "https://www.biochem.mpg.de/2025-12-04-data-center",
    "https://azure.microsoft.com\":": "https://azure.microsoft.com/en-us/\":",
}

for old, new in replacements.items():
    text = text.replace(old, new)

# Preserve the direct current RP PDF as an additional document link where Heusenstamm is mentioned.
rp_page = "https://rp-darmstadt.hessen.de/veroeffentlichungen-und-digitales/oeffentliche-bekanntmachungen/umweltrecht/18032026-edgeconnex-heusenstamm-gmbh-errichtung-und-betrieb-von-42-notstromdieselmotoranlagen"
rp_pdf = "https://rp-darmstadt.hessen.de/sites/rp-darmstadt.hessen.de/files/2026-03/zoeb_oeb_rz_heusenstamm_2026_05_13.pdf"
text = text.replace(f"\\nRP PDF Bekanntmachung: {rp_pdf}", "")

planegg_page = "https://www.biochem.mpg.de/2025-12-04-data-center"
planegg_extra = "https://www.biochem.mpg.de/8714065/Bauausschuss"
if planegg_extra not in text:
    text = text.replace(planegg_page, f"{planegg_page}\\nMPG Bauausschuss/Planungsstart: {planegg_extra}", 1)

path.write_text(text, encoding="utf-8")
print("known broken links replaced")
