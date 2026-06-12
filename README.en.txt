==========================================================
 TOOL 3 — 9ROUTER INJECTOR (Fix 403 error)
 Languages: README.txt (VI) | README.en.txt | README.zh.txt
==========================================================

FEATURES
  - Drag & drop (or pick) durable JSON / cookie export files:
      1. Parse profileArn + tokens from file
      2. Match the right Kiro connection in 9router (by email / token / IDC)
         - Match found  -> UPDATE profileArn (fix 403)
         - No match     -> CREATE new connection (no manual login in 9router)
      3. (optional) Live verify via ListAvailableProfiles API
      4. AUTO-RESTART 9router (stop -> write DB -> start)
  - Connection list: OK / 403 (missing profileArn) / ~1h (cookie-only).

REQUIREMENTS
  - Windows + 9router installed (run 9router once to create the DB)
  - Python 3.10+ (check "Add to PATH" when installing Python)

INSTALL (first time only)
  - Double-click CAI_DAT.bat

RUN
  - Double-click RUN.bat

HOW TO USE
  1. Drag JSON files (from Tool 2 or cookie export) into the green zone.
  2. Review the plan (update / create) -> click Continue.
  3. Tool writes DB + restarts 9router. Wait a few seconds for quota.

INPUT JSON TYPES
  - Durable JSON (Tool 2): has refresh_token -> long-lived, 9router auto-refreshes.
  - Cookie export (access + ProfileArn only): works ~1 hour only.

NOTES
  - Many IAM users in the same IDC share one profileArn (same Kiro quota) but
    different tokens — tool imports each account separately by email.
  - If 403 returns later, drag the JSON file again to re-inject.

GUI LANGUAGE
  Top-right dropdown: Tiếng Việt / English / 中文
