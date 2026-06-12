#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCPD_DIR="${MCPD_DIR:-$HOME/mozilla-hackathon/mcpd}"
MCPD_BIN="${MCPD_BIN:-$MCPD_DIR/mcpd}"
CONFIG="$ROOT/mcpd/.mcpd.toml"

log() { echo "[setup-mcpd] $*"; }

if [[ ! -x "$MCPD_BIN" ]]; then
  log "mcpd binary not found at $MCPD_BIN"
  log "Install mcpd in WSL first (see Mozilla mcpd docs)."
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  log "Missing config: $CONFIG"
  exit 1
fi

log "Using config: $CONFIG"
log "Servers configured:"
grep 'name = ' "$CONFIG" || true

log "Done. Start with: d:\\proj\\start-mcpd.ps1"
