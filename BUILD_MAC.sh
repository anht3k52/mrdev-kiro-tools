#!/usr/bin/env bash
# Build Tool 3 — 9router Injector (.app) on macOS
# Requires: python3, Xcode CLT (xcode-select --install)
#   pip install nuitka zstandard customtkinter psutil tkinterdnd2
set -euo pipefail
cd "$(dirname "$0")"

PY="${PY:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "LOI: khong tim thay python3"; exit 1; }

echo "=== Build macOS app (Nuitka) — Tool 3 9router Injector ==="
"$PY" -m pip install -q nuitka zstandard customtkinter psutil tkinterdnd2 2>/dev/null || true

"$PY" -m nuitka \
  --onefile \
  --macos-create-app-bundle \
  --assume-yes-for-downloads \
  --lto=no \
  --enable-plugin=tk-inter \
  --include-package-data=customtkinter \
  --include-package-data=tkinterdnd2 \
  --output-dir=_build \
  --output-filename=Tool3_9router_Injector \
  inject_9router_gui.py

echo ""
echo "=== Done: _build/Tool3_9router_Injector.app ==="
