# README Hệ Thống — 9router Injector Tool

> Tài liệu kỹ thuật đầy đủ để xây dựng một tool tương tự từ đầu.

---

## 1. Bài Toán Cần Giải Quyết

### 1.1 Context

**9router** là một desktop app chạy proxy/tunnel cho phép nhiều tài khoản Kiro (AI coding assistant của Amazon) hoạt động đồng thời trên cùng một máy. Mỗi tài khoản Kiro xác thực qua AWS IAM Identity Center (IDC) bằng giao thức OAuth2.

### 1.2 Vấn Đề 403

Khi 9router gọi API Kiro, nó gửi kèm:
```
Authorization: Bearer <accessToken>
X-Amz-Profile-Arn: arn:aws:sso:us-east-1::permissionSet/...
```

Nếu `profileArn` **null** hoặc **sai**, AWS trả về HTTP 403 `"User is not authorized"`. Điều này xảy ra vì:

- Tài khoản được tạo từ nguồn ngoài (không qua GUI đăng nhập của 9router)
- 9router lưu credential nhưng bỏ sót trường `profileArn`
- Token được refresh nhưng `profileArn` bị xóa/reset

### 1.3 Giải Pháp

Lấy đúng `profileArn` từ credential export của tài khoản → ghi đè vào SQLite database của 9router → restart 9router để load lại.

---

## 2. Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────┐
│                   GUI Layer                         │
│           inject_9router_gui.py                     │
│  - Drag & drop / file picker                        │
│  - Connection list với status badges                │
│  - Preview dialog → confirmation → worker thread    │
└───────────────────┬─────────────────────────────────┘
                    │ calls
┌───────────────────▼─────────────────────────────────┐
│               Business Logic Layer                  │
│                nine_router.py                       │
│  - Parse input files (3 formats)                    │
│  - Read/write SQLite database                       │
│  - Match credential to connection                   │
│  - Verify credential via live API call              │
│  - Stop/start 9router process                       │
└───────────────────┬─────────────────────────────────┘
                    │ reads/writes
