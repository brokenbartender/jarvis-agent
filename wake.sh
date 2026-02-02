#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$ROOT_DIR/.venv/Scripts/activate"

# Start server if not running
if ! python -m jarvis.cli send "ping" >/dev/null 2>&1; then
  python -m jarvis.cli serve --daemon
  sleep 1
fi

# Start UI
python -m jarvis.cli ui --open
