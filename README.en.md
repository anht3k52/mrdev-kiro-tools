# MRDev Kiro Tools

Three Python tools for managing Kiro accounts (AWS IAM Identity Center + 9router + Kiro IDE).

**Languages:** [Tiếng Việt](README.md) · **English** · [中文](README.zh.md)

| Tool | Folder | Purpose |
|------|--------|---------|
| **Tool 1** | `1_Kiro_IDE_Swapper/` | Swap Kiro IDE account via JSON file |
| **Tool 2** | `2_AWS_Auto_Login/` | Auto IAM login → export durable JSON |
| **Tool 3** | *(root)* | Inject JSON into 9router (fix 403) |

## Requirements

- Python 3.10+
- Windows (`.exe` build), macOS/Linux (`.sh` scripts included)
- Tool 2: Playwright + Chromium (`CAI_DAT.bat` in `2_AWS_Auto_Login/`)

## Quick start (Windows)

```bat
rem Tool 1 — Kiro IDE Swapper
cd 1_Kiro_IDE_Swapper
CAI_DAT.bat
RUN.bat

rem Tool 2 — AWS Auto Login → durable JSON
cd 2_AWS_Auto_Login
CAI_DAT.bat
RUN.bat

rem Tool 3 — 9router Injector
cd ..
CAI_DAT.bat
RUN.bat
```

## GUI language

All three tools have a **language dropdown** (top-right): **Tiếng Việt / English / 中文**.

## Regions (Tool 2)

Two **different** regions:

- **OIDC region (IAM login):** usually `us-east-1` (must match IAM Identity Center)
- **Kiro region (9router quota):** `eu-central-1` for EU workspace

## Workflow

1. **Tool 2** — login IAM accounts → `output_json/kiro-durable-*.json`
2. **Tool 3** — drag JSON into 9router → fix 403 / create connections → restart 9router
3. **Tool 1** — swap account on Kiro IDE desktop

## Per-tool docs

| Tool | Vietnamese | English | 中文 |
|------|------------|---------|------|
| Tool 1 | `1_Kiro_IDE_Swapper/README.txt` | `README.en.txt` | `README.zh.txt` |
| Tool 2 | `2_AWS_Auto_Login/README.txt` | `README.en.txt` | `README.zh.txt` |
| Tool 3 | `README.txt` | `README.en.txt` | `README.zh.txt` |

## Technical reference

See [README_SYSTEM.md](README_SYSTEM.md) — JSON schema, 9router SQLite, API verify.

## Security

- **Do not** commit JSON files with `refresh_token`, `client_secret`, or account lists
- `266mrdev/`, `output_json/` are in `.gitignore`