┌───────────────────▼─────────────────────────────────┐
│             9router SQLite Database                  │
│   %APPDATA%\9router\db\data.sqlite                  │
│   Table: providerConnections                        │
└─────────────────────────────────────────────────────┘
```

---

## 3. Database Schema của 9router

### 3.1 Vị Trí Database

| OS      | Path |
|---------|------|
| Windows | `%APPDATA%\9router\db\data.sqlite` |
| macOS   | `~/.9router/db/data.sqlite` |

### 3.2 Table `providerConnections`

```sql
CREATE TABLE providerConnections (
    id         TEXT PRIMARY KEY,   -- UUID v4
    provider   TEXT,               -- "kiro"
    authType   TEXT,               -- "oauth"
    name       TEXT,               -- display name (email thường)
    email      TEXT,
    data       TEXT,               -- JSON blob (xem bên dưới)
    priority   INTEGER DEFAULT 0,
    isActive   INTEGER DEFAULT 1,
    createdAt  TEXT,
    updatedAt  TEXT
);
```

### 3.3 Cấu Trúc JSON trong Cột `data`

Có 2 "shape" tùy theo phiên bản 9router:

**Shape "oauth"** (phiên bản mới, camelCase):
```json
{
  "accessToken": "eyJr...",
  "refreshToken": "eyJr...",
  "expiresAt": "2024-01-15T10:30:00.000Z",
  "providerSpecificData": {
    "profileArn": "arn:aws:sso:us-east-1::permissionSet/ssoins-xxx/ps-xxx",
    "clientId": "q1l24sqjcpuqiitl3cb5n93hsh",
    "clientSecret": "1lam8pjuqn9qsk...",
    "startUrl": "https://d-9066713dd7.awsapps.com/start",
    "region": "us-east-1",
    "registrationExpiresAt": "2025-01-15T10:30:00.000Z"
  },
  "errorCode": null,
  "backoffLevel": 0,
  "disabledUntil": null
}
```

**Shape "idc"** (phiên bản cũ, snake_case):
```json
{
  "access_token": "eyJr...",
  "refresh_token": "eyJr...",
  "profile_arn": "arn:aws:sso:...",
  "start_url": "https://d-xxx.awsapps.com/start",
  "expires_at": "..."
}
```

**Trường quan trọng nhất:** `profileArn` (shape oauth) hoặc `profile_arn` (shape idc).

---

## 4. Các Định Dạng Input

Tool nhận 3 định dạng file khác nhau:

### 4.1 Cookie Export (Cookie-Editor Chrome Extension)

Export từ `app.kiro.dev` bằng Cookie-Editor plugin, lưu dạng JSON array:

```json
[
  {"name": "AccessToken", "value": "eyJr..."},
  {"name": "ProfileArn", "value": "arn:aws:sso:us-east-1::permissionSet/..."},
  {"name": "RefreshToken", "value": "eyJr..."},
  {"name": "UserId", "value": "d-9066713dd7.b4981428-xxxx-..."},
  {"name": "Idp", "value": "https://d-9066713dd7.awsapps.com/start"}
]
```

Chỉ có `AccessToken` + `ProfileArn` là bắt buộc. `RefreshToken` thường không có (cookie-only).

### 4.2 kiro-auth-token.json

File JSON phẳng (flat) chứa đầy đủ OAuth2 credentials:

```json
{
  "accessToken": "eyJr...",
  "refreshToken": "eyJr...",
  "profileArn": "arn:aws:sso:us-east-1::permissionSet/...",
  "expiresAt": "2024-01-15T10:30:00.000Z",
  "startUrl": "https://d-xxx.awsapps.com/start",
  "clientId": "q1l24sqjcpuqiitl3cb5n93hsh",
  "clientSecret": "1lam8pjuqn9qsk...",
  "region": "us-east-1"
}
```

### 4.3 Account JSON (Purchased Account Format)

Format của provider bên thứ 3, thường có thêm email/info:

```json
{
  "email": "user@example.com",
  "access_token": "eyJr...",
  "refresh_token": "eyJr...",
  "profile_arn": "arn:aws:sso:...",
  "expires_at": "1705312200",
  "start_url": "https://d-xxx.awsapps.com/start",
  "client_id": "q1l24sqjcpuqiitl3cb5n93hsh",
  "client_secret": "1lam8pjuqn9qsk..."
}
```

**Phân biệt 3 format:**
1. Nếu là JSON array → Cookie export
2. Nếu là JSON object và có `name`/`value` keys → Cookie export (alternate)
3. Nếu key chứa `AccessToken` (PascalCase) → Cookie export (inline)
4. Nếu key chứa `accessToken` (camelCase) → kiro-auth-token.json
5. Nếu key chứa `access_token` (snake_case) → Account JSON

---

## 5. Core Data Models

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class KiroRow:
    """Đại diện cho một connection trong database của 9router."""
    id: str                      # UUID
    provider: str                # "kiro"
    auth_type: str               # "oauth"
    name: Optional[str] = None   # email hoặc tên hiển thị
    email: Optional[str] = None
    data: dict = field(default_factory=dict)  # raw JSON blob
    is_active: bool = True

@dataclass  
class KiroExport:
    """Credentials được parse từ file input."""
    access_token: str
    profile_arn: str
    refresh_token: str = ""
    expires_at: str = ""
    start_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    registration_expires_at: str = ""
    region: str = "us-east-1"
    email: str = ""

    def can_create(self) -> bool:
        """Đủ field để tạo connection mới."""
        return bool(self.access_token and self.profile_arn)

    def can_refresh(self) -> bool:
        """Có refresh token + client credentials → tự động gia hạn."""
        return bool(
            self.refresh_token and 
            self.client_id and 
            self.client_secret
        )
```

---

## 6. Thuật Toán Matching

Khi có nhiều connection trong database và nhiều file input, cần tìm đúng connection để update.

### 6.1 Priority 1: Access Token Match

```python
def match_by_access_token(rows: list[KiroRow], export: KiroExport) -> Optional[KiroRow]:
    for row in rows:
        row_token = (
            row.data.get("accessToken") or           # oauth shape
            row.data.get("access_token") or          # idc shape
            ""
        )
        if row_token and row_token == export.access_token:
            return row
    return None
```

