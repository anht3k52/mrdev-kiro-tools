#!/usr/bin/env bash
# Build Tool 1 — Kiro IDE Swapper (.app) on macOS
# Requires: python3, Xcode CLT (xcode-select --install)
set -euo pipefail
cd "$(dirname "$0")"

PY="${PY:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "LOI: khong tim thay python3"; exit 1; }

echo "=== Build macOS app (Nuitka) — Tool 1 Kiro IDE Swapper ==="
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
  --output-filename=Tool1_Kiro_IDE_Swapper \
  swap_ide_gui.py

echo ""
echo "=== Done: _build/Tool1_Kiro_IDE_Swapper.app ==="
