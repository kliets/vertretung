"""Vertretungsgenerator – Streamlit-App für Gymnasien in Schleswig-Holstein."""
import io
from datetime import date

import streamlit as st
from docx import Document
from pypdf import PdfReader

from export import als_html
from generator import baue_prompt, generiere
from schulkalender import lade_ferien, schuljahr_info

st.set_page_config(page_title="Vertretungsgenerator", page_icon="📋", layout="centered")

MAX_ZEICHEN = 120_000  # Obergrenze für Dokumenttext (Kosten und Kontext)

JAHRGAENGE = ["5", "6", "7", "8", "9", "10", "E (11)", "Q1 (12)", "Q2 (13)"]
SCHULARTEN = ["Gymnasium", "Gemeinschaftsschule", "Gemeinschaftsschule mit Oberstufe"]
FAECHER = ["Mathematik", "Physik", "Informatik", "Chemie", "Biologie", "Deutsch", "Englisch",
           "Französisch", "Latein", "Spanisch", "Geschichte", "Geographie", "Wirtschaft/Politik",
           "Philosophie", "Religion", "Kunst", "Musik", "Sport (Theorie)", "Anderes …"]
KOMPETENZEN = ["Lesekompetenz und Textverständnis", "Lern- und Arbeitstechniken (Methodenkompetenz)",
               "Medien- und Informationskompetenz", "Problemlösen und logisches Denken",
               "Argumentieren und Diskutieren", "Kooperation (Sozialkompetenz)",
               "Selbstorganisation (Selbstkompetenz)", "Demokratiebildung",
               "Bildung für nachhaltige Entwicklung", "Andere …"]
GERAETE = ["Tablets/iPads", "Smartphones der Schülerinnen und Schüler", "Computerraum",
           "Beamer/Tafel digital"]


# ---------- Zugang ----------
def geheimnis(name: str, standard=None):
    """Liest einen Eintrag aus den Streamlit-Secrets, ohne Absturz wenn keine hinterlegt sind."""
    try:
        return st.secrets.get(name, standard)
    except Exception:
        return standard


def zugang_ok() -> bool:
    pw = geheimnis("APP_PASSWORD")
    if not pw:
        return True
    if st.session_state.get("zugang"):
        return True
    st.title("Vertretungsgenerator")
    eingabe = st.text_input("Schulpasswort", type="password")
    if eingabe:
        if eingabe == pw:
            st.session_state.zugang = True
            st.rerun()
        st.error("Passwort stimmt nicht.")
    return False


if not zugang_ok():
    st.stop()

api_key = geheimnis("ANTHROPIC_API_KEY")
modell = geheimnis("MODEL", "claude-sonnet-5-5")


# ---------- Dokumente lesen ----------
@st.cache_data(show_spinner=False)
def text_aus_datei(name: str, daten: bytes) -> str:
    if name.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(daten))
        return "\n".join(f"[Seite {i + 1}]\n{p.extract_text() or ''}" for i, p in enumerate(reader.pages))
    if name.lower().endswith(".docx"):
        doc = Document(io.BytesIO(daten))
        teile = [p.text for p in doc.paragraphs if p.text.strip()]
        for t in doc.tables:
            for zeile in t.rows:
                teile.append(" | ".join(z.text.strip() for z in zeile.cells))
        return "\n".join(teile)
    return daten.decode("utf-8", errors="replace")


# ---------- Seitenleiste ----------
with st.sidebar:
    st.header("Einstellungen")
    websuche = st.toggle("Websuche nach Materialien", value=True,
                         help="Sucht passende Materialien und Links. Kostet etwas mehr und dauert länger.")
    st.caption(f"KI-Modell: {modell}")

    st.subheader("Schulinterne freie Tage")
    st.caption("Zusätzlich zu SH-Ferien und Feiertagen, z. B. eigene bewegliche Ferientage oder pädagogische Tage.")
    zusatz_text = st.text_area("Ein Datum pro Zeile (TT.MM.JJJJ)", height=90, key="zusatz")
    zusatz = []
    for zeile in zusatz_text.splitlines():
        try:
            t, m, j = zeile.strip().split(".")
            zusatz.append(date(int(j), int(m), int(t)))
        except ValueError:
            if zeile.strip():
                st.warning(f"Nicht erkannt: {zeile}")

    with st.expander("Hinterlegte SH-Ferien anzeigen"):
        for sj_name, sj in lade_ferien()["schuljahre"].items():
            st.markdown(f"**{sj_name}** · Unterricht {sj['beginn']} bis {sj['ende']}")
            for n, v, b in sj["ferien"]:
                st.markdown(f"- {n}: {v} bis {b}")
        st.caption("Anpassen in der Datei ferien_sh.json im GitHub-Repository.")

    st.divider()
    st.caption("Bitte keine Namen oder andere personenbezogene Daten eingeben.")


# ---------- Hauptbereich ----------
st.title("Vertretungsgenerator")
st.write("Erstellt eine druckfertige Vertretungsstunde mit Ablauf, Aufgaben, Lösungen und Materiallinks.")

modus = st.radio(
    "Wie viel wissen Sie über die Lerngruppe?",
    ["A · Fach und Jahrgang", "B · Überfachliche Kompetenz", "C · Mit Curriculum (Upload)"],
    horizontal=False,
)

c1, c2 = st.columns(2)
with c1:
    schulart = st.selectbox("Schulart", SCHULARTEN)
    jahrgang = st.selectbox("Jahrgangsstufe", JAHRGAENGE, index=3)