Đây là match chính xác nhất vì access token là unique per session.

### 6.2 Priority 2: IDC Directory Match

Nếu access token không match (token đã đổi), dùng IDC directory ID:

```python
import re

def idc_directory(text: str) -> str:
    """Extract 'd-xxxxxxxxxx' từ URL hoặc UserId."""
    # "https://d-9066713dd7.awsapps.com/start" → "d-9066713dd7"
    # "d-9066713dd7.b4981428-xxxx" → "d-9066713dd7"
    m = re.search(r'(d-[0-9a-f]{10})', text or "")
    return m.group(1) if m else ""

def match_by_idc(rows: list[KiroRow], export: KiroExport) -> list[KiroRow]:
    export_idc = idc_directory(export.start_url)
    if not export_idc:
        return []
    
    matches = []
    for row in rows:
        row_url = (
            (row.data.get("providerSpecificData") or {}).get("startUrl") or
            row.data.get("start_url") or
            ""
        )
        if idc_directory(row_url) == export_idc:
            matches.append(row)
    return matches
```

---

## 7. Quy Trình Inject (Core Operation)

```python
import sqlite3, json, uuid
from datetime import datetime, timezone

def apply_export_to_row(db_path: str, row_id: str, export: KiroExport) -> None:
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT data FROM providerConnections WHERE id = ?",
            (row_id,)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Row {row_id} not found")
        
        data = json.loads(row[0])
        shape = detect_shape(data)
        
        if shape == "oauth":
            psd = data.setdefault("providerSpecificData", {})
            psd["profileArn"] = export.profile_arn
            if export.access_token:
                data["accessToken"] = export.access_token
            if export.expires_at:
                data["expiresAt"] = export.expires_at
            # Clear error/backoff flags
            data["errorCode"] = None
            data["backoffLevel"] = 0
            data["disabledUntil"] = None
            
        elif shape == "idc":
            data["profile_arn"] = export.profile_arn
            if export.access_token:
                data["access_token"] = export.access_token
        
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        cur.execute(
            "UPDATE providerConnections SET data = ?, updatedAt = ? WHERE id = ?",
            (json.dumps(data), now, row_id)
        )
        conn.commit()


def detect_shape(data: dict) -> str:
    if "providerSpecificData" in data or "accessToken" in data:
        return "oauth"
    return "idc"
```

---

## 8. Tạo Connection Mới

Khi không tìm thấy connection nào match, tạo mới:

```python
def create_connection(db_path: str, export: KiroExport) -> str:
    row_id = str(uuid.uuid4())
    
    # Tính expires_at: ngay lập tức nếu có thể refresh, ngược lại +45 phút
    if export.can_refresh():
        expires_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        from datetime import timedelta
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=45)
        ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    data = {
        "accessToken": export.access_token,
        "refreshToken": export.refresh_token,
        "expiresAt": expires_at,
        "providerSpecificData": {
            "profileArn": export.profile_arn,
            "clientId": export.client_id,
            "clientSecret": export.client_secret,
            "startUrl": export.start_url,
            "region": export.region or "us-east-1",
        },
        "errorCode": None,
        "backoffLevel": 0,
        "disabledUntil": None,
    }
    
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT INTO providerConnections
                (id, provider, authType, name, email, data, priority, isActive, createdAt, updatedAt)
            VALUES (?, 'kiro', 'oauth', ?, ?, ?, 0, 1, ?, ?)
        """, (
            row_id,
            export.email or export.start_url or "Kiro Account",
            export.email or "",
            json.dumps(data),
            now, now
        ))
        conn.commit()
    
    return row_id
```

---

## 9. Live Verification (Tùy Chọn)

Kiểm tra credential trực tiếp qua API AWS Kiro:

