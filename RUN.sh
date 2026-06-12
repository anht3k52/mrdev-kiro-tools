#!/usr/bin/env bash
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  python3 inject_9router_gui.py
elif command -v python >/dev/null 2>&1; then
  python inject_9router_gui.py
else
  echo "Python not found. Run: pip install -r requirements.txt"
  exit 1
fi
