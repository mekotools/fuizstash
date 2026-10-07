# MekoTools-Fuizstash

Ablage für fuiz-Quizze, an der MekoTools-Anmeldung hängend: Quizze liegen auf dem
Server, sind geräteunabhängig, wiederherstellbar und werden mit einem Klick als
Kopie im Browser geöffnet.

- **Erreichbar unter:** https://fuizstash.mekotools.de (nur mit Anmeldung)
- **Betrieb, Speicherorte, Notfälle:** [docs/betrieb.md](docs/betrieb.md)
- **Prüfbericht (was belegt ist und was nicht):** [docs/pruefbericht.md](docs/pruefbericht.md)
- **Entwurf und Aufgaben:** `openspec/changes/001-fuizstash/` · **Überblick:** `openspec/project.md`

## Warum

fuiz hält Quizze ausschließlich im Browser (IndexedDB) und kennt keine Konten:
kein Backup, gerätegebunden, auf geteilten Geräten für die nächste Person sichtbar.
Diese Ablage ergänzt fuiz um einen Server-Bestand je angemeldeter Lehrkraft —
**ohne** die gespiegelten fuiz-Abbilder zu verändern.

## Arbeitsweise

1. In fuiz ein Quiz öffnen, auf **Teilen** gehen, den Link kopieren.
2. In der Ablage einfügen → der Dienst legt eine **vollständige Kopie** ab (Bilder
   reisen als Teil des Inhalts mit).
3. **In fuiz öffnen** → ein Knopf legt einen dauerhaften fuiz-Eintrag an und schickt
   den Browser dorthin; das Quiz landet als Kopie im Browser. Ein Klick, kein
   Datei-Handling.
4. Löschen schiebt in einen Papierkorb (30 Tage). Endgültiges Löschen entfernt auch
   den Übernahme-Eintrag in fuiz wieder.

Zwei Personen sehen jeweils nur ihren eigenen Bestand. Ohne Anmeldung gibt es keine
Inhalte — die Sperre `mekotools-auth` steht davor.

## Bestandteile

```
app/main.py           Wege, Zugang, Oberflächen-Aufbereitung
app/datenbank.py      SQLite: Bestand je Person, Papierkorb, Einstellungen, Verlauf
app/fuizspeicher.py   Kopplung an den Teilen-Speicher von fuiz (lesen + eigene Einträge)
app/kennungen.py      Teilen-Link/Kennung lesen und prüfen (Form zuerst!)
app/vorlagen/         HTML-Vorlagen   app/statisch/stil.css   Stil
tests/test_ablage.py  26 Prüfungen
docker-compose.yml    Behälteraufsatz für flip
ausliefern.sh         Spiegeln, bauen, neu erzeugen
```

## Regeln für die Weiterarbeit

- Jedes neue Vorhaben beginnt als Change unter `openspec/changes/<id>/`
  (`proposal.md`, `design.md`, `tasks.md`, bei Spec-Änderungen
  `specs/<fähigkeit>/spec.md` als Delta).
- Nach der Umsetzung wird das Delta in `openspec/specs/` angewendet und der Change
  nach `openspec/changes/archive/` verschoben.
- Prüfen: `cd openspec && OPENSPEC_TELEMETRY=0 npx --yes @fission-ai/openspec@latest validate <id>`
  (das Urteil steht in der **ersten** Zeile).
- Belege statt Behauptungen: Messwerte mit Datum, keine erfundenen Zahlen.

## Entwickeln

    uv venv .venv --python 3.12
    uv pip install --python .venv/bin/python -r requirements.txt
    .venv/bin/python -m pytest

## Umgebung

- `FUIZ_KV` — Pfad zur `kv.db` von fuiz im Behälter (dort `/fuiz/kv.db`)
- `FUIZSTASH_DATEN` — Pfad zur eigenen Datenbank (Vorgabe `/daten/fuizstash.db`)
- `FUIZSTASH_FUIZ_BASIS` — Adresse der eigenen fuiz-Instanz für die Übernahme
- `FUIZSTASH_FUIZ_HOSTS` — erlaubte Hosts für Teilen-Links (Komma-getrennt)

Inhalte stammen aus der eigenen fuiz-Instanz; fremde Anbieter (z. B. `fuiz.org`)
werden abgelehnt, weil deren Inhalte nicht im eigenen Teilen-Speicher liegen.
