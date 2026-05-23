#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p certs
if [ ! -f certs/cert.pem ] || [ ! -f certs/key.pem ]; then
  openssl req \
    -x509 \
    -newkey rsa:2048 \
    -nodes \
    -keyout certs/key.pem \
    -out certs/cert.pem \
    -days 365 \
    -subj "/CN=remote.vdi.mipt.ru" \
    -addext "subjectAltName=DNS:remote.vdi.mipt.ru"
fi

if [ -f app.pid ]; then
  kill "$(cat app.pid)" 2>/dev/null || true
fi

MODEL_DIR="${MODEL_DIR:-data/models/item2vec_mpd_gensim}" \
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://remote.vdi.mipt.ru:56183}" \
GITHUB_URL="${GITHUB_URL:-https://github.com/your-username/PlaylistAnalyze}" \
CORS_ORIGINS="${CORS_ORIGINS:-https://remote.vdi.mipt.ru:56183}" \
REQUIRE_MODEL_ON_STARTUP="${REQUIRE_MODEL_ON_STARTUP:-1}" \
nohup .venv/bin/uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-3389}" \
  --ssl-keyfile certs/key.pem \
  --ssl-certfile certs/cert.pem \
  > server.log 2>&1 &

echo "$!" > app.pid
echo "PlaylistAnalyze started with pid $(cat app.pid)"
