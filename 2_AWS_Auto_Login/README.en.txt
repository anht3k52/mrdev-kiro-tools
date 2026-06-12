==========================================================
 TOOL 2 — AWS AUTO LOGIN -> durable JSON
 Languages: README.txt (VI) | README.en.txt | README.zh.txt
==========================================================

FEATURES
  - Read account file (Excel/txt) -> open clean Chrome (Playwright)
  - Auto login AWS IAM Identity Center:
      * New account (first login) -> auto change password (configurable)
      * Already changed password  -> normal login
    (Tool auto-detects — no mode switch needed)
  - Export full DURABLE JSON (refresh_token + client_id + secret + profileArn).
    Batch + multi-threaded.
  - Does NOT touch 9router (use Tool 3 for that).

REQUIREMENTS
  - Windows + Python 3.10+

INSTALL (first time)
  - Double-click CAI_DAT.bat (installs libs + Chromium ~150MB)

RUN
  - Double-click RUN.bat

ACCOUNT FILE FORMAT
  - Excel (.xlsx): column A = Email/Username, B = Password
  - Text (.txt): one line per account "email:password" or "email|password"
  - Tool writes new password + result back to the file after run.

HOW TO USE
  1. Choose account file.
  2. Choose JSON output folder (default: output_json).
  3. Set parallel threads (3-5 recommended), new password, IDC start URL.
     If password already changed: tick "Override file password" + enter current password.
  4. OIDC region: us-east-1 (IAM). Kiro region: eu-central-1 (EU workspace).
  5. Click START AUTO LOGIN. Watch the log.

REGIONS
  - OIDC region = IAM login (usually us-east-1)
  - Kiro region = Q API quota (eu-central-1 for EU)

NOTES
  - Accounts without MFA/2FA login fully automatically.
  - CAPTCHA -> turn off Headless and solve manually.

GUI LANGUAGE
  Top-right dropdown: Tiếng Việt / English / 中文
