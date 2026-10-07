# Change 001 — Fuizstash auf dem Server (Weg B)

**Status:** umgesetzt und ausgeliefert (07.10.2026); Katalogeintrag offen
**Datum:** 2026-10-07
**Vorgeschichte:** Nach Auslieferung von fuiz auf `fuiz.mekotools.de` (06.10.2026) stand die Frage
nach privaten und öffentlichen Quizzen. Festgestellt: fuiz hält Quizze nur im Browser; die amtliche
Bibliothek ist bei uns nicht in Betrieb und hinge an Cloudflare-Gebinden sowie an einer
gitlab.com-Identität. Dieser Change baut **keinen** Ersatz für die amtliche Bibliothek, sondern eine
eigene Ablage für angemeldete Lehrkräfte.

## Why

Quizze entstehen heute im Browser der Lehrkraft. Das hat drei praktische Folgen, die im Betrieb
stören: kein Backup (Browserprofil weg = Quizze weg), Bindung an ein Gerät (Schulrechner ≠ zuhause),
und auf geteilten Geräten sieht die nächste Person mit demselben Browserprofil die Quizze. Eine
Ablage, die an der Anmeldung hängt, beseitigt alle drei — ohne die gespiegelten fuiz-Abbilder
anzufassen.

## What Changes

Verhaltens-Delta gegenüber heute:

- **Neu: Einreichen.** Eine angemeldete Lehrkraft kann ein fuiz-Quiz in ihren Server-Bestand
  übernehmen — über den Teilen-Link aus fuiz (`/share/<kennung>`) oder, wenn vorhanden, über eine
  hochgeladene Datei (`.toml`/`.zip`, das Format, das die fuiz-Oberfläche importiert). Der Dienst
  legt eine eigene, vollständige Kopie ab (Bilder eingeschlossen); eine spätere Änderung an der
  Teilen-Kennung berührt den Bestand nicht.
- **Neu: Bestand je Nutzer.** Eingereichte Quizze erscheinen als Liste mit Titel, Anzahl Fragen,
  Größe, Einreichdatum und Herkunft. Zwei angemeldete Personen sehen jeweils nur ihren eigenen
  Bestand; ohne Anmeldung ist der Dienst überhaupt nicht erreichbar (Sperre davor).
- **Neu: Übernahme in den Browser.** Ein Knopf je Quiz legt in fuiz einen dauerhaften
  Teilen-Eintrag an und schickt die Lehrkraft auf die fuiz-Seite dieses Eintrags — dort landet das
  Quiz mit Bildern als Kopie im Browser, ein Klick, kein Datei-Handling. Zusätzlich bleibt der
  Datei-Download möglich (Import in fuiz über „Import").
- **Neu: Löschen mit Sicherheitsnetz.** Löschen verschiebt in einen Papierkorb (30 Tage), aus dem
  wiederhergestellt werden kann; endgültiges Löschen entfernt Eintrag _und_ die zugehörige
  Übernahme-Kennung in fuiz sowie alle Zwischenstände, anschließend wird der Speicher verdichtet.
- **Unverändert:** fuiz selbst. Kein eigener Bau, kein Patch, kein Cloudflare, keine
  gitlab.com-Identität. Angemeldet wird sich wie bei den übrigen geschützten MekoTools-Werkzeugen
  über `auth.mekotools.de` (Pocket ID) mit der Sperre `mekotools-auth`.

## Specs-Delta

| Fähigkeit | Art | Datei |
| --- | --- | --- |
| Ablage | ADDED | `changes/001-fuizstash/specs/ablage/spec.md` |
| Zugang | ADDED | `changes/001-fuizstash/specs/zugang/spec.md` |

## Nicht-Ziele (ausdrücklich)

- **Keine** öffentliche, durchsuchbare Quiz-Bibliothek wie auf fuiz.org (die amtliche hängt an
  Cloudflare D1/R2/KV und an Merge-Requests in ein gitlab.com-Repository; ein Nachbau wäre ein
  eigener Bau plus fremde Identität). Ein eigener öffentlicher Katalog ist ein **späterer** Change
  und würde auf derselben Ablage aufsetzen.
- **Keine** Anmeldung bei fuiz, **keine** Nutzerkonten in fuiz selbst.
- **Keine** Versionen und **keine** Freigaben zwischen Kolleginnen und Kollegen in Stufe 1
  (Entscheidung des Eigentümers steht noch aus, siehe Offene Fragen).
- **Kein** automatischer Abgleich wie bei Google Drive in der amtlichen Oberfläche (das ginge nur
  mit eigenem Bau, siehe `design.md`, Weg A).

## Offene Fragen

1. **Versionen:** jede Änderung als eigener Stand, oder ersetzt eine Neueinreichung den Eintrag?
2. **Freigaben:** sollen Kolleginnen und Kollegen Quizze untereinander freigeben können, oder
   bleibt der Bestand strikt persönlich?
3. **Datei-Einreichung:** der Import-Weg der Oberfläche ist belegt (`.toml`/`.zip`); zu prüfen ist,
   ob die Oberfläche auch einen Export-Knopf anbietet, der eine solche Datei erzeugt. Solange das
   offen ist, ist der Teilen-Link der Hauptweg.
