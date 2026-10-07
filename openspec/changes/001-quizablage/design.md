# Design — Quiz-Ablage (Change 001)

## Ausgangslage (gemessen, 07.10.2026)

- fuiz hält Quizze in der IndexedDB `FuizDB` (`creations`, `images`, `reports`); die
  Bearbeitungsseite `/quiz/<id>/edit` liest aus dieser lokalen Datenbank, `id` ist ein lokaler
  Zähler. Es gibt serverseitig **keinen** Quiz-Bestand.
- Die einzige serverseitige Kopie ist der Teilen-Speicher: `kv.db` im Datenordner des
  fuiz-Web-Behälters, Tabelle `kv_share (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires_at INTEGER)`.
  `PUT /share` schreibt `crypto.randomUUID()` mit **30 Tagen** Frist; `expires_at IS NULL` bedeutet
  nachweislich „läuft nie ab" (Aufräumen löscht nur abgelaufene Zeilen).
- Der Teilen-Inhalt ist **selbsttragend**: `IdlessFullFuizConfig` trägt Bilder als
  `{Image:{Base64:{data,alt}}}`. Am lebenden System geprüft: ein Quiz mit zwei Bildern eingereicht
  (Kennung `a739e463…`), im Browser aufgerufen → Weiterleitung `/quiz/1/edit`, Bilder mit
  `naturalWidth=8/Height=8` sichtbar, Titel und Fragetexte im DOM. Der Bild-Transport über den
  Teilen-Weg ist damit belegt, nicht nur gelesen.
- Die Oberfläche importiert Dateien vom Typ `application/toml, .toml, application/x-zip, .zip`
  (Zip = `config.toml` + Bilder, dasselbe Format wie im amtlichen Bibliotheks-Repository). Ein
  Download-Helfer (`new File` → `URL.createObjectURL` → `a.download`) ist im ausgelieferten Programm
  vorhanden; ob ein sichtbarer Export-Knopf darauf zeigt, ist **noch zu prüfen**.
- Anmelde-Identität liefert die Sperre `mekotools-auth` als Kopfzeilen (`remote-user`,
  `remote-email`, `remote-groups`, `remote-sub`).

## Entscheidung: eigener Dienst neben fuiz (Weg B)

Verworfen wurde **Weg A**: ein eigener Fernspeicher-Anbieter *in* der fuiz-Oberfläche (die
Schnittstelle `RemoteSyncProvider` ist amtlich vorhanden, amtlich ist nur Google Drive eingetragen).
Weg A wäre das nahtlosere Erlebnis, verlangt aber einen **eigenen Bau** des Website-Abbilds: damit
endet das digest-genagelte Spiegeln für dieses eine Abbild, und wir pflegen dauerhaft einen Patch
gegen eine fremde Codebasis. Aufwand und Dauerrisiko stehen in keinem Verhältnis zum Nutzen.

Gewählt: ein **eigener kleiner Dienst** (`quizablage.mekotools.de`) hinter der Sperre. Er benutzt
fuiz nur über Wege, die die amtliche Software ohnehin anbietet. Kein Eingriff in die Abbilder.

## Einreichen: Teilen-Link als Hauptweg

1. Lehrkraft klickt in fuiz „Teilen" (die Oberfläche kopiert den Link `/share/<kennung>`).
2. Lehrkraft fügt den Link in der Ablage ein.
3. Die Ablage liest den Inhalt **lesend** aus `kv_share` (derselbe Host, dasselbe Laufwerk) und
   legt eine eigene, vollständige Kopie im eigenen Bestand ab.

Begründung: der Inhalt ist selbsttragend (Bilder eingeschlossen) und der Weg ist am lebenden System
belegt. Der Browser der Lehrkraft ist nicht beteiligt; es gibt keinen zweiten Anmeldeweg und keine
Datei-Handhabung.

Alternative (Zusatz, nicht Ersatz): **Datei hochladen** (`.toml`/`.zip`) für Fälle, in denen eine
Datei schon vorliegt. Wird nur gebaut, wenn der Export-Knopf in fuiz bestätigt ist.

## Übernahme in den Browser: dauerhafter Teilen-Eintrag

Statt die Lehrkraft eine Datei herunterladen und importieren zu lassen, legt der Dienst beim Klick
„In fuiz öffnen" in fuiz einen **neuen** Teilen-Eintrag an (`PUT /share`-Semantik, jedoch ohne Frist
und mit dem im Bestand liegenden Inhalt) und leitet auf `/share/<neue kennung>` um. fuiz legt das
Quiz im Browser als Kopie an — derselbe Vorgang, den ein geteilter Link immer auslöst.

Nebeneffekt, der bewusst so ist: nach der Übernahme lebt das Quiz wieder im Browser, und der Bestand
bleibt die Sicherung. Maßgeblich ist der Bestand; die Übernahme ist ein Transportweg.

## Kopplung und ihre Absicherung

Die Einreichung liest und die Übernahme schreibt in die Tabelle `kv_share` von fuiz. Das ist eine
Kopplung an eine fremde, aber offen gemessene Struktur:

- **Nur anhängen, nie ändern:** die Ablage schreibt ausschließlich neue Zeilen mit frischen
  Kennungen und `expires_at = NULL`; sie liest, löscht oder verändert keine fremden Zeilen. Das
  Aufräumen von fuiz löscht nur abgelaufene Zeilen und lässt fristlose unberührt (belegt im Quelltext).
- **Schreibzugriff klein halten:** eigener Datenordner des Dienstes plus **lesender** Blick auf die
  fuiz-Datenbank für die Einreichung; für die Übernahme genau eine Schreiboperation (INSERT).
- **Erkennbarer Bruch:** fehlt die Tabelle/das Feld nach einem fuiz-Update, meldet die Ablage das
  sichtbar im Betrieb (Prüfung beim Start + beim Einreichen), statt still zu scheitern.
- **Rückfallweg:** Download der Datei (`.toml`/`.zip`) und Import in fuiz — funktioniert auch, wenn
  die Kopplung einmal bricht.

## Datenschutz, Sicherung, Aufbewahrung

- Zugriff nur angemeldet; jeder sieht nur seinen eigenen Bestand. Die Identität kommt aus den
  Kopfzeilen der Sperre, damit gibt es **kein zweites Konto** und kein Passwort in diesem Dienst.
- Löschen: Papierkorb 30 Tage, danach endgültig; „endgültig löschen" entfernt zusätzlich die
  Übernahme-Kennung in fuiz und alle Zwischenstände, anschließend `VACUUM` (Grundsatz: Löschen
  entfernt alle abhängigen Daten).
- Sicherung: der Datenordner liegt unter dem gesicherten Pfad des Containerhosts; Prüfung, ob die
  vorhandene Sicherung ihn erfasst, gehört zu den Aufgaben (nicht angenommen, sondern geprüft).
- Größen: Base64 bläht Bilder um etwa ein Drittel auf. Je Quiz wird eine Obergrenze gesetzt und die
  Größe je Eintrag und je Nutzer **sichtbar** angezeigt (keine stillen Grenzen).

## Offen (entscheidet der Eigentümer)

1. Versionen je Einreichung oder Ersetzen?
2. Freigaben zwischen Kolleginnen und Kollegen oder strikt persönlicher Bestand?
3. Öffentlicher Katalog auf `mekotools.de` als eigener späterer Change (auf derselben Ablage)?
