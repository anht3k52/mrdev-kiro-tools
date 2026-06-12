# MRDev Kiro 工具集

三个 Python 工具，用于管理 Kiro 账号（AWS IAM Identity Center + 9router + Kiro IDE）。

**语言：** [Tiếng Việt](README.md) · [English](README.en.md) · **中文**

| 工具 | 目录 | 功能 |
|------|------|------|
| **工具1** | `1_Kiro_IDE_Swapper/` | 用 JSON 文件切换 Kiro IDE 账号 |
| **工具2** | `2_AWS_Auto_Login/` | 自动 IAM 登录 → 导出持久 JSON |
| **工具3** | *(根目录)* | 将 JSON 注入 9router（修复 403） |

## 环境要求

- Python 3.10+
- Windows（可打包 `.exe`），macOS/Linux（附带 `.sh` 脚本）
- 工具2：Playwright + Chromium（在 `2_AWS_Auto_Login/` 运行 `CAI_DAT.bat`）

## 快速开始（Windows）

```bat
rem 工具1 — Kiro IDE 切换器
cd 1_Kiro_IDE_Swapper
CAI_DAT.bat
RUN.bat

rem 工具2 — AWS 自动登录 → 持久 JSON
cd 2_AWS_Auto_Login
CAI_DAT.bat
RUN.bat

rem 工具3 — 9router 注入器
cd ..
CAI_DAT.bat
RUN.bat
```

## 界面语言

三个工具右上角均有 **语言下拉菜单**：**Tiếng Việt / English / 中文**。

## 区域设置（工具2）

两个 **不同** 的区域：

- **OIDC 区域（IAM 登录）：** 通常为 `us-east-1`（须与 IAM Identity Center 一致）
- **Kiro 区域（9router 额度）：** 欧盟工作区用 `eu-central-1`

## 使用流程

1. **工具2** — 登录 IAM 账号 → 生成 `output_json/kiro-durable-*.json`
2. **工具3** — 拖入 JSON 到 9router → 修复 403 / 创建连接 → 重启 9router
3. **工具1** — 在 Kiro IDE 桌面端切换账号

## 各工具说明

| 工具 | 越南语 | English | 中文 |
|------|--------|---------|------|
| 工具1 | `1_Kiro_IDE_Swapper/README.txt` | `README.en.txt` | `README.zh.txt` |
| 工具2 | `2_AWS_Auto_Login/README.txt` | `README.en.txt` | `README.zh.txt` |
| 工具3 | `README.txt` | `README.en.txt` | `README.zh.txt` |

## 技术文档

见 [README_SYSTEM.md](README_SYSTEM.md) — JSON 结构、9router SQLite、API 验证。

## 安全提示

- **不要** 提交含 `refresh_token`、`client_secret` 或账号列表的 JSON
- `266mrdev/`、`output_json/` 已在 `.gitignore` 中