```python
import urllib.request

def verify_token_profile(access_token: str, profile_arn: str) -> tuple[int, str]:
    """
    Returns: (http_status_code, message)
    200 = valid, 403 = bad profileArn, 401 = expired token
    """
    url = "https://q.us-east-1.amazonaws.com/generateAssistantResponse"
    payload = json.dumps({
        "conversationState": {
            "currentMessage": {"userInputMessage": {"content": []}},
            "chatTriggerType": "MANUAL"
        }
    }).encode()
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "x-amzn-identity-profile-arn": profile_arn,
            "Content-Type": "application/json",
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, "OK"
    except urllib.error.HTTPError as e:
        return e.code, e.reason
    except Exception as e:
        return 0, str(e)
```

---

## 10. Quản Lý Process 9router

### 10.1 Tìm và Dừng Process

```python
import psutil
import subprocess
import time

KIRO_KEYWORDS = ["cli.js", "server.js", "cloudflared", "tray.ps1", "9router"]

def find_9router_processes() -> list[psutil.Process]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = " ".join(p.info["cmdline"] or []).lower()
            if any(kw in cmd for kw in KIRO_KEYWORDS):
                procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return procs

def capture_launch_command() -> str:
    """Lưu lại command để restart sau."""
    procs = find_9router_processes()
    if procs:
        try:
            cmdline = procs[0].cmdline()
            return subprocess.list2cmdline(cmdline)
        except Exception:
            pass
    return ""

def stop_9router() -> None:
    for p in find_9router_processes():
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(1.5)  # Đợi process thực sự dừng

def start_9router(launch_cmd: str) -> None:
    if launch_cmd:
        subprocess.Popen(
            launch_cmd,
            shell=True,
            creationflags=subprocess.DETACHED_PROCESS  # Windows only
        )
```

---

## 11. Phân Tích Status của Connection

```python
from datetime import datetime, timezone

def connection_status(row: KiroRow) -> str:
    """
    Returns:
        "ok"    → có profileArn hợp lệ + token còn hạn
        "403"   → thiếu profileArn
        "~1h"   → có profileArn nhưng token sắp hết hạn (không tự refresh được)
        "exp"   → token đã hết hạn
    """
    data = row.data
    psd = data.get("providerSpecificData", {})
    
    profile_arn = psd.get("profileArn") or data.get("profile_arn") or ""
    expires_at_str = data.get("expiresAt") or data.get("expires_at") or ""
    refresh_token = data.get("refreshToken") or data.get("refresh_token") or ""
    client_id = psd.get("clientId") or data.get("client_id") or ""
    
    if not profile_arn:
        return "403"
    
    if expires_at_str:
        try:
            # Handle both ISO string and Unix timestamp
            if expires_at_str.isdigit():
                expires_at = datetime.fromtimestamp(int(expires_at_str), tz=timezone.utc)
            else:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            
            now = datetime.now(timezone.utc)
            if expires_at < now:
                if refresh_token and client_id:
                    return "ok"  # Có thể tự refresh
                return "exp"
            
            remaining = (expires_at - now).total_seconds()
            if remaining < 3600 and not (refresh_token and client_id):
                return "~1h"
        except ValueError:
            pass
    
    return "ok"
```

---

## 12. GUI Layer

### 12.1 Stack Công Nghệ

```
customtkinter    → Modern dark-mode Tkinter widgets
tkinterdnd2      → Drag-and-drop file support
threading        → Worker thread để không block UI
```

### 12.2 Luồng Người Dùng

```
1. App khởi động
   → Tìm database 9router
   → Load tất cả connections
   → Hiển thị list với status badge

2. User drop file JSON (hoặc click Browse)
   → Parse file → tạo KiroExport object
   → Match với connections trong DB
   → Hiển thị Preview Dialog:
      - List connections sẽ được UPDATE
      - List connections sẽ được CREATE (nếu không match)
      - ⚠ Warning nếu nhiều account cùng profileArn (shared quota)

3. User xác nhận
   → Worker thread chạy:
      a. capture_launch_command()
      b. stop_9router()
      c. apply_export_to_row() hoặc create_connection()
      d. verify_token_profile() (nếu được bật)
      e. start_9router()
   → Cập nhật log box realtime
   → Refresh connection list

4. Done: hiển thị kết quả
```

### 12.3 Cấu Trúc Widget Chính

