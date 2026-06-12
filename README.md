# MRDev Kiro Tools

Bộ 3 tool Python hỗ trợ quản lý account Kiro (AWS IAM Identity Center + 9router + Kiro IDE).

| Tool | Thư mục | Chức năng |
|------|---------|-----------|
| **Tool 1** | `1_Kiro_IDE_Swapper/` | Swap account Kiro IDE bằng file JSON |
| **Tool 2** | `2_AWS_Auto_Login/` | Auto login IAM → xuất JSON durable |
| **Tool 3** | *(root)* | Inject JSON vào 9router (fix 403) |

## Yêu cầu

- Python 3.10+
- Windows (build `.exe`), macOS/Linux (script `.sh` có sẵn)
- Tool 2: Playwright + Chromium (`CAI_DAT.bat` trong `2_AWS_Auto_Login/`)

## Chạy nhanh (Windows)

```bat
rem Tool 1 — Kiro IDE Swapper
cd 1_Kiro_IDE_Swapper
CAI_DAT.bat
RUN.bat

rem Tool 2 — AWS Auto Login → JSON durable
cd 2_AWS_Auto_Login
CAI_DAT.bat
RUN.bat

rem Tool 3 — 9router Injector
cd ..
CAI_DAT.bat
RUN.bat
```

## Region (Tool 2)

Hai region **khác nhau**:

- **OIDC region (login IAM):** thường `us-east-1` (trùng IAM Identity Center)
- **Kiro region (9router quota):** `eu-central-1` cho workspace EU

## Build

| Tool | Windows | macOS | Linux |
|------|---------|-------|-------|
| Tool 1 | `1_Kiro_IDE_Swapper/BUILD_EXE.bat` | `BUILD_MAC.sh` | `BUILD_LINUX.sh` |
| Tool 2 | `2_AWS_Auto_Login/BUILD_EXE.bat` | — | — |
| Tool 3 | `BUILD_EXE.bat` | `BUILD_MAC.sh` | `BUILD_LINUX.sh` |

## Luồng sử dụng

1. **Tool 2** — login account IAM → `output_json/kiro-durable-*.json`
2. **Tool 3** — kéo JSON vào 9router → fix 403 / tạo connection → restart 9router
3. **Tool 1** — swap account trên Kiro IDE desktop

## Tài liệu kỹ thuật

Xem [README_SYSTEM.md](README_SYSTEM.md) — schema JSON, SQLite 9router, API verify.

## Lưu ý bảo mật

- **Không** commit file JSON chứa `refresh_token`, `client_secret`, account list
- Folder `266mrdev/`, `output_json/` đã nằm trong `.gitignore`
