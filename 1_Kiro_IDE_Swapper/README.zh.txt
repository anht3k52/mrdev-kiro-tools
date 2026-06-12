==========================================================
 工具1 — KIRO IDE 切换器
 用 JSON 一键快速切换 Kiro IDE 账号
 语言: README.txt (越) | README.en.txt | README.zh.txt
==========================================================

功能
  - 显示当前 Kiro IDE 登录账号（提供商、过期时间、profile）。
  - 注入一个 JSON -> 结束 Kiro.exe -> 重新打开即已登录。
  - 支持：
      * kiro-auth-token.json（字典）
      * 从 app.kiro.dev 导出的 cookie（数组）
      * 工具2 的持久 JSON（数组）+ OIDC 注册以支持刷新
  - 备份当前账号供日后使用。

环境要求
  - Windows + 已安装 Kiro IDE
  - Python 3.10+

安装（仅首次）
  - 双击 CAI_DAT.bat

运行
  - 双击 RUN.bat

使用步骤
  1. （可选）备份当前账号。
  2. 将 JSON 拖到绿色区域，或选择文件，或在 accounts 文件夹扫描 -> 选择 -> 切换。
  3. 工具会关闭 Kiro -> 写入 token -> 重新打开。切换前请保存工作。

说明
  - 旧账号自动备份为 _previous_<time>.kiro-auth-token.json。
  - 若不想自动打开 Kiro，取消勾选「切换后重新打开 Kiro」。

界面语言
  右上角下拉：Tiếng Việt / English / 中文