```python
import customtkinter as ctk

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("9router Injector")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")
        
        self._build_header()    # Language selector, Refresh, Restart buttons
        self._build_drop_zone() # Drag & drop area
        self._build_db_status() # Database path + summary counts
        self._build_conn_list() # Scrollable list of connections
        self._build_options()   # Auto-restart, Live-verify checkboxes
        self._build_file_picker()
        self._build_log_box()   # Real-time activity log

    def _on_file_drop(self, event):
        paths = self.tk.splitlist(event.data)
        self._process_files(paths)

    def _process_files(self, paths: list[str]):
        exports = []
        for path in paths:
            try:
                exp = parse_kiro_export(path)
                exports.append(exp)
            except Exception as e:
                self._log(f"[ERR] {path}: {e}")
        
        if exports:
            self._show_preview(exports)

    def _show_preview(self, exports: list[KiroExport]):
        # Modal dialog hiển thị plan của thao tác
        dialog = PreviewDialog(self, exports, self.rows)
        self.wait_window(dialog)
        if dialog.confirmed:
            self._run_inject(exports, dialog.plan)

    def _run_inject(self, exports, plan):
        import threading
        threading.Thread(
            target=self._inject_worker,
            args=(exports, plan),
            daemon=True
        ).start()

    def _inject_worker(self, exports, plan):
        self._log("Đang dừng 9router...")
        launch_cmd = capture_launch_command()
        stop_9router()
        
        for item in plan:
            if item["action"] == "update":
                apply_export_to_row(self.db_path, item["row_id"], item["export"])
            elif item["action"] == "create":
                create_connection(self.db_path, item["export"])
        
        if self.var_verify.get():
            for item in plan:
                status, msg = verify_token_profile(
                    item["export"].access_token,
                    item["export"].profile_arn
                )
                self._log(f"Verify: HTTP {status} — {msg}")
        
        if self.var_restart.get() and launch_cmd:
            self._log("Đang khởi động lại 9router...")
            start_9router(launch_cmd)
        
        self.after(0, self._refresh_list)  # Update UI từ main thread
```

---

## 13. Internationalization

### 13.1 Cấu Trúc i18n

```python
LANG_CODE = "vi"  # "vi", "en", "zh"

TRANSLATIONS = {
    "Làm mới": {"en": "Refresh", "zh": "刷新"},
    "Khởi động lại 9router": {"en": "Restart 9router", "zh": "重启 9router"},
    "Kéo thả file JSON vào đây": {
        "en": "Drop JSON file here",
        "zh": "将 JSON 文件拖放到此处"
    },
    # ... 170+ entries
}

def t(text: str) -> str:
    """Translate text to current language."""
    if LANG_CODE == "vi":
        return text
    entry = TRANSLATIONS.get(text, {})
    return entry.get(LANG_CODE, text)
```

---

## 14. Build & Deployment

### 14.1 Dependencies

```
# requirements.txt
customtkinter>=5.2.0    # GUI framework
psutil>=5.9.0           # Process management
tkinterdnd2>=0.3.0      # Drag-and-drop (optional)
```

Cài đặt:
```batch
pip install -r requirements.txt
```

### 14.2 Chạy từ Source

```batch
:: RUN.bat
@echo off
py inject_9router_gui.py 2>nul || python inject_9router_gui.py
```

### 14.3 Build thành EXE (Nuitka)

```batch
:: BUILD_EXE.bat — Yêu cầu Python 3.12 (không tương thích Python 3.13)
pip install nuitka zstandard

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    --include-package=customtkinter ^
    --include-data-dir="%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages\customtkinter"=customtkinter ^
    --output-dir=_build ^
    inject_9router_gui.py
```

---

## 15. Hướng Dẫn Xây Dựng Tool Tương Tự

### 15.1 Checklist Tối Thiểu (MVP)

- [ ] **Parse input**: Nhận JSON file, detect format (cookie/auth-token/account)
- [ ] **Locate DB**: Tìm SQLite database của target app theo OS
- [ ] **Read rows**: Query rows cần update
- [ ] **Match**: Thuật toán ghép credential với row
- [ ] **Patch**: UPDATE hoặc INSERT vào SQLite
- [ ] **Restart**: Stop/start target app process

