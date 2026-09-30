# Vertretungsgenerator

Streamlit-App, die druckfertige Vertretungsstunden für Gymnasien in Schleswig-Holstein erstellt:
Einordnung, Hinweise für die Vertretungslehrkraft, Ablauf, Aufgaben (immer analog nutzbar),
optionale digitale Ergänzung mit geprüften Links, Lösungen und Quellen.

## Drei Modi
- **A · Fach und Jahrgang:** Thema wird aus den Fachanforderungen SH und dem Zeitpunkt im Schuljahr geschätzt.
- **B · Überfachliche Kompetenz:** fachunabhängige Stunde, ideal für fachfremde Vertretung.
- **C · Mit Curriculum:** Upload von schulinternem Fachcurriculum und/oder Fachanforderungen (PDF, DOCX, TXT);
  Reihenfolge und Zeitangaben werden mit dem Datum abgeglichen.

Ein eingetragenes „zuletzt behandeltes Thema“ hat immer Vorrang.

## Einrichtung (einmalig, ca. 15 Minuten)
1. **API-Schlüssel:** Auf https://console.anthropic.com ein Konto anlegen, Guthaben aufladen,
   unter *Limits* ein monatliches Ausgabenlimit setzen und einen API-Key erstellen.
2. **GitHub:** Neues Repository anlegen (am besten *privat*) und alle Dateien dieses Ordners hochladen,
   inklusive `ferien_sh.json` und dem Ordner `.streamlit` (nur die `.example`-Datei!).
3. **Streamlit:** Auf https://share.streamlit.io mit GitHub anmelden → *Create app* → Repository wählen,
   Main file: `app.py`.
4. **Secrets:** Unter *Advanced settings* bzw. später *Settings → Secrets* eintragen:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   APP_PASSWORD = "euer-schulpasswort"
   ```
5. Deploy. Den Link und das Passwort ans Kollegium geben – niemand braucht ein eigenes Konto.

## Pflege
- **Ferien:** in `ferien_sh.json` (neue Schuljahre ergänzen, schulinterne bewegliche Ferientage eintragen).
  Einzelne freie Tage können auch direkt in der App in der Seitenleiste eingetragen werden.
- **Modell:** optional über das Secret `MODEL` änderbar.

## Datenschutz
Es werden nur Fach, Jahrgang, Datum, Thema und ggf. Curriculumstext an die KI übermittelt.
Keine Namen oder personenbezogenen Daten eingeben. Vor dem Einsatz im Kollegium Schulleitung und
Datenschutzbeauftragte:n informieren.

## Lokal testen
```
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # Schlüssel eintragen
streamlit run app.py
```
