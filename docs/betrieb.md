# Betrieb — Fuizstash

## Wo was liegt

| Sache | Ort |
| --- | --- |
| Adresse | https://fuizstash.mekotools.de (nur mit Anmeldung) |
| Stapel auf flip | `/poolio/docker/mekotools-fuizstash` (`docker-compose.yml`, `quelle/`) |
| Eigener Bestand | Docker-Volume `mekotools-fuizstash_daten` → `/daten/fuizstash.db` |
| Teilen-Speicher von fuiz | Volume `mekotools-fuiz_fuiz-web-data` → im Behälter unter `/fuiz/kv.db` |
| Umgebung | `FUIZSTASH_DATEN`, `FUIZ_KV`, `FUIZSTASH_FUIZ_BASIS`, `FUIZSTASH_FUIZ_HOSTS`, `FUIZSTASH_RAEUMEN_STUNDEN` |
| Sicherung | rsnapshot auf flip erfasst `/poolio` |

## Wie es arbeitet

- **Einreichen** liest einen Teilen-Eintrag aus `kv_share` (nur lesend) und legt eine eigene,
  vollständige Kopie in `ablage.db` ab. Danach ist der Bestand unabhängig von fuiz.
- **Übernahme** schreibt einen eigenen, fristlosen Eintrag in `kv_share` und leitet auf
  `https://fuiz.mekotools.de/share/<kennung>`. fuiz legt das Quiz daraufhin als Kopie im Browser an.
  Der Eintrag bleibt dauerhaft und wird bei erneuter Neueinreichung desselben Titels aktualisiert.
- **Löschen** verschiebt in den Papierkorb (30 Tage). Endgültiges Löschen entfernt den Eintrag, den
  eigenen Übernahme-Eintrag im fuiz-Speicher und die zugehörigen Verlaufszeilen, danach `VACUUM`.
- **Papierkorb-Frist** wird im Prozess alle 6 Stunden geprüft (`FUIZSTASH_RAEUMEN_STUNDEN`).
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

      TINYAUTH_APPS_FUIZSTASH_CONFIG_DOMAIN=fuizstash.mekotools.de
      TINYAUTH_APPS_FUIZSTASH_OAUTH_WHITELIST=<erlaubte Anmeldeadresse>

  Weitere Lehrkräfte bekommen je eine weitere Zeile (`_OAUTH_WHITELIST` ist eine Liste).
  Danach **nur** den Sperrdienst neu erzeugen: `docker compose up -d --no-deps tinyauth` — ein
  Neubau des ganzen Stapels hat früher schon andere Dienste stillgelegt.

## Bau-Auftrag (Forgejo-Läufer)

Der Läufer `flip-01` hängt an der Organisation `mekotools` und läuft als Stapel
`/poolio/docker/forgejo-runner` auf flip. Er baut aus der Quelle ein Abbild und
schiebt es nach `ghcr.io/mekotools/fuizstash`. Ausgelöst bei jedem Push auf `main`
und über `.forgejo/workflows/abbild.yml`.

Besonderheiten dieses Aufbaus (nicht annehmen, nachlesen):

- Der Läufer spricht Forgejo **intern** an (`http://forgejo-server:3000`): von flip
  aus ist `git.n0ne.de` über den VPS nicht erreichbar.
- Arbeitsabbild ist `docker:27-cli` — es hat docker, buildx und git, aber **kein
  bash und kein node**. Deshalb steht im Auftrag `shell: sh`, und die Quelle wird
  per `git clone` geholt statt mit `actions/checkout` (das braucht node).
- Der Docker-Sockel ist in den Auftrag gereicht; `docker build` läuft also auf dem
  Daemon des Wirts.
- Anmeldung an GHCR über die Organisations-Geheimnisse `GHCR_TOKEN` und
  `GHCR_BENUTZER` (Forgejo, Einstellungen → Geheimnisse).
- **Erstanlage und Sichtbarkeit (nachgemessen):** ein Paket, das die Befehlzeile
  oder ein fremder Läufer zum *ersten* Mal schiebt, entsteht in GHCR **privat** —
  und privat lässt es sich über die Schnittstelle nicht umstellen (es gibt keinen
  Eintrag dafür; `PATCH`/`PUT` auf `/orgs/mekotools/packages/container/<paket>`
  antworten mit 404, auch bei längst öffentlichen Paketen). Öffentlich wird es nur,
  wenn die **Erstanlage aus dem Arbeitsablauf dieses Repos** kommt:
  `.github/workflows/erstanlage.yml` (nur von Hand auslösbar) baut und schiebt das
  Abbild — danach ist das Paket **öffentlich**, anonym ziehbar und mit
  `mekotools/fuizstash` verknüpft. Ein anschließender Push des Forgejo-Läufers
  ändert das nicht mehr (nachgemessen: Lauf 8 danach, Sichtbarkeit weiter
  öffentlich). Der Anker `org.opencontainers.image.source` im Dockerfile hält die
  Verknüpfung.
- **Nicht `docker push --all-tags` verwenden:** das schiebt jede im Wirt liegende
  Marke desselben Namens mit, auch veraltete aus früheren Läufen. Nur die beiden
  eigenen Marken schieben (Übergabe-Kennung und `latest`).

## Ausliefern

    ./ausliefern.sh          # Quelle spiegeln (Rückfallweg), Abbild ziehen, Behälter neu erzeugen
    ./ausliefern.sh pruefen  # Zustand, laufendes Abbild, Gesundheit, Außensicht

Der Stapel **zieht** sein Abbild seit 07.10.2026 aus GHCR, festgenagelt auf den
Verdauungswert (`image: ghcr.io/mekotools/fuizstash@sha256:…` in
`docker-compose.yml`). Der Wirt baut nicht mehr selbst und braucht keine
Zugangsdaten, weil das Paket öffentlich ist (nachgemessen: `DOCKER_CONFIG` auf ein
leeres Verzeichnis gesetzt und trotzdem gezogen).

Neuen Stand ausliefern:

1. Push auf `main` → der Forgejo-Läufer baut und schiebt; der Lauf muss grün sein.
2. Verdauungswert des neuen Standes holen (Paketansicht auf GitHub oder
   `docker manifest inspect ghcr.io/mekotools/fuizstash:latest`).
3. Wert in `docker-compose.yml` eintragen, `./ausliefern.sh` laufen lassen.

**Zurückrollen:** alten Verdauungswert eintragen und erneut ausliefern.
**Rückfallweg ohne Registrierung:** in `docker-compose.yml` die beiden
`build: ./quelle`-Zeilen einkommentieren und die `image:`-Zeile mit dem Wert
entfernen, dann `docker compose build && docker compose up -d --no-deps fuizstash`.

## Notfälle

- **Seite zeigt „Verbindung zu fuiz gestört"**: Volume-Einbindung prüfen
  (`docker inspect mekotools-fuizstash`), `/gesundheit` aufrufen. Die Ablage selbst bleibt lesbar;
  nur Einreichen und Übergeben sind gesperrt.
- **Quiz im Browser fehlt nach dem Öffnen**: Übernahme-Link im Adressfeld erneut aufrufen; der
  Eintrag ist fristlos. Hilft das nicht, „Sicherung" herunterladen und in fuiz importieren.
- **Behälter neu bauen (Rückfallweg ohne Registrierung)**: in `docker-compose.yml` die
  `build: ./quelle`-Zeilen einkommentieren und die `image:`-Zeile mit dem Verdauungswert entfernen,
  dann `cd /poolio/docker/mekotools-fuizstash && docker compose build && docker compose up -d --no-deps fuizstash`.