### 15.2 Adapt Sang App Khác

Nếu muốn làm tool tương tự cho một app khác (không phải 9router):

1. **Tìm database**: Dùng `Process Monitor` (Windows) hoặc `strace` (Linux) để xem app đọc file nào
2. **Reverse data schema**: Dùng `DB Browser for SQLite` để inspect table structure
3. **Identify credential fields**: Chạy app, login, xem data thay đổi gì trong DB
4. **Implement parser**: Parse credential từ source (cookie, token file, API response...)
5. **Implement patcher**: UPDATE đúng fields trong DB
6. **Test**: Verify HTTP 200 sau khi patch

### 15.3 Điểm Cần Lưu Ý

| Vấn đề | Giải pháp |
|--------|-----------|
| App đang chạy, DB bị lock | Dùng WAL mode: `PRAGMA journal_mode=WAL` hoặc stop app trước |
| Schema thay đổi giữa các version | Detect shape động (không hardcode field names) |
| Token hết hạn | Implement refresh flow hoặc cảnh báo user |
| Multiple accounts match | Ưu tiên exact match, fallback sang partial match |
| App cache credentials trong RAM | Bắt buộc restart app sau khi patch DB |

---

## 16. Cấu Trúc File Cho Tool Mới

```
my_injector/
├── main.py              # Entry point, khởi tạo GUI
├── gui.py               # GUI layer (CustomTkinter)
├── core.py              # Business logic (parse, match, patch, verify)
├── models.py            # Data classes (Row, Export)
├── process_mgr.py       # Stop/start target app
├── i18n.py              # Translations (nếu cần đa ngôn ngữ)
├── requirements.txt
├── RUN.bat
└── BUILD_EXE.bat
```

---

## 17. Ví Dụ Code Đầy Đủ — Core Flow

```python
# Minimal working example
import sqlite3, json, sys
from pathlib import Path

def inject(db_path: str, credential_file: str) -> None:
    # 1. Parse credential
    with open(credential_file) as f:
        raw = json.load(f)
    
    # Detect format và extract fields
    if isinstance(raw, list):  # Cookie export
        cookies = {c["name"]: c["value"] for c in raw}
        access_token = cookies.get("AccessToken", "")
        profile_arn  = cookies.get("ProfileArn", "")
    else:  # JSON object
        access_token = raw.get("accessToken") or raw.get("access_token", "")
        profile_arn  = raw.get("profileArn") or raw.get("profile_arn", "")
    
    if not (access_token and profile_arn):
        print("ERROR: Missing accessToken or profileArn")
        sys.exit(1)
    
    # 2. Tìm matching row trong DB
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM providerConnections WHERE provider = 'kiro'"
        ).fetchall()
    
    target_row = None
    for row in rows:
        data = json.loads(row["data"])
        if data.get("accessToken") == access_token:
            target_row = row
            break
    
    if not target_row:
        print(f"No matching connection found. Will create new.")
    
    # 3. Patch database
    with sqlite3.connect(db_path) as conn:
        if target_row:
            data = json.loads(target_row["data"])
            psd = data.setdefault("providerSpecificData", {})
            psd["profileArn"] = profile_arn
            data["errorCode"] = None
            data["backoffLevel"] = 0
            conn.execute(
                "UPDATE providerConnections SET data = ? WHERE id = ?",
                (json.dumps(data), target_row["id"])
            )
            print(f"Updated connection: {target_row['id']}")
        # else: create new row (xem section 8)
        conn.commit()
    
    print("Done! Restart 9router to apply changes.")


if __name__ == "__main__":
    DB = Path.home() / "AppData/Roaming/9router/db/data.sqlite"
    inject(str(DB), sys.argv[1])
```

---

*Tài liệu này mô tả đầy đủ cách hoạt động của 9router Injector Tool và cung cấp đủ thông tin để xây dựng tool tương tự cho bất kỳ app nào có cơ chế lưu credential trong SQLite.*
