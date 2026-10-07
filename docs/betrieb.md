# Betrieb — Quizablage

## Wo was liegt

| Sache | Ort |
| --- | --- |
| Adresse | https://quizablage.mekotools.de (nur mit Anmeldung) |
| Stapel auf flip | `/poolio/docker/mekotools-quizablage` (`docker-compose.yml`, `quelle/`) |
| Eigener Bestand | Docker-Volume `mekotools-quizablage_ablage-daten` → `/daten/ablage.db` |
| Teilen-Speicher von fuiz | Volume `mekotools-fuiz_fuiz-web-data` → im Behälter unter `/fuiz/kv.db` |
| Umgebung | `ABLAGE_DATEN`, `FUIZ_KV`, `ABLAGE_FUIZ_BASIS`, `ABLAGE_FUIZ_HOSTS`, `ABLAGE_RAEUMEN_STUNDEN` |
| Sicherung | rsnapshot auf flip erfasst `/poolio` |

## Wie es arbeitet

- **Einreichen** liest einen Teilen-Eintrag aus `kv_share` (nur lesend) und legt eine eigene,
  vollständige Kopie in `ablage.db` ab. Danach ist der Bestand unabhängig von fuiz.
- **Übernahme** schreibt einen eigenen, fristlosen Eintrag in `kv_share` und leitet auf
  `https://fuiz.mekotools.de/share/<kennung>`. fuiz legt das Quiz daraufhin als Kopie im Browser an.
  Der Eintrag bleibt dauerhaft und wird bei erneuter Neueinreichung desselben Titels aktualisiert.
- **Löschen** verschiebt in den Papierkorb (30 Tage). Endgültiges Löschen entfernt den Eintrag, den
  eigenen Übernahme-Eintrag im fuiz-Speicher und die zugehörigen Verlaufszeilen, danach `VACUUM`.
- **Papierkorb-Frist** wird im Prozess alle 6 Stunden geprüft (`ABLAGE_RAEUMEN_STUNDEN`).
- **Kopplung** wird beim Start und danach höchstens alle 30 Sekunden geprüft (Probeeintrag mit
  kurzer Frist, sofort wieder entfernt). Fehlt die Tabelle, zeigt jede Seite einen Betriebsvermerk.

## Bekannte Kopplungen und Grenzen

- Der Behälter läuft als **root**, weil der fuiz-Datenträger root gehört (Bild `USER ablage` wird
  in `docker-compose.yml` überschrieben). Die Anwendung öffnet ausschließlich `kv.db`, Tabelle
  `kv_share`, und fasst `fuiz.db` nie an; fremde Zeilen werden nie geändert oder gelöscht.
- Ändert fuiz sein Speicherformat (Tabellen- oder Spaltennamen), bricht die Kopplung. Sie wird
  sichtbar gemeldet, und der Rückfallweg bleibt: Eintrag herunterladen (Sicherung) und in fuiz über
  „Import" einlesen.
- Einrichtungsregel der Sperre (in `/poolio/docker/mekotools-auth/.env`):

      TINYAUTH_APPS_QUIZABLAGE_CONFIG_DOMAIN=quizablage.mekotools.de
      TINYAUTH_APPS_QUIZABLAGE_OAUTH_WHITELIST=<erlaubte Anmeldeadresse>

  Weitere Lehrkräfte bekommen je eine weitere Zeile (`_OAUTH_WHITELIST` ist eine Liste).
  Danach **nur** den Sperrdienst neu erzeugen: `docker compose up -d --no-deps tinyauth` — ein
  Neubau des ganzen Stapels hat früher schon andere Dienste stillgelegt.

## Ausliefern

    ./ausliefern.sh          # Quelle spiegeln, Abbild bauen, Behälter neu erzeugen
    ./ausliefern.sh pruefen  # nur Zustand ansehen

## Notfälle

- **Seite zeigt „Verbindung zu fuiz gestört"**: Volume-Einbindung prüfen
  (`docker inspect mekotools-quizablage`), `/gesundheit` aufrufen. Die Ablage selbst bleibt lesbar;
  nur Einreichen und Übergeben sind gesperrt.
- **Quiz im Browser fehlt nach dem Öffnen**: Übernahme-Link im Adressfeld erneut aufrufen; der
  Eintrag ist fristlos. Hilft das nicht, „Sicherung" herunterladen und in fuiz importieren.
- **Behälter neu bauen**: `cd /poolio/docker/mekotools-quizablage && docker compose build && docker compose up -d --no-deps ablage`.
