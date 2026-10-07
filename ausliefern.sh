#!/usr/bin/env bash
# Auslieferung der Fuizstash auf flip.
#   ./ausliefern.sh            — Quelle spiegeln, Abbild ziehen, Behälter neu erzeugen
#   ./ausliefern.sh pruefen    — nur den Zustand ansehen
#
# Das Abbild kommt seit dem 07.10.2026 aus der eigenen CI (GHCR, digest-genagelt,
# gebaut vom Forgejo-Läufer). Der Wirt baut nicht mehr selbst; er zieht nur noch.
set -euo pipefail

HOST="${FUIZSTASH_HOST:-root@192.168.1.20}"
SPRUNG="${FUIZSTASH_SPRUNG:--J n0ne}"
SCHLUESSEL="${FUIZSTASH_SCHLUESSEL:-/opt/data/.ssh/id_rsa}"
ZIEL=/poolio/docker/mekotools-fuizstash
HIER="$(cd "$(dirname "$0")" && pwd)"

ssh_() { ssh -i "$SCHLUESSEL" -o BatchMode=yes -o ConnectTimeout=15 $SPRUNG "$HOST" "$@"; }

if [ "${1:-}" = "pruefen" ]; then
  ssh_ "docker ps --filter name=mekotools-fuizstash --format '{{.Names}} | {{.Image}} | {{.Status}}'"
  ssh_ "docker inspect mekotools-fuizstash --format 'laufendes Abbild: {{index .Config.Image}}{{println}}gestartet: {{.State.StartedAt}}'"
  ssh_ "docker exec mekotools-fuizstash python -c \"import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/gesundheit',timeout=5).read().decode())\" || true"
  ssh_ "curl -s -o /dev/null -w 'aussen: HTTP %{http_code}\\n' https://fuizstash.mekotools.de/ablage || true"
  exit 0
fi

echo "== Quelle spiegeln (nur Rückfallweg — der Betrieb zieht das Abbild) =="
ssh_ "rm -rf $ZIEL/quelle && mkdir -p $ZIEL/quelle"
tar --exclude=.venv --exclude=.git --exclude=__pycache__ --exclude=.pytest_cache \
    -czf - -C "$HIER" app tests Dockerfile requirements.txt pytest.ini \
  | ssh -i "$SCHLUESSEL" -o BatchMode=yes -o ConnectTimeout=15 $SPRUNG "$HOST" "tar -xzf - -C $ZIEL/quelle"
scp -i "$SCHLUESSEL" -o BatchMode=yes $SPRUNG "$HIER/docker-compose.yml" \
  "$HOST:$ZIEL/docker-compose.yml"

echo "== Abbild ziehen (festgenagelt, anonym) =="
ssh_ "cd $ZIEL && docker compose pull fuizstash"
echo "== Behälter neu erzeugen (nur dieser Dienst) =="
ssh_ "cd $ZIEL && docker compose up -d --no-deps fuizstash"
sleep 4
ssh_ "cd $ZIEL && docker compose ps"
ssh_ "docker inspect mekotools-fuizstash --format 'laufendes Abbild: {{index .Config.Image}}'"
ssh_ "docker exec mekotools-fuizstash python -c \"import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/gesundheit',timeout=5).read().decode())\"" || true
echo
