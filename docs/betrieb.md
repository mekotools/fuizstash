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
- Das neue Paket ist in GHCR zunächst **privat** und muss einmalig öffentlich
  gestellt werden; der Schnittstellenweg dafür antwortet mit 404 (die Rechte des
  Schlüssels reichen dafür nicht) — der Schalter im Browser geht.

## Ausliefern

    ./ausliefern.sh          # Quelle spiegeln, Abbild bauen, Behälter neu erzeugen
    ./ausliefern.sh pruefen  # nur Zustand ansehen

Nach einem grünen Lauf lässt sich der Stapel statt selbst zu bauen auch das
veröffentlichte Abbild ziehen (digest-genagelt, wie bei den übrigen Werkzeugen):

    image: ghcr.io/mekotools/fuizstash@sha256:<Verdauungswert>
    # build: ./quelle entfällt dann

## Notfälle

- **Seite zeigt „Verbindung zu fuiz gestört"**: Volume-Einbindung prüfen
  (`docker inspect mekotools-fuizstash`), `/gesundheit` aufrufen. Die Ablage selbst bleibt lesbar;
  nur Einreichen und Übergeben sind gesperrt.
- **Quiz im Browser fehlt nach dem Öffnen**: Übernahme-Link im Adressfeld erneut aufrufen; der
  Eintrag ist fristlos. Hilft das nicht, „Sicherung" herunterladen und in fuiz importieren.
- **Behälter neu bauen**: `cd /poolio/docker/mekotools-fuizstash && docker compose build && docker compose up -d --no-deps ablage`.
