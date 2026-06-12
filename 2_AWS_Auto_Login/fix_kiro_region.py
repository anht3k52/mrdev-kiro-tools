#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sua field region trong file JSON durable cu (us-east-1 -> eu-central-1).

Vi du:
  python fix_kiro_region.py output_json
  python fix_kiro_region.py output_json --region eu-central-1 --dry-run
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from device_code_auth import DEFAULT_KIRO_REGION


def fix_file(path: Path, region: str, dry_run: bool) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"SKIP {path.name}: {e}")
        return False
    items = data if isinstance(data, list) else [data]
    changed = False
    for item in items:
        if not isinstance(item, dict):
            continue
        old = item.get("region", "")
        if old != region:
            item["region"] = region
            changed = True
    if not changed:
        return False
    if dry_run:
        print(f"DRY {path.name}: -> region={region}")
    else:
        out = data if isinstance(data, list) else items[0]
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"FIX {path.name}: region={region}")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Batch sua region trong JSON durable Kiro.")
    ap.add_argument("folder", help="Thu muc chua *.json")
    ap.add_argument("--region", default=DEFAULT_KIRO_REGION)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.folder)
    if not root.is_dir():
        raise SystemExit(f"Khong tim thay thu muc: {root}")
    n = 0
    for p in sorted(root.glob("*.json")):
        if fix_file(p, args.region, args.dry_run):
            n += 1
    print(f"Xong: {n} file da sua (region={args.region})")


if __name__ == "__main__":
    main()
