#!/usr/bin/env bash
# Levanta el servidor del juego y un túnel público para probarlo en el móvil.
# Uso:  bash web/servir_movil.sh
# Imprime la IP de la red local y la URL pública del túnel.

set -u
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PY="$RAIZ/venv/bin/python"
BIN="$HOME/.local/bin/cloudflared"
LOG_SRV="$RAIZ/web/servidor.log"
LOG_TUN="$RAIZ/web/tunel.log"

# 1) Servidor del juego en el puerto 8000 (sin COEP, recursos locales incluidos).
if ! curl -sf -o /dev/null http://localhost:8000/; then
    nohup "$PY" "$RAIZ/servidor_web.py" "$RAIZ/juego_lleva/build/web" > "$LOG_SRV" 2>&1 &
    sleep 2
fi

LOCAL_IP="$(ip -4 addr show 2>/dev/null | grep -oP 'inet \K[0-9.]+' | grep -v '^127\.' | head -1)"
echo "Servidor local:  http://localhost:8000/  (en el movil de la misma red: http://${LOCAL_IP:-<ip-pc>}:8000/)"

# 2) Túnel público (funciona con datos móviles, sin depender de la red wifi).
if ! pgrep -x cloudflared >/dev/null 2>&1; then
    if [ ! -x "$BIN" ]; then
        mkdir -p "$HOME/.local/bin"
        curl -sL -o "$BIN" \
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        chmod +x "$BIN"
    fi
    nohup "$BIN" tunnel --url http://localhost:8000 --no-autoupdate > "$LOG_TUN" 2>&1 &
    sleep 10
fi

echo "Túnel público:"
grep -o "https://[a-z0-9-]*\.trycloudflare\.com" "$LOG_TUN" | head -1
echo
echo "Abre esa URL (o la local) en el celular y haz un toque para arrancar el audio."
echo "Si cambia la URL al relanzar, mira $LOG_TUN"