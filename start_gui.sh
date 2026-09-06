#!/usr/bin/env bash
# NetBearing Console - grafik arayuzu baslatir (tarayicida acilir).
#
# Uygulamanin tamami (paket yakalama + web sunucusu) TEK surecte, root
# olarak calisir (pkexec ile bir kez sifre sorulur). Tarayici ise AYRI ve
# YETKISIZ olarak acilir - root sürecin kendisi tarayici baslatmaz (Chrome/
# Firefox guvenlik geregi root olarak calismayi reddeder).
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

mkdir -p logs
# ONEMLI: pkexec, sudo'nun aksine calisma dizinini KORUMAZ (genelde /root
# olur) - bu yuzden buradaki her yol MUTLAK olmali, yoksa 'webapp/app.py
# bulunamadi (/root/webapp/app.py)' gibi bir hatayla sessizce basarisiz olur.
pkexec "$DIR/.venv/bin/python3" "$DIR/webapp/app.py" > "$DIR/logs/app.log" 2>&1 &
APP_PID=$!

URL="http://127.0.0.1:5757/"
for _ in $(seq 1 30); do
  if curl -s -o /dev/null "$URL" 2>/dev/null; then
    break
  fi
  sleep 0.5
done
xdg-open "$URL" >/dev/null 2>&1 &

wait "$APP_PID"
