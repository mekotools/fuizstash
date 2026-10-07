# Prüfbericht — Fuizstash (Change 001)

Stand: 07.10.2026. Alles hier Genannte wurde ausgeführt, nicht gefolgert. Wo etwas
**nicht** geprüft ist, steht das ausdrücklich dabei.

## 1. Vorarbeiten („belegen, nicht annehmen")

| Nr. | Frage | Ergebnis | Beleg |
| --- | --- | --- | --- |
| 0.1 | Erzeugt fuiz eine Datei (`.toml`/`.zip`)? | **teilweise**: im ausgelieferten Programm existiert ein TOML-Erzeuger — die Downloadhilfe wird als `… <Titel>.toml` aufgerufen; der sichtbare Knopf in der Oberfläche ließ sich nicht bestätigen (Kartenmenüs zeigen Einstellungen/Start/Teilen/Speichern/Löschen) | Suche im Programmtext von `mekotools-fuiz-web`; Importfeld trägt `accept="application/toml, .toml, application/x-zip, .zip"` |
| 0.2 | Größe einer Einreichung | **gemessen**, aber klein: Bildprobe mit 8×8-PNG = **716 B**; größere Gegenprobe lokal: Quiz mit 6 Folienbildern je ~200 KB = **1,5 MB** (Base64 bläht um rund ein Drittel auf). Echte Fotoquizze stehen noch aus | Lauf vom 07.10. (716 B), lokaler Lauf mit erzeugter Bildprobe (1,5 MB) |
| 0.3 | Trägt das Schreiben in `kv_share` aus einem zweiten Behälter? | **ja** | eigener Probeeintrag gesetzt, von außen über `/share/<kennung>` mit HTTP 200 gelesen, danach wieder entfernt |
| 0.4 | Erfasst die Sicherung des Containerhosts den Datenordner? | **ja** | Eintrag `/poolio/docker` in der rsnapshot-Konfiguration von flip |

## 2. Prüfungen (automatisiert, 26 Stück)

`pytest` im Repo, alle **26 grün**. Abgedeckt: Zugang (ohne Kopfzeilen 401, fremde
Herkunft 403), Einreichen (Teilen-Link, Kennung, fremder Anbieter, kaputte Form,
unbekannt, abgelaufen, unlesbar, fehlender Titel), Trennung zweier Personen,
Übernahme (dauerhafte Kennung, gleiche Kennung beim zweiten Aufruf, Neueinreichung
aktualisiert den Link), Papierkorb/Wiederherstellen/endgültiges Löschen,
Papierkorb-Frist, Grenzen je Quiz und je Person, Einstellungen, gestörte Kopplung.

### Gegenproben (mutwillig gebrochen, rot gesehen, zurückgenommen)

| Mutation | erwartetes Ergebnis | Ergebnis |
| --- | --- | --- |
| `nutzer`-Bedingung aus der Listenabfrage entfernt (Trennung aufgehoben) | Trennungstests schlagen fehl | genau die zwei Trennungstests rot, alle anderen grün |
| Übernahme-Eintrag mit Frist statt fristlos angelegt | Dauerhaftigkeitstest schlägt fehl | `test_uebernahme_legt_dauerhaften_eintrag_an` rot, die übrigen Übernahmetests grün |

Die Prüfungen messen also wirklich das, was sie behaupten.

## 3. Abnahme am lebenden System (`fuizstash.mekotools.de`)

Ausgeführt am 07.10.2026 gegen den laufenden Dienst, ausschließlich mit eigenen
Testdaten; anschließend vollständig aufgeräumt.

- **Zugang:** Aufruf von außen ohne Anmeldung → **HTTP 401** mit
  `x-tinyauth-location: https://tinyauth.mekotools.de/login?login_for=app&redirect_uri=…fuizstash.mekotools.de%2Fablage`.
  Ohne Kopfzeilen am Behälter selbst → `{"detail":"Keine Anmeldung erkennbar…"}`.
- **Einreichen:** Teilen-Link des eigenen Bildquiz (Kennung `a739e463…`) eingereicht →
  Eintrag „Bildprobe (selbsttragend)", **2 Fragen · 716 B**, Speicherbalken
  „716 B von 250 MB belegt".
- **Trennung:** zweite, fremde Kennung sah **keinen** Eintrag; Öffnen und Löschen
  wurden verweigert, der Eintrag blieb unverändert.
- **Übernahme:** `/ablage/<id>/oeffnen` → **303** auf
  `https://fuiz.mekotools.de/share/<neue Kennung>`; im Teilen-Speicher lag der
  Eintrag mit `expires_at = NULL` (fristlos) und vollständigem Inhalt inklusive
  Base64-Bilddaten. Zweiter Aufruf → **dieselbe** Kennung (kein zweiter Eintrag).
- **Von außen abgerufen:** `https://fuiz.mekotools.de/share/<Kennung>` → **HTTP 200**,
  **18.092 Bytes**, Titel im Text, Base64-Bilddaten enthalten, Alt-Text
  „Rotes Testquadrat" vorhanden.
- **Endgültiges Löschen:** Eintrag weg, Übernahme-Kennung aus dem Teilen-Speicher
  entfernt (Abruf danach **HTTP 404**), Ablage leer, eigene Zeilen im Speicher
  unberührt (Gesamtzahl der Zeilen unverändert außer der eigenen).
- **Kopplung:** `/gesundheit` → `{"ok":true,…"tabelle_ok":true,"schreibbar":true}`.

## 4. Oberfläche

Geprüft im Browser mit 390 × 844 Bildpunkten (Telefon) und erzwungenem dunklen Schema:

- kein waagerechter Überlauf, weder hell noch dunkel
- hell `rgb(246,247,249)` / Text `rgb(27,29,33)`; dunkel `rgb(20,22,26)` / Text `rgb(236,237,239)`
- vier Bedienelemente je Eintrag, **keines unter 40 Bildpunkten Höhe** (Fingerbedienung)
- Eingabefeld füllt die Breite (324 von 390 Bildpunkten), Fortschrittsanzeige beim
  Absenden ist echt (kein Fortschrittsbalken, sondern Zustandstext)
- Einstellungsseite liest die Werte aus der Datenbank (25 / 250 / 30)

## 5. Ausdrücklich **nicht** geprüft

1. **Anmeldung durch einen Menschen.** Die Sperre fordert die Anmeldung an (belegt),
   der Klickweg über Pocket ID mit Passkey ist der letzte Schritt und bleibt der
   Lehrkraft vorbehalten — hier steht kein Anmeldegeheimnis zur Verfügung.
   Ebenso ungeprüft: die Wirkung des Abmeldens.
2. **Datei-Einreichung** (`.toml`/`.zip`) — bewusst nicht in Stufe 1 (siehe 0.1).
3. **Echte Fotoquizze** — die Größengrenzen (25 MB je Quiz, 250 MB je Person) sind ein
   Startwert aus kleinen Proben und nach dem ersten echten Quiz nachzuziehen.
4. **Gleichzeitiger Zugriff** von fuiz und Ablage auf `kv.db` unter Last — nur der
   Grundfall (wenige Einträge) wurde berührt.
