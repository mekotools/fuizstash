#!/usr/bin/env bash
# Auslieferung der Quizablage auf flip.
#   ./ausliefern.sh            — Quelle spiegeln, Abbild bauen, Behälter neu erzeugen
#   ./ausliefern.sh pruefen    — nur den Zustand ansehen
set -euo pipefail

HOST="${ABLAGE_HOST:-root@192.168.1.20}"
SPRUNG="${ABLAGE_SPRUNG:--J n0ne}"
SCHLUESSEL="${ABLAGE_SCHLUESSEL:-/opt/data/.ssh/id_rsa}"
ZIEL=/poolio/docker/mekotools-quizablage
HIER="$(cd "$(dirname "$0")" && pwd)"

ssh_() { ssh -i "$SCHLUESSEL" -o BatchMode=yes -o ConnectTimeout=15 $SPRUNG "$HOST" "$@"; }

if [ "${1:-}" = "pruefen" ]; then
  ssh_ "docker ps --filter name=mekotools-quizablage --format '{{.Names}} {{.Status}}'"
  ssh_ "curl -s -o /dev/null -w 'innen: HTTP %{http_code}\n' http://127.0.0.1:8000/gesundheit || true"
  ssh_ "curl -s -o /dev/null -w 'aussen: HTTP %{http_code}\n' https://quizablage.mekotools.de/ablage || true"
  exit 0
fi

echo "== Quelle spiegeln =="
ssh_ "rm -rf $ZIEL/quelle && mkdir -p $ZIEL/quelle"
tar --exclude=.venv --exclude=.git --exclude=__pycache__ --exclude=.pytest_cache \
    -czf - -C "$HIER" app tests Dockerfile requirements.txt pytest.ini \
  | ssh -i "$SCHLUESSEL" -o BatchMode=yes -o ConnectTimeout=15 $SPRUNG "$HOST" "tar -xzf - -C $ZIEL/quelle"
scp -i "$SCHLUESSEL" -o BatchMode=yes $SPRUNG "$HIER/docker-compose.yml" \
  "$HOST:$ZIEL/docker-compose.yml"

echo "== Abbild bauen =="
ssh_ "cd $ZIEL && docker compose build"
echo "== Behälter neu erzeugen (nur dieser Dienst) =="
ssh_ "cd $ZIEL && docker compose up -d --no-deps ablage"
sleep 3
ssh_ "cd $ZIEL && docker compose ps"
ssh_ "curl -s http://127.0.0.1:8000/gesundheit" || true
echo
