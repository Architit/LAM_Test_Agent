#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TPL="$ROOT/deploy/public/Caddyfile.tpl"
OUT_DIR="$ROOT/.gateway/public"
OUT_CFG="$OUT_DIR/Caddyfile"

DOMAIN="${DOMAIN:-radriloniuma.local}"
OS_SUBDOMAIN="${OS_SUBDOMAIN:-os.${DOMAIN}}"
PORT="${PORT:-8099}"
RUN_CADDY="${RUN_CADDY:-0}"

usage() {
  cat <<'EOF'
Usage:
  scripts/deploy_public_site.sh [--domain DOMAIN] [--os-subdomain HOST] [--port PORT] [--run-caddy]

Example:
  DOMAIN=radriloniuma.example.com OS_SUBDOMAIN=os.radriloniuma.example.com scripts/deploy_public_site.sh --run-caddy
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2;;
    --os-subdomain) OS_SUBDOMAIN="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --run-caddy) RUN_CADDY=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

mkdir -p "$OUT_DIR"
sed \
  -e "s#{{DOMAIN}}#${DOMAIN}#g" \
  -e "s#{{OS_SUBDOMAIN}}#${OS_SUBDOMAIN}#g" \
  -e "s#{{PORT}}#${PORT}#g" \
  "$TPL" > "$OUT_CFG"

IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
cat <<EOF
[public-site] config rendered: $OUT_CFG
[public-site] domain:           $DOMAIN
[public-site] os subdomain:     $OS_SUBDOMAIN
[public-site] upstream:         http://127.0.0.1:${PORT}
[public-site] dns A records:
  $DOMAIN -> ${IP:-<server_ip>}
  $OS_SUBDOMAIN -> ${IP:-<server_ip>}
EOF

if [[ "$RUN_CADDY" == "1" ]]; then
  if ! command -v caddy >/dev/null 2>&1; then
    echo "[public-site] caddy not found; install caddy first." >&2
    exit 1
  fi
  echo "[public-site] starting caddy..."
  exec caddy run --config "$OUT_CFG" --adapter caddyfile
fi
