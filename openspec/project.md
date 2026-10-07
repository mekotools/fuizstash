# Quiz-Ablage für fuiz (MekoTools)

## Zweck

Ablage für fuiz-Quizze, die an der MekoTools-Anmeldung hängt: Quizze liegen auf
dem Server, sind geräteunabhängig, wiederherstellbar und werden mit einem Klick
als Kopie in den Browser übernommen.

## Warum es das braucht

fuiz hält Quizze ausschließlich im Browser der Lehrkraft (IndexedDB `FuizDB`) und
kennt keine Konten. Folgen: kein Backup, Bindung an Browserprofil und Gerät, auf
geteilten Geräten für die nächste Person sichtbar, keine Wiederherstellung nach
Aufräumen. Ein Übernahme-Weg auf den Server fehlt im amtlichen Programm.

## Fähigkeiten

| Fähigkeit | Spec | Stand |
| --- | --- | --- |
| Ablage (Bestand, Einreichen, Übernahme, Löschen) | `specs/ablage/spec.md` | geplant (Change 001) |
| Zugang (Sperre, Identität, Rechte am eigenen Bestand) | `specs/zugang/spec.md` | geplant (Change 001) |

## Fremdsysteme

- **fuiz** (`fuiz.mekotools.de`): amtliche Abbilder, digest-genagelt gespiegelt;
  wird **nicht** verändert. Zwei belegte Wege stehen zur Verfügung:
  - `PUT /share` legt einen Quiz-Inhalt unter einer Zufallskennung ab
    (KV-Speicher `kv.db`, Tabelle `kv_share`, Spalten `key`, `value`, `expires_at`).
    Der Inhalt ist selbsttragend: Bilder stecken als Base64 im Inhalt.
  - `/share/<kennung>` legt beim Aufruf eine **Kopie** im Browser an
    (`addCreation` → Weiterleitung auf `/quiz/<neue id>/edit`).
  - Die Oberfläche kann Dateien importieren (`application/toml, .toml,
    application/x-zip, .zip`).
- **Sperre** `mekotools-auth` (Pocket ID + Tinyauth auf dem Containerhost .50):
  Forward-Auth vor dem Dienst; sie reicht `remote-user`, `remote-email`,
  `remote-name`, `remote-groups`, `remote-sub` als Kopfzeilen durch.
- **Hosting**: Containerhost .50 / flip, Netz `coolify`, TLS endet am VPS.

## Konventionen

- Sprache der Specs und Changes: Deutsch (deutschsprachige Abnahme; CLI ist sprachneutral).
- Spec-Header tool-nativ: `## Purpose`, `## Requirements`, `### Requirement: <Name>`, `#### Scenario: <Name>`.
- Ein neuer Feature-Abschnitt = neues Change unter `changes/<id>/` + Spec-Fortschreibung im selben Commit.
- Datenschutz: Löschen entfernt alle abhängigen Daten (auch Zwischenstände), danach `VACUUM`.
- Werte/Belege werden gemessen und mit Datum berichtet, nicht behauptet.
