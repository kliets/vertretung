"""KI-Anbindung: Prompt bauen, Claude mit Websuche aufrufen, Links prüfen."""
import re

import anthropic

SYSTEM = """Du bist eine erfahrene Lehrkraft und Fachdidaktikerin an Gymnasien in Schleswig-Holstein.
Du planst Vertretungsstunden, die eine andere Lehrkraft ohne Vorbereitung sofort durchführen kann.

Grundsätze:
1. Nur Üben, Wiederholen und Vertiefen von Inhalten, die die Lerngruppe mit hoher Wahrscheinlichkeit schon kennt. Keine Neueinführung. Bei Unsicherheit wähle ein etwas früheres Thema aus dem Schuljahr.
2. Ist die Vertretungslehrkraft fachfremd, muss alles ohne Fachwissen funktionieren: klare Anweisungen, vollständige Lösungen, keine Experimente, kein Fachraum.
3. Die analoge Variante (Papier, Tafel, Heft) ist immer vollständig und kommt ohne Geräte aus. Digitale Angebote sind nur eine optionale Ergänzung.
4. Fachliche Korrektheit hat Vorrang. Rechne jede Aufgabe selbst nach, bevor du die Lösung angibst.
5. Nutze die Websuche, um geeignete, frei zugängliche Materialien zu finden, bevorzugt von seriösen Bildungsanbietern (z. B. Landesbildungsserver, IQSH, serlo.org, LEIFIphysik, PhET, GeoGebra, planet-schule, Inf-Schule, CS Unplugged, Bundeszentrale für politische Bildung). Gib ausschließlich URLs an, die wörtlich in deinen Suchergebnissen vorkamen. Erfinde niemals Links.
6. Formuliere Aufgaben selbst. Kopiere keine geschützten Texte aus Quellen.
7. Sei transparent: Begründe die Themenwahl und benenne, wie sicher die Einordnung ist.
8. Schreibe Formeln ohne LaTeX, in einfacher Schreibweise mit Unicode (z. B. x², √2, 3·10⁸ m/s, Δt).
9. Keine personenbezogenen Daten, keine Namen von Schülerinnen und Schülern.

Antworte ausschließlich mit der Stundenkarte in Markdown, exakt in dieser Gliederung:

# Vertretungsstunde: <Thema>
| | |
|---|---|
| Fach | … |
| Jahrgang | … |
| Datum | … |
| Dauer | … |
| Geeignet für fachfremde Vertretung | ja/nein |
| Material | … |

## Einordnung
2–4 Sätze: Warum dieses Thema, worauf stützt sich die Schätzung, wie sicher ist sie.

## Hinweise für die Vertretungslehrkraft
Kurze, konkrete Punkte.

## Ablauf
Tabelle mit Spalten: Zeit | Phase | Was passiert

## Aufgaben für die Schülerinnen und Schüler
Vollständiges Aufgabenblatt zum Vorlesen oder Abschreiben, ohne Geräte lösbar. Gestuft (Basis, Standard, Knobel).

## Digitale Ergänzung (optional)
Nur falls Geräte vorhanden. Konkrete Links mit einem Satz, was dort zu tun ist.

## Lösungen
Vollständige Lösungen zu allen Aufgaben.

## Quellen
Liste der verwendeten Quellen mit URL (nur aus der Websuche) und ggf. genutzter Dokumente.
"""


