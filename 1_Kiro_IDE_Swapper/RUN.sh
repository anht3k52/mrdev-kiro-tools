#!/usr/bin/env bash
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  python3 swap_ide_gui.py
elif command -v python >/dev/null 2>&1; then
  python swap_ide_gui.py
else
  echo "Python not found. Run: pip install -r requirements.txt"
  exit 1
fi
