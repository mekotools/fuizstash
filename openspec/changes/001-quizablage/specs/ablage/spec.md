## ADDED Requirements

### Requirement: Eigener Bestand je angemeldeter Person

Die Ablage führt je angemeldeter Person einen getrennten Bestand eingereichter Quizze. Ein Quiz
trägt Titel, Anzahl Fragen, Größe, Einreichdatum, Herkunft (Teilen-Kennung oder Datei) und eine
eigene Kennung. Der vollständige Inhalt wird gespeichert, Bilder eingeschlossen.

#### Scenario: Zwei Personen sehen getrennte Bestände

- **Akteure:** zwei angemeldete Lehrkräfte A und B
- **Eingaben:** A reicht ein Quiz ein; B öffnet die Ablage
- **Ergebnis:** A sieht das Quiz in ihrer Liste, B sieht es nicht. Kein Quiz ist ohne die
  zugehörige Kennung über die Schnittstelle abrufbar.

#### Scenario: Bestand überlebt einen Gerätewechsel

- **Akteure:** angemeldete Lehrkraft
- **Eingaben:** Einreichung an einem Rechner, Aufruf der Ablage an einem anderen Rechner
- **Ergebnis:** dieselbe Liste mit demselben Inhalt; die Ablage ist nicht an Browser oder Gerät
  gebunden.

### Requirement: Einreichen eines Quiz

Eine angemeldete Person reicht ein Quiz ein, indem sie die Teilen-Kennung aus fuiz angibt. Die
Ablage liest den Inhalt (lesend) aus dem Teilen-Speicher von fuiz und legt eine eigene vollständige
Kopie ab. Eine später geänderte oder abgelaufene Teilen-Kennung berührt den Bestand nicht. Optional
kann eine Datei im von fuiz importierbaren Format (`.toml`, `.zip`) hochgeladen werden.

#### Scenario: Einreichen über die Teilen-Kennung

- **Akteure:** angemeldete Lehrkraft
- **Eingaben:** Teilen-Link aus fuiz, der ein Quiz mit Bildern enthält
- **Ergebnis:** ein Eintrag im eigenen Bestand; das Bild ist im gespeicherten Inhalt enthalten und
  wird in der Vorschau angezeigt. Die Anzahl der Fragen stimmt mit dem eingereichten Quiz überein.

#### Scenario: Abgelehnte Einreichung mit sichtbarem Grund

- **Akteure:** angemeldete Lehrkraft
- **Eingaben:** eine unbekannte oder abgelaufene Kennung, oder eine Kennung einer anderen Person
  ohne gültigen Inhalt
- **Ergebnis:** die Einreichung schlägt fehl, es entsteht **kein** Eintrag, und der Grund wird
  sichtbar benannt (unbekannt, abgelaufen, Inhalt unlesbar). Kein stiller Fehler.

### Requirement: Übernahme in den Browser

Je Quiz gibt es die Handlung „In fuiz öffnen". Sie lässt in fuiz einen dauerhaften
Übernahme-Eintrag mit dem gespeicherten Inhalt entstehen und schickt die Lehrkraft auf die
zugehörige fuiz-Seite. Dort legt fuiz das Quiz mit Bildern als Kopie im Browser an. Zusätzlich ist
ein Datei-Download möglich.

#### Scenario: Ein Klick legt das Quiz in den Browser

- **Akteure:** angemeldete Lehrkraft mit einem Eintrag im Bestand
- **Eingaben:** Klick auf „In fuiz öffnen"
- **Ergebnis:** der Browser landet auf der fuiz-Seite des Eintrags und zeigt das Quiz im Editor,
  Bilder sichtbar; der Bestand in der Ablage bleibt unverändert.

#### Scenario: Übernahmekennung ist dauerhaft

- **Akteure:** angemeldete Lehrkraft, späterer Aufruf über den Verlauf
- **Eingaben:** erneuter Aufruf desselben Eintrags nach mehr als 30 Tagen
- **Ergebnis:** die Übernahme funktioniert weiterhin; sie unterliegt nicht der Frist des von fuiz
  erzeugten Teilen-Vorgangs.

### Requirement: Löschen mit Papierkorb und Verdichtung

Löschen verschiebt einen Eintrag in einen Papierkorb und lässt ihn 30 Tage wiederherstellen.
Endgültiges Löschen entfernt den Eintrag, den gespeicherten Inhalt, die zugehörige Übernahme-Kennung
in fuiz und alle Zwischenstände und verdichtet anschließend den Speicher. Nach endgültigem Löschen
ist weder über die eigene Schnittstelle noch über fuiz ein Rest abrufbar.

#### Scenario: Wiederherstellen aus dem Papierkorb

- **Akteure:** angemeldete Lehrkraft
- **Eingaben:** Eintrag löschen, am nächsten Tag wiederherstellen
- **Ergebnis:** der Eintrag steht mit unverändertem Inhalt, Größe und Datum wieder in der Liste.

#### Scenario: Endgültiges Löschen lässt nichts zurück

- **Akteure:** angemeldete Lehrkraft
- **Eingaben:** Eintrag endgültig löschen
- **Ergebnis:** kein Listeneintrag, keine Inhaltsdaten, kein Zwischenstand; die zuvor erzeugte
  Übernahme-Kennung in fuiz ist ebenfalls entfernt und der Speicher verdichtet.

### Requirement: Sichtbare Kennzahlen und Grenzen

Die Ablage zeigt je Eintrag die Größe und die Anzahl der Fragen und je Nutzer den belegten
Speicher. Wird eine Obergrenze (Größe je Quiz, Gesamtmenge je Nutzer) erreicht, wird das **vor** dem
Scheitern sichtbar angezeigt und die Einreichung mit Klartextgrund abgelehnt.

#### Scenario: Überschreitung wird vorher angezeigt

- **Akteure:** angemeldete Lehrkraft nahe der Obergrenze
- **Eingaben:** Einreichung, die die Grenze überschreiten würde
- **Ergebnis:** die Grenze und der aktuelle Stand sind sichtbar; die Einreichung wird mit Grund
  abgelehnt, ohne dass ein halber Eintrag entsteht.