with c2:
    datum = st.date_input("Datum der Vertretung", value=date.today(), format="DD.MM.YYYY")
    dauer = st.selectbox("Dauer", [45, 90, 60], format_func=lambda x: f"{x} Minuten")

fach = kompetenz = None
if modus.startswith(("A", "C")):
    fach = st.selectbox("Fach", FAECHER)
    if fach == "Anderes …":
        fach = st.text_input("Fach eingeben")
else:
    kompetenz = st.selectbox("Überfachliche Kompetenz", KOMPETENZEN)
    if kompetenz == "Andere …":
        kompetenz = st.text_input("Kompetenz eingeben")

fachfremd = st.checkbox("Vertretung durch fachfremde Lehrkraft", value=True)
geraete = st.multiselect("Verfügbare Geräte (leer lassen = nur analog)", GERAETE)
thema = st.text_input("Zuletzt behandeltes Thema (falls bekannt)",
                      help="Hat Vorrang vor jeder Schätzung – die genaueste Angabe überhaupt.")

dokumente = []
if modus.startswith("C"):
    dateien = st.file_uploader(
        "Schulinternes Fachcurriculum und/oder Fachanforderungen (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt", "md"], accept_multiple_files=True,
        help="Tipp: Bei den Fachanforderungen nur die Seiten zum Jahrgang hochladen – das spart Kosten.")
    for d in dateien or []:
        text = text_aus_datei(d.name, d.getvalue())
        if len(text) > MAX_ZEICHEN:
            st.warning(f"{d.name} ist sehr lang und wurde gekürzt. Besser nur die relevanten Seiten hochladen.")
            text = text[:MAX_ZEICHEN]
        if not text.strip():
            st.warning(f"Aus {d.name} ließ sich kein Text lesen (evtl. eingescannt).")
        dokumente.append((d.name, text))

hinweise = st.text_area("Weitere Hinweise (optional)",
                        placeholder="z. B. Raum ohne Tafel, Klasse arbeitet gut in Gruppen, Klausur nächste Woche")

# Kalender-Einordnung sofort anzeigen
kal = schuljahr_info(datum, zusatz)
if not kal.get("gefunden"):
    st.warning("Das Datum liegt außerhalb der hinterlegten Schuljahre bzw. in den Sommerferien.")
elif not kal["unterrichtstag"]:
    st.warning(f"Am gewählten Tag ist kein Unterricht ({kal['grund_frei']}).")
else:
    st.info(f"Schuljahr {kal['schuljahr']}, {kal['halbjahr']}. Halbjahr · "
            f"Unterrichtstag {kal['tage_bisher'] + 1} von {kal['tage_gesamt']} "
            f"({kal['anteil']:.0%} des Schuljahres)")

if modus.startswith("C") and not dokumente:
    st.caption("Ohne Upload wird wie in Modus A geschätzt.")

if st.button("Stunde erstellen", type="primary", use_container_width=True):
    if not api_key:
        st.error("Kein API-Schlüssel hinterlegt. In Streamlit unter Settings → Secrets "
                 "ANTHROPIC_API_KEY eintragen.")
        st.stop()
    if (modus.startswith(("A", "C")) and not fach) or (modus.startswith("B") and not kompetenz):
        st.error("Bitte Fach bzw. Kompetenz angeben.")
        st.stop()

    eingaben = dict(modus=modus, schulart=schulart, jahrgang=jahrgang, fach=fach, kompetenz=kompetenz,
                    datum=datum, dauer=dauer, fachfremd=fachfremd, geraete=geraete,
                    thema=thema.strip(), hinweise=hinweise.strip())
    prompt = baue_prompt(eingaben, kal, dokumente)

    with st.status("Stunde wird erstellt – das dauert etwa 1–2 Minuten …", expanded=False) as status:
        try:
            ergebnis = generiere(api_key, modell, prompt, websuche)
            status.update(label="Fertig", state="complete")
        except Exception as fehler:  # API-Fehler verständlich anzeigen
            status.update(label="Fehler", state="error")
            st.error(f"Die Erstellung ist fehlgeschlagen: {fehler}")
            st.stop()

    st.session_state.ergebnis = ergebnis
    st.session_state.titel = f"Vertretung {jahrgang} {fach or kompetenz} {datum:%d.%m.%Y}"

# ---------- Ergebnis ----------
if "ergebnis" in st.session_state:
    erg = st.session_state.ergebnis
    titel = st.session_state.titel
    st.divider()

    if not erg["markdown"]:
        st.error("Die KI hat keine Stundenkarte geliefert. Bitte erneut versuchen.")
    else:
        if erg["ungepruefte_links"]:
            st.warning("Diese Links stammen nicht aus der Websuche und sind ungeprüft – bitte vor dem Einsatz öffnen:\n\n"
                       + "\n".join(f"- {u}" for u in erg["ungepruefte_links"]))

        dateiname = titel.replace(" ", "_").replace("/", "-").replace(".", "-")
        d1, d2 = st.columns(2)
        d1.download_button("Druckversion (HTML)", als_html(erg["markdown"], titel),
                           file_name=f"{dateiname}.html", mime="text/html", use_container_width=True)
        d2.download_button("Text (Markdown)", erg["markdown"],
                           file_name=f"{dateiname}.md", mime="text/markdown", use_container_width=True)
        st.caption("Druckversion im Browser öffnen und über „Drucken“ ausdrucken oder als PDF speichern. "
                   "Aufgaben und Lösungen beginnen jeweils auf einer neuen Seite.")

        st.markdown(erg["markdown"])
        st.caption(f"Verbrauch: {erg['tokens_in']:,} Eingabe- und {erg['tokens_out']:,} Ausgabe-Tokens"
                   .replace(",", "."))
