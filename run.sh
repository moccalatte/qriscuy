#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.11}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3.11 tidak ditemukan. Set variabel PYTHON_BIN ke interpreter Python 3.11 atau install lebih dulu." >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
else
  CURRENT_VERSION="$(.venv/bin/python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
  if [[ "$CURRENT_VERSION" != "3.11" ]]; then
    echo "Virtualenv .venv menggunakan Python ${CURRENT_VERSION}. Hapus .venv dan ulangi agar memakai Python 3.11." >&2
    exit 1
  fi
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt

export QRISCUY_MODE="${QRISCUY_MODE:-${QRISCUY_MODE_DEFAULT:-FAST}}"
export UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
export UVICORN_PORT="${UVICORN_PORT:-8000}"

exec uvicorn app.api:app --host "$UVICORN_HOST" --port "$UVICORN_PORT"
