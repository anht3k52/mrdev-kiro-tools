==========================================================
 工具3 — 9ROUTER 注入器（修复 403）
 语言: README.txt (越) | README.en.txt | README.zh.txt
==========================================================

功能
  - 拖放（或选择）持久 JSON / cookie 导出文件：
      1. 从文件解析 profileArn + token
      2. 匹配 9router 中的 Kiro 连接（按 email / token / IDC）
         - 有匹配  -> 更新 profileArn（修复 403）
         - 无匹配  -> 新建连接（无需在 9router 内手动登录）
      3. （可选）通过 ListAvailableProfiles API 实时验证
      4. 自动重启 9router（停止 -> 写 DB -> 启动）
  - 连接状态：OK / 403（缺少 profileArn）/ ~1h（仅 cookie）。

环境要求
  - Windows + 已安装 9router（至少运行一次以创建数据库）
  - Python 3.10+（安装时勾选 "Add to PATH"）

安装（仅首次）
  - 双击 CAI_DAT.bat

运行
  - 双击 RUN.bat

使用步骤
  1. 将 JSON 文件（来自工具2或 cookie 导出）拖入绿色区域。
  2. 查看预览（更新/新建）-> 点击继续。
  3. 工具写入数据库并重启 9router。稍等几秒查看额度。

输入 JSON 类型
  - 持久 JSON（工具2）：含 refresh_token -> 长期有效，9router 自动刷新。
  - Cookie 导出（仅 access + ProfileArn）：约 1 小时内有效。

说明
  - 同一 IDC 的多个 IAM 用户可能共用 profileArn（同一 Kiro 额度），
    但 token 不同 — 工具按 email 分别导入每个账号。
  - 若之后再次出现 403，重新拖入 JSON 注入即可。

界面语言
  右上角下拉：Tiếng Việt / English / 中文
