# Aufgaben — Quiz-Ablage (Change 001)

Stand 07.10.2026. Belege je Punkt im `docs/pruefbericht.md`.

## 0. Vorarbeiten (belegen, nicht annehmen)

- [x] 0.1 Export-Weg in fuiz bestätigt: **teilweise** — ein TOML-Erzeuger ist im ausgelieferten
      Programm vorhanden (Aufruf als `<Titel>.toml`), ein sichtbarer Knopf dafür ließ sich nicht
      bestätigen. Folge: Datei-Einreichung bleibt in Stufe 1 offen (siehe 1.4).
- [x] 0.2 Größen gemessen: Bildprobe 716 B; größere Probe (6 Folienbilder, je ~200 KB) 1,5 MB.
      **Offen:** echte Fotoquizze — Grenzen danach nachziehen.
- [x] 0.3 Schreiben in `kv_share` aus einem zweiten Behälter geprüft: Probeeintrag gesetzt, von
      außen mit HTTP 200 gelesen, danach entfernt.
- [x] 0.4 Sicherung geprüft: `/poolio/docker` steht in der rsnapshot-Konfiguration von flip.

## 1. Dienst (Backend)

- [x] 1.1 Gerüst in `/poolio/docker/mekotools-quizablage` — SQLite, ein Prozess, Scheduler im
      Prozess (Papierkorb-Räumung alle 6 Stunden), keine Fremddienste.
- [x] 1.2 Bestand je Person: Anlegen, Auflisten, Einzelabruf, Größenkennzahlen.
- [x] 1.3 Einreichen über Teilen-Kennung (lesender Zugriff); Fehlerfälle mit Klartextgrund
      (unbekannt, abgelaufen, unlesbar, fehlender Titel, fremder Anbieter, kaputte Form).
- [ ] 1.4 Einreichen per Datei (`.toml`/`.zip`) — **nicht gebaut**: braucht eine Umsetzung des
      TOML-Aufbaus in den Teilen-Aufbau; nach 0.1 zurückgestellt.
- [x] 1.5 Übernahme: fristloser Eintrag in fuiz, Weiterleitung, Kennung je Eintrag gemerkt und
      beim erneuten Öffnen wiederverwendet.
- [x] 1.6 Löschen: Papierkorb (30 Tage), Wiederherstellen, endgültiges Löschen samt
      Übernahme-Kennung und Verdichtung (`VACUUM`).
- [x] 1.7 Grenzen je Quiz und je Person, mit sichtbarem Stand und Klartextgrund.
- [x] 1.8 Startprüfung der Kopplung: fehlen Datei, Tabelle oder Spalten, erscheint ein sichtbarer
      Betriebsvermerk; Einreichen meldet den Grund im Klartext.

## 2. Zugang

- [x] 2.1 Traefik-Kennzeichnungen (`quizablage.mekotools.de`, Sperre `mekotools-auth`) — von außen
      belegt: HTTP 401 mit Anmelde-Weiterleitung.
- [x] 2.2 Identität aus den Kopfzeilen (`remote-sub`, `remote-user`, `remote-email`); Aufrufe ohne
      Kopfzeilen werden abgelehnt und protokolliert.
- [x] 2.3 Gegenprobe ohne Anmeldung: landet an der Anmeldung („login_for=app" mit Rückleitung auf
      die Ablage). **Offen:** Wirkung des Abmeldens (menschlicher Klickweg).
- [x] 2.4 Regel für die Sperre eingetragen (`TINYAUTH_APPS_QUIZABLAGE_CONFIG_DOMAIN` und
      `_OAUTH_WHITELIST`); Sperrdienst einzeln neu erzeugt, andere Dienste des Stapels unberührt
      (`pocket-id` lief weiter, `shadowbroker` weiterhin 401).

## 3. Oberfläche

- [x] 3.1 Liste mit Titel, Fragenzahl, Größe, Datum; Zustand „Papierkorb"; Verlauf.
- [x] 3.2 Einreichen-Formular mit sichtbarem Zustand beim Absenden und sichtbaren Fehlern
      (Klartext statt stiller Fehler).
- [x] 3.3 Handlungen „In fuiz öffnen", „Sicherung", „Löschen", im Papierkorb „Wiederherstellen" und
      „Endgültig löschen" — keine funktionslosen Knöpfe.
- [x] 3.4 Löschen mit Bestätigung; Speicherbalken mit Anteil und Klartext.
- [x] 3.5 Mobile Prüfung (390 × 844) und dunkles Schema im Browser geprüft: kein waagerechter
      Überlauf, kein Bedienelement unter 40 Bildpunkten Höhe.

## 4. Prüfungen

- [x] 4.1 26 automatische Prüfungen, alle grün (Trennung, Einreichen mit Bildern, abgelaufene
      Kennung, Übernahme, Papierkorb, endgültiges Löschen, Grenzen, gestörte Kopplung).
- [x] 4.2 Gegenprobe: zwei Mutationen gesetzt, rot gesehen, zurückgenommen (Trennung; Frist des
      Übernahme-Eintrags).
- [x] 4.3 Abnahme am lebenden System mit Belegen (Kennungen, 18.092 Bytes, Bild sichtbar,
      HTTP 404 nach dem Aufräumen).

## 5. Auslieferung

- [x] 5.1 Behälter läuft gesund, von außen erreichbar **nur** mit Anmeldung.
- [ ] 5.2 Katalogeintrag `mekotools-quizablage` — **offen**: braucht die drei Doku-Bausteine
      (Anleitung, Didaktik, Unterrichtsentwurf) und die Entscheidung, ob ein Werkzeug, das ein
      Konto verlangt, in den öffentlichen Katalog gehört.
- [x] 5.3 Betriebsdoku: `README.md` (Adresse, Speicherorte, Sicherung, Papierkorb, Kopplung,
      Rückfallweg) und `docs/betrieb.md`.
