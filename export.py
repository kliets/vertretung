"""Stundenkarte als druckfertiges HTML (im Browser öffnen → Drucken → als PDF speichern)."""
import html

import markdown as md

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "Source Sans 3", "Segoe UI", Arial, sans-serif; font-size: 11pt;
       line-height: 1.5; color: #1d2a33; max-width: 760px; margin: 2rem auto; padding: 0 1rem; }
h1 { font-size: 19pt; margin: 0 0 .6rem; color: #0f4c5c; border-bottom: 3px solid #0f4c5c; padding-bottom: .3rem; }
h2 { font-size: 13.5pt; margin: 1.4rem 0 .4rem; color: #0f4c5c; }
table { border-collapse: collapse; width: 100%; margin: .5rem 0; }
th, td { border: 1px solid #b9c7cf; padding: .35rem .5rem; text-align: left; vertical-align: top; }
th { background: #e7eff2; }
a { color: #0f4c5c; word-break: break-all; }
.seitenumbruch { page-break-before: always; }
.fuss { margin-top: 2rem; font-size: 9pt; color: #5b6b75; border-top: 1px solid #b9c7cf; padding-top: .4rem; }
@media print { body { margin: 0; max-width: none; } .keindruck { display: none; } }
"""


def als_html(markdown_text: str, titel: str) -> str:
    rumpf = md.markdown(markdown_text, extensions=["tables", "sane_lists"])
    # Aufgaben und Lösungen jeweils auf eine neue Seite (Aufgabenblatt kann separat kopiert werden)
    for kopf in ("<h2>Aufgaben", "<h2>Lösungen"):
        rumpf = rumpf.replace(kopf, f'<div class="seitenumbruch"></div>{kopf}', 1)
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>{html.escape(titel)}</title><style>{CSS}</style></head>
<body>
<p class="keindruck"><button onclick="window.print()">Drucken oder als PDF speichern</button></p>
{rumpf}
<p class="fuss">Erstellt mit dem Vertretungsgenerator (KI-gestützt). Inhalte vor dem Einsatz kurz prüfen.</p>
</body></html>"""
