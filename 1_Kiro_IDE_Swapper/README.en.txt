==========================================================
 TOOL 1 — KIRO IDE SWAPPER
 Quick account switch on Kiro IDE via JSON (one click)
 Languages: README.txt (VI) | README.en.txt | README.zh.txt
==========================================================

FEATURES
  - Show currently logged-in Kiro IDE account (provider, expiry, profile).
  - Inject one JSON file -> kill Kiro.exe -> reopen = logged in.
  - Supports:
      * kiro-auth-token.json (dict)
      * cookie export from app.kiro.dev (array)
      * durable JSON from Tool 2 (array) + OIDC registration for refresh
  - Backup current account for later use.

REQUIREMENTS
  - Windows + Kiro IDE installed
  - Python 3.10+

INSTALL (first time)
  - Double-click CAI_DAT.bat

RUN
  - Double-click RUN.bat

HOW TO USE
  1. (Optional) Backup current account.
  2. Drag JSON to green zone, or pick file, or scan "accounts" folder -> Select -> SWAP.
  3. Tool closes Kiro -> writes token -> reopens. SAVE YOUR WORK BEFORE SWAP.

NOTES
  - Previous account auto-backed up as _previous_<time>.kiro-auth-token.json.
  - Uncheck "Reopen Kiro" if you don't want auto-launch.

GUI LANGUAGE
  Top-right dropdown: Tiếng Việt / English / 中文
