==========================================================
 工具2 — AWS 自动登录 -> 持久 JSON
 语言: README.txt (越) | README.en.txt | README.zh.txt
==========================================================

功能
  - 读取账号文件（Excel/txt）-> 用 Playwright 打开全新 Chrome
  - 自动登录 AWS IAM Identity Center：
      * 新账号（首次）-> 自动修改密码（可配置）
      * 已改过密码    -> 正常登录
    （工具自动识别，无需切换模式）
  - 导出完整持久 JSON（refresh_token + client_id + secret + profileArn）。
    支持批量 + 多线程。
  - 不操作 9router（请用工具3）。

环境要求
  - Windows + Python 3.10+

安装（仅首次）
  - 双击 CAI_DAT.bat（安装依赖 + Chromium 约150MB）

运行
  - 双击 RUN.bat

账号文件格式
  - Excel (.xlsx)：A列=邮箱/用户名，B列=密码
  - 文本 (.txt)：每行 "email:password" 或 "email|password"
  - 运行后工具会将新密码和结果写回文件。

使用步骤
  1. 选择账号文件。
  2. 选择 JSON 输出文件夹（默认 output_json）。
  3. 设置并行线程（建议3-5）、新密码、IDC start URL。
     若已改过密码：勾选「覆盖文件中的密码」并输入当前登录密码。
  4. OIDC 区域：us-east-1（IAM）。Kiro 区域：eu-central-1（欧盟工作区）。
  5. 点击开始自动登录。查看日志。

区域说明
  - OIDC 区域 = IAM 登录（通常 us-east-1）
  - Kiro 区域 = Q API 额度（欧盟用 eu-central-1）

说明
  - 无 MFA/2FA 的账号可全自动登录。
  - 出现验证码 -> 关闭无头模式手动处理。

界面语言
  右上角下拉：Tiếng Việt / English / 中文
