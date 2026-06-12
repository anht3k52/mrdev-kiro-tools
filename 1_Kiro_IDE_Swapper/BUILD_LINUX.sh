#!/usr/bin/env bash
# Build Tool 1 — Kiro IDE Swapper (Linux binary)
# Requires: python3, python3-tk, gcc (hoac build-essential)
#   Debian/Ubuntu: sudo apt install python3 python3-tk python3-dev python3-pip build-essential
set -euo pipefail
cd "$(dirname "$0")"

PY="${PY:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "LOI: khong tim thay python3"; exit 1; }

echo "=== Build Linux binary (Nuitka) — Tool 1 Kiro IDE Swapper ==="
"$PY" -m pip install -q nuitka zstandard customtkinter psutil tkinterdnd2 2>/dev/null || true

"$PY" -m nuitka \
  --onefile \
  --assume-yes-for-downloads \
  --lto=no \
  --enable-plugin=tk-inter \
  --include-package-data=customtkinter \
  --include-package-data=tkinterdnd2 \
  --output-dir=_build \
  --output-filename=Tool1_Kiro_IDE_Swapper \
  swap_ide_gui.py

chmod +x "_build/Tool1_Kiro_IDE_Swapper"
echo ""
echo "=== Done: _build/Tool1_Kiro_IDE_Swapper ==="
