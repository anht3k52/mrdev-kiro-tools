# -*- coding: utf-8 -*-
"""i18n don gian cho 3 tool: VI (goc) / EN / ZH. Key = chuoi tieng Viet goc.
t(s) tra ve ban dich theo ngon ngu hien tai; thieu -> tra lai s (fallback VI)."""
from __future__ import annotations

_CUR = {"lang": "vi"}
LANG_DISPLAY = {"vi": "Tiếng Việt", "en": "English", "zh": "中文"}
DISPLAY_TO_CODE = {v: k for k, v in LANG_DISPLAY.items()}
LANG_ORDER = ["Tiếng Việt", "English", "中文"]


def set_lang(code: str) -> None:
    _CUR["lang"] = code if code in LANG_DISPLAY else "vi"


def get_lang() -> str:
    return _CUR["lang"]


def t(s: str) -> str:
    if _CUR["lang"] == "vi":
        return s
    return _TR.get(s, {}).get(_CUR["lang"], s)


# vi_key -> {"en":..., "zh":...}
_TR = {
    # ---------- Chung ----------
    "(bam de mo)": {"en": "(click to open)", "zh": "(点击打开)"},
    "Telegram: @BotbanloBot": {"en": "Telegram: @BotbanloBot", "zh": "Telegram: @BotbanloBot"},
    "Log:": {"en": "Log:", "zh": "日志:"},
    "Ngon ngu:": {"en": "Language:", "zh": "语言:"},
    "thieu profileArn (403)": {"en": "missing profileArn (403)", "zh": "缺少 profileArn (403)"},
    "cookie-only (chet ~1h)": {"en": "cookie-only (~1h)", "zh": "仅 cookie（约1小时）"},
    "   ⚠ cookie-only (~1h)": {"en": "   ⚠ cookie-only (~1h)", "zh": "   ⚠ 仅 cookie（约1小时）"},
    "DB loi:": {"en": "DB error:", "zh": "数据库错误:"},
    "(folder chua ton tai: {path})": {"en": "(folder not found: {path})", "zh": "（文件夹不存在: {path}）"},
    "Luong song song:": {"en": "Parallel threads:", "zh": "并行线程:"},
    "Loi": {"en": "Error", "zh": "错误"},
    "Xong": {"en": "Done", "zh": "完成"},
    "Tiep tuc?": {"en": "Continue?", "zh": "继续？"},

    # ---------- TOOL 1 ----------
    "Tool 1 — Kiro IDE Swapper": {"en": "Tool 1 — Kiro IDE Swapper", "zh": "工具1 — Kiro IDE 切换器"},
    "🔄 KIRO IDE SWAPPER": {"en": "🔄 KIRO IDE SWAPPER", "zh": "🔄 KIRO IDE 切换器"},
    "↻ Refresh": {"en": "↻ Refresh", "zh": "↻ 刷新"},
    "💾 Backup account dang login...": {"en": "💾 Backup current account...", "zh": "💾 备份当前账号..."},
    "Mo lai Kiro sau khi swap": {"en": "Reopen Kiro after swap", "zh": "切换后重新打开 Kiro"},
    "📥 KEO-THA file JSON vao day de SWAP ngay":
        {"en": "📥 DRAG & DROP a JSON file here to SWAP now",
         "zh": "📥 把 JSON 文件拖到这里立即切换"},
    "📥 Bam 'Swap file JSON...' de chon file (cai tkinterdnd2 de keo-tha)":
        {"en": "📥 Click 'Swap JSON file...' to pick a file (install tkinterdnd2 for drag & drop)",
         "zh": "📥 点击“切换 JSON 文件...”选择文件（安装 tkinterdnd2 可拖放）"},
    "Folder account:": {"en": "Accounts folder:", "zh": "账号文件夹:"},
    "↻ Scan": {"en": "↻ Scan", "zh": "↻ 扫描"},
    "📂 Swap file JSON...": {"en": "📂 Swap JSON file...", "zh": "📂 切换 JSON 文件..."},
    "Cac file account trong folder (chon roi Swap):":
        {"en": "Account files in folder (select then Swap):", "zh": "文件夹中的账号文件（选择后切换）:"},
    "⟳ SWAP sang account da chon": {"en": "⟳ SWAP to selected account", "zh": "⟳ 切换到所选账号"},
    "(chua chon)": {"en": "(none selected)", "zh": "(未选择)"},
    "Active: (chua login Kiro IDE)": {"en": "Active: (not logged into Kiro IDE)", "zh": "当前: (未登录 Kiro IDE)"},
    "(khong co file .json)": {"en": "(no .json files)", "zh": "(没有 .json 文件)"},
    "Chon": {"en": "Select", "zh": "选择"},
    "Da chon:": {"en": "Selected:", "zh": "已选:"},
    "Chua chon": {"en": "Nothing selected", "zh": "未选择"},
    "Hay bam 'Chon' o 1 dong truoc.": {"en": "Click 'Select' on a row first.", "zh": "请先在某一行点击“选择”。"},
    "Khong thay file": {"en": "File not found", "zh": "找不到文件"},
    "Xac nhan SWAP": {"en": "Confirm SWAP", "zh": "确认切换"},
    "Da swap. Mo Kiro IDE de kiem tra.": {"en": "Swapped. Open Kiro IDE to check.", "zh": "已切换。打开 Kiro IDE 检查。"},
    "Loi swap": {"en": "Swap error", "zh": "切换错误"},
    "Chua login": {"en": "Not logged in", "zh": "未登录"},
    "Khong co account dang login de backup.": {"en": "No logged-in account to back up.", "zh": "没有可备份的已登录账号。"},
    "Backup": {"en": "Backup", "zh": "备份"},
    "Dat ten cho account dang login:": {"en": "Name for the current account:", "zh": "为当前账号命名:"},
    "Da backup": {"en": "Backed up", "zh": "已备份"},
    "Loi backup": {"en": "Backup error", "zh": "备份错误"},

    # ---------- TOOL 2 ----------
    "Tool 2 — AWS Auto Login": {"en": "Tool 2 — AWS Auto Login", "zh": "工具2 — AWS 自动登录"},
    "🤖 AWS AUTO LOGIN → JSON DURABLE":
        {"en": "🤖 AWS AUTO LOGIN → DURABLE JSON", "zh": "🤖 AWS 自动登录 → 持久 JSON"},
    "File account (xlsx: Email|Password · txt: email:password):":
        {"en": "Account file (xlsx: Email|Password · txt: email:password):",
         "zh": "账号文件 (xlsx: 邮箱|密码 · txt: email:password):"},
    "📂 Chon file...": {"en": "📂 Choose file...", "zh": "📂 选择文件..."},
    "Thu muc xuat JSON:": {"en": "JSON output folder:", "zh": "JSON 输出文件夹:"},
    "IDC start URL:": {"en": "IDC start URL:", "zh": "IDC start URL:"},
    "Kiro region (9router quota):": {"en": "Kiro region (9router quota):", "zh": "Kiro 区域 (9router 额度):"},
    "OIDC region (login IAM):": {"en": "OIDC region (login IAM):", "zh": "OIDC 区域 (IAM 登录):"},
    "OIDC region:": {"en": "OIDC region:", "zh": "OIDC 区域:"},
    "Kiro region:": {"en": "Kiro region:", "zh": "Kiro 区域:"},
    "Mat khau moi (doi lan dau):": {"en": "New password (first-login reset):", "zh": "新密码（首次登录需改）:"},
    "Mat khau dang nhap (tuy chinh):": {"en": "Login password (custom):", "zh": "登录密码（自定义）:"},
    "Ghi de password trong file (da doi pass)": {
        "en": "Override file password (already changed pass)", "zh": "覆盖文件中的密码（已改过密）"},
    "Bat 'ghi de password' va nhap mat khau hien tai.": {
        "en": "Enable override and enter the current login password.", "zh": "请勾选覆盖并输入当前登录密码。"},
    "Login password:": {"en": "Login password:", "zh": "登录密码:"},
    "Headless (an browser)": {"en": "Headless (hide browser)", "zh": "无头模式（隐藏浏览器）"},
    "🚀 BAT DAU AUTO LOGIN": {"en": "🚀 START AUTO LOGIN", "zh": "🚀 开始自动登录"},
    "⛔ Dung": {"en": "⛔ Stop", "zh": "⛔ 停止"},
    "Tu nhan dien 2 dang: account moi (bi bat doi pass) & account da doi pass. "
    "Da doi pass roi -> tick 'Ghi de password' va nhap mat khau hien tai. "
    "Account fresh khong MFA login 100% tu dong. Neu gap captcha (account bi nghi ngo) "
    "-> tat Headless de giai tay.":
        {"en": "Auto-detects new account (forced password change) & already-changed account. "
               "Already changed pass -> tick override and enter current login password. "
               "Fresh accounts without MFA log in automatically. Captcha -> turn off Headless.",
         "zh": "自动识别新账号（强制改密）与已改密账号。已改过密请勾选覆盖并输入当前密码。"
               "无 MFA 可全自动登录。遇验证码请关闭无头模式手动处理。"},
    "Thieu file": {"en": "Missing file", "zh": "缺少文件"},
    "Hay chon file account hop le.": {"en": "Please choose a valid account file.", "zh": "请选择有效的账号文件。"},
    "Loi doc file": {"en": "File read error", "zh": "读取文件出错"},
    "File trong": {"en": "Empty file", "zh": "空文件"},
    "Khong doc duoc account.\nXlsx: cot A=Email, B=Password.\nTxt: moi dong 'email:password'.":
        {"en": "No accounts read.\nXlsx: col A=Email, B=Password.\nTxt: one 'email:password' per line.",
         "zh": "未读取到账号。\nXlsx: A列=邮箱, B列=密码。\nTxt: 每行 'email:password'。"},
    "Xac nhan": {"en": "Confirm", "zh": "确认"},
    "Auto login — xong": {"en": "Auto login — done", "zh": "自动登录 — 完成"},

    # ---------- TOOL 3 ----------
    "Tool 3 — 9router Injector": {"en": "Tool 3 — 9router Injector", "zh": "工具3 — 9router 注入器"},
    "⚡ 9ROUTER INJECTOR — Fix 403": {"en": "⚡ 9ROUTER INJECTOR — Fix 403", "zh": "⚡ 9ROUTER 注入器 — 修复 403"},
    "⟳ Restart 9router": {"en": "⟳ Restart 9router", "zh": "⟳ 重启 9router"},
    "Tu restart 9router sau khi inject":
        {"en": "Auto-restart 9router after inject", "zh": "注入后自动重启 9router"},
    "Live verify (goi API, chac chan 200)":
        {"en": "Live verify (ListAvailableProfiles API)", "zh": "实时验证（ListAvailableProfiles API）"},
    "📥 Chon file JSON...": {"en": "📥 Choose JSON file...", "zh": "📥 选择 JSON 文件..."},
    "📥 KEO-THA (vut) file JSON vao day → tu Import + Fix 403 (tao moi neu chua co)":
        {"en": "📥 DRAG & DROP JSON files here → auto Import + Fix 403 (create new if missing)",
         "zh": "📥 把 JSON 文件拖到这里 → 自动导入 + 修复 403（没有则新建）"},
    "📥 Bam 'Chon file JSON...' (cai tkinterdnd2 de keo-tha)":
        {"en": "📥 Click 'Choose JSON file...' (install tkinterdnd2 for drag & drop)",
         "zh": "📥 点击“选择 JSON 文件...”（安装 tkinterdnd2 可拖放）"},
    "Kiro connections trong 9router (trang thai profileArn):":
        {"en": "Kiro connections in 9router (profileArn status):", "zh": "9router 中的 Kiro 连接（profileArn 状态）:"},
    "DB 9router: KHONG TIM THAY — mo 9router 1 lan roi Refresh":
        {"en": "9router DB: NOT FOUND — open 9router once then Refresh",
         "zh": "9router 数据库：未找到 — 先打开一次 9router 再刷新"},
    "(khong co DB 9router)": {"en": "(no 9router DB)", "zh": "(没有 9router 数据库)"},
    "(chua co connection Kiro — vut 1 file JSON vao de TAO MOI)":
        {"en": "(no Kiro connection — drop a JSON file to CREATE)",
         "zh": "(还没有 Kiro 连接 — 拖入一个 JSON 文件以新建)"},
    "Khong tim thay 9router DB": {"en": "9router DB not found", "zh": "找不到 9router 数据库"},
    "Mo 9router it nhat 1 lan (de co DB).": {"en": "Open 9router at least once (to create the DB).", "zh": "至少打开一次 9router（以生成数据库）。"},
    "Loi doc DB": {"en": "DB read error", "zh": "读取数据库出错"},
    "Khong xu ly duoc gi": {"en": "Nothing to process", "zh": "无可处理项"},
    "Xac nhan Inject → 9router": {"en": "Confirm Inject → 9router", "zh": "确认注入 → 9router"},
    "9router — xong": {"en": "9router — done", "zh": "9router — 完成"},

    # ---------- Dialog body / template (placeholder {..} giu nguyen o moi ngon ngu) ----------
    # Tool 1
    "Doi account Kiro IDE sang:": {"en": "Switch Kiro IDE account to:", "zh": "将 Kiro IDE 账号切换为:"},
    "Kiro.exe se TAT (luu cong viec truoc!) roi mo lai.":
        {"en": "Kiro.exe will CLOSE (save your work first!) then reopen.",
         "zh": "将关闭 Kiro.exe（请先保存工作！）然后重新打开。"},
    # Tool 2
    "Login {n} account?": {"en": "Log in {n} account(s)?", "zh": "登录 {n} 个账号？"},
    "Headless:": {"en": "Headless:", "zh": "无头模式:"},
    "Xuat JSON ->": {"en": "Export JSON ->", "zh": "导出 JSON ->"},
    "Thanh cong:": {"en": "Success:", "zh": "成功:"},
    "That bai:": {"en": "Failed:", "zh": "失败:"},
    "JSON da xuat vao:": {"en": "JSON exported to:", "zh": "JSON 已导出到:"},
    "Dung Tool 3 de inject cac JSON nay vao 9router.":
        {"en": "Use Tool 3 to inject these JSON files into 9router.",
         "zh": "用工具3 把这些 JSON 注入 9router。"},
    # Tool 3
    "{u} cap nhat, {c} tao moi:": {"en": "{u} update, {c} create:", "zh": "{u} 个更新, {c} 个新建:"},
    "Sau do TU RESTART 9router.": {"en": "Then AUTO-RESTART 9router.", "zh": "之后自动重启 9router。"},
    "Bo qua:": {"en": "Skipped:", "zh": "已跳过:"},
    "Cap nhat {u} · Tao moi {c}.": {"en": "Updated {u} · Created {c}.", "zh": "更新 {u} · 新建 {c}。"},
    "9router da restart — doi vai giay, quota se hien.":
        {"en": "9router restarted — wait a few seconds, quota will appear.",
         "zh": "9router 已重启 — 稍等几秒，额度将显示。"},
    "Nho restart 9router de doc lai DB.":
        {"en": "Remember to restart 9router to reload the DB.", "zh": "请重启 9router 以重新加载数据库。"},
    "CAP NHAT": {"en": "UPDATE", "zh": "更新"},
    "TAO MOI": {"en": "NEW", "zh": "新建"},
    "TRUNG QUOTA": {"en": "DUP QUOTA", "zh": "额度重复"},
    "BO QUA TRUNG": {"en": "SKIP DUP", "zh": "跳过重复"},
    "Bo qua trung:": {"en": "Skipped duplicates:", "zh": "跳过重复:"},
    "Da bo qua {n} file trung profileArn trong lo nay (chi giu 1).":
        {"en": "Skipped {n} duplicate profileArn file(s) in this batch (kept 1 only).",
         "zh": "本批次跳过 {n} 个 profileArn 重复文件（仅保留 1 个）。"},
    "Da bo qua {n} file trung account trong lo nay (cung email/token).":
        {"en": "Skipped {n} duplicate account file(s) in this batch (same email/token).",
         "zh": "本批次跳过 {n} 个重复账号文件（相同 email/token）。"},
    "CANH BAO: nhieu account CHUNG profileArn — quota Kiro giong nhau, nhung moi connection co token rieng.":
        {"en": "WARNING: multiple accounts SHARE profileArn — same Kiro quota, but each connection has its own token.",
         "zh": "警告：多个账号共用 profileArn — Kiro 额度相同，但每个连接有独立 token。"},
    "tam ~1h": {"en": "~1h temp", "zh": "临时~1h"},
    "⚠⚠ CANH BAO: {n} account TRUNG profileArn (chung 1 quota voi acc da co/da add — them KHONG tang quota):":
        {"en": "⚠⚠ WARNING: {n} account(s) DUPLICATE profileArn (same quota as existing/added — adds NO extra quota):",
         "zh": "⚠⚠ 警告: {n} 个账号 profileArn 重复（与已有/已加账号共用同一额度 — 不会增加额度）:"},
    "-> Muon tang quota: dung acc co profileArn KHAC (directory IDC khac).":
        {"en": "-> To add quota: use accounts with a DIFFERENT profileArn (different IDC directory).",
         "zh": "-> 想增加额度: 使用 profileArn 不同的账号（不同的 IDC directory）。"},
    "acc CHUNG QUOTA": {"en": "acc(s) SHARE QUOTA", "zh": "账号共用额度"},
    "profileArn)": {"en": "profileArn)", "zh": "profileArn)"},
}
