## ADDED Requirements

### Requirement: Nur angemeldete Personen erreichen die Ablage

Die Ablage steht ausschließlich hinter der Sperre `mekotools-auth` (Pocket ID). Ohne gültige
Anmeldung gibt es keine Inhalte und keine Handlungen zu sehen.

#### Scenario: Aufruf ohne Anmeldung

- **Akteure:** nicht angemeldete Person
- **Eingaben:** Aufruf der Adresse der Ablage
- **Ergebnis:** Weiterleitung auf die Anmeldung von `auth.mekotools.de`; keine Liste, keine
  Kennungen, keine Inhalte im ausgelieferten Quelltext.

#### Scenario: Abmeldung beendet den Zugriff

- **Akteure:** angemeldete Person
- **Eingaben:** Abmeldung an der Sperre, danach Aufruf der Ablage
- **Ergebnis:** erneute Anmeldung erforderlich; der Bestand bleibt unverändert erhalten.

### Requirement: Identität kommt aus der Sperre

Die Ablage führt **kein** eigenes Konto und kein eigenes Passwort. Die Identität entnimmt sie den
von der Sperre durchgereichten Kopfzeilen (`remote-user`, `remote-email`). Änderungen an der
Sperre (anderer Anbieter, andere Kennung) werden als eigener Vorgang behandelt.

#### Scenario: Kein zweites Anmeldeverfahren

- **Akteure:** angemeldete Lehrkraft
- **Eingaben:** erster Aufruf nach der Anmeldung an der Sperre
- **Ergebnis:** die Ablage ordnet den Bestand der Person anhand der Kopfzeilen zu; es wird weder
  ein Konto angelegt noch ein Passwort abgefragt.

#### Scenario: Fehlende Kopfzeilen werden nicht geraten

- **Akteure:** Betrieb
- **Eingaben:** Aufruf des Dienstes ohne die Kopfzeilen der Sperre (z. B. direkt am Behälter)
- **Ergebnis:** die Anfrage wird abgelehnt und im Betriebsprotokoll benannt; es wird **kein**
  Ersatzbestand und **kein** anonymer Zugang eröffnet.