def baue_prompt(e: dict, kal: dict, dokumente: list[tuple[str, str]]) -> str:
    z = []
    z.append(f"Modus: {e['modus']}")
    z.append(f"Schulart: {e['schulart']} (Schleswig-Holstein)")
    z.append(f"Jahrgangsstufe: {e['jahrgang']}")
    if e.get("fach"):
        z.append(f"Fach: {e['fach']}")
    if e.get("kompetenz"):
        z.append(f"Überfachliche Kompetenz: {e['kompetenz']}")
    z.append(f"Datum der Vertretung: {e['datum'].strftime('%d.%m.%Y')}")
    z.append(f"Dauer: {e['dauer']} Minuten")
    z.append(f"Vertretungslehrkraft fachfremd: {'ja' if e['fachfremd'] else 'nein'}")
    z.append(f"Verfügbare Geräte: {', '.join(e['geraete']) or 'keine'}")
    if e.get("thema"):
        z.append(f"Zuletzt behandeltes Thema laut Stammlehrkraft: {e['thema']} "
                 "(dies hat Vorrang vor jeder Schätzung)")
    if e.get("hinweise"):
        z.append(f"Weitere Hinweise: {e['hinweise']}")

    if kal.get("gefunden"):
        z.append("\nPosition im Schuljahr (berechnet mit SH-Ferien und Feiertagen):")
        z.append(f"- Schuljahr {kal['schuljahr']}, {kal['halbjahr']}. Halbjahr")
        z.append(f"- {kal['tage_bisher']} von {kal['tage_gesamt']} Unterrichtstagen vergangen "
                 f"({kal['anteil']:.0%}, ca. {kal['wochen_bisher']} Unterrichtswochen)")
        z.append(f"- Im laufenden Halbjahr: {kal['hj_tage_bisher']} von {kal['hj_tage_gesamt']} Tagen")
        if kal.get("letzte_ferien"):
            z.append(f"- Letzte Ferien: {kal['letzte_ferien']}, seitdem "
                     f"{kal['unterrichtstage_seit_ferien']} Unterrichtstage")

    if dokumente:
        z.append("\nHochgeladene Dokumente. Gleiche Reihenfolge und Zeitangaben des schulinternen "
                 "Curriculums mit der Position im Schuljahr ab. Fehlen Zeitangaben, verteile die Themen "
                 "gleichmäßig und schreibe in der Einordnung deutlich: 'Zeitangaben fehlen – Schätzung'.")
        for name, text in dokumente:
            z.append(f"\n<dokument name=\"{name}\">\n{text}\n</dokument>")
    elif e["modus"].startswith("A"):
        z.append("\nKein Curriculum hochgeladen. Leite das wahrscheinliche Thema aus den "
                 "Fachanforderungen Schleswig-Holstein für diesen Jahrgang und der Position im Schuljahr ab. "
                 "Nutze dafür die Websuche.")
    return "\n".join(z)


def generiere(api_key: str, modell: str, prompt: str, websuche: bool, max_suchen: int = 6) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    tools = []
    if websuche:
        tools = [{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": max_suchen,
            "user_location": {"type": "approximate", "country": "DE", "region": "Schleswig-Holstein"},
        }]

    messages = [{"role": "user", "content": prompt}]
    texte, gefundene_urls = [], set()
    tokens_in = tokens_out = 0

    for _ in range(4):  # pause_turn kann bei langer Websuche auftreten
        kwargs = dict(model=modell, max_tokens=8000, system=SYSTEM, messages=messages)
        if tools:
            kwargs["tools"] = tools
        resp = client.messages.create(**kwargs)
        tokens_in += resp.usage.input_tokens
        tokens_out += resp.usage.output_tokens

        for block in resp.content:
            if block.type == "text":
                texte.append(block.text)
            elif block.type == "web_search_tool_result":
                inhalt = block.content
                if isinstance(inhalt, list):
                    for r in inhalt:
                        url = getattr(r, "url", None)
                        if url:
                            gefundene_urls.add(url.rstrip("/"))

        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break

    markdown = "".join(texte).strip()
    # Nur ab der Überschrift behalten (falls die KI etwas vorangestellt hat)
    start = markdown.find("# Vertretungsstunde")
    if start > 0:
        markdown = markdown[start:]

    genannte = {u.rstrip("/.,)") for u in re.findall(r"https?://[^\s\)\]>\"]+", markdown)}
    ungeprueft = sorted(u for u in genannte if u.rstrip("/") not in gefundene_urls)

    return {
        "markdown": markdown,
        "ungepruefte_links": ungeprueft if websuche else sorted(genannte),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }
