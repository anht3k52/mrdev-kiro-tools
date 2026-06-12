"""Auto import / fix Kiro accounts in 9router.

9router luu connections trong SQLite:
    Windows: %APPDATA%\\9router\\db\\data.sqlite
    Mac:     ~/.9router/db/data.sqlite
    (fallback Win: %USERPROFILE%\\.9router\\db\\data.sqlite)

Bang `providerConnections`, cot `data` (TEXT JSON). Voi Kiro tren build hien tai,
data co shape "oauth":
    {
      "accessToken": "...",            <- top-level
      "refreshToken": "...",
      "expiresAt": "...",
      "testStatus": "active",
      "providerSpecificData": {        <- NESTED
        "profileArn": null,            <- *** null = loi 403 ***
        "clientId": "...",
        "clientSecret": "...",
        "region": "us-east-1",           <- OIDC/IAM (token refresh), KHONG doi neu IDC o US
        "kiroRegion": "eu-central-1",    <- Kiro Q API (quota), workspace EU
        "authMethod": "idc",
        "startUrl": "https://d-9066713dd7.awsapps.com/start"
      }
    }
Mot so build IDC cu dung snake_case top-level (access_token, profile_arn, ...).

=== NGUYEN NHAN 403 (da verify bang live API) ===
    POST https://q.us-east-1.amazonaws.com/generateAssistantResponse
      - profileArn dung   -> HTTP 200 (9router hien quota)
      - profileArn = null  -> HTTP 403 "User is not authorized to make this call."
      - profileArn sai     -> HTTP 403 "bearer token ... is invalid."

=== CACH FIX ===
    Lay profileArn that cua account tu file export (cookie `ProfileArn`) roi ghi
    vao dung row 9router (`providerSpecificData.profileArn`). Kem theo access token
    khop de chay duoc ngay. Match row theo IDC directory (startUrl `d-XXXX`).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sqlite3
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import psutil

Q_ENDPOINT = "https://q.eu-central-1.amazonaws.com/generateAssistantResponse"  # legacy alias
DEFAULT_OIDC_REGION = "us-east-1"   # IAM Identity Center / OIDC token refresh
DEFAULT_KIRO_REGION = "eu-central-1"  # Kiro Q API (quota generateAssistantResponse)


def region_from_profile_arn(arn: str) -> str:
    parts = (arn or "").split(":")
    if len(parts) >= 4 and parts[2] == "codewhisperer" and parts[3]:
        return parts[3]
    return ""


def kiro_q_endpoint(region: str = "") -> str:
    r = (region or "").strip() or DEFAULT_KIRO_REGION
    return f"https://q.{r}.amazonaws.com/generateAssistantResponse"


def resolve_kiro_region(*, region: str = "", kiro_region: str = "", profile_arn: str = "") -> str:
    """Region endpoint Kiro Q (q.*.amazonaws.com) — KHAC OIDC/AWS region."""
    r = (kiro_region or region or "").strip()
    if r:
        return r
    return DEFAULT_KIRO_REGION


def resolve_oidc_region(*, oidc_region: str = "", idc_region: str = "", psd_region: str = "") -> str:
    """Region OIDC (oidc.*.amazonaws.com) — IAM login/refresh, thuong us-east-1."""
    r = (oidc_region or idc_region or psd_region or "").strip()
    return r or DEFAULT_OIDC_REGION

# Kiro IDE / AWS SSO luu creds o day sau khi login that (SSO device flow):
#   kiro-auth-token.json     -> accessToken, refreshToken, profileArn, expiresAt
#   <sha1>.json (OIDC reg)   -> clientId, clientSecret  (han ~3 thang)
LOCAL_SSO_CACHE = Path.home() / ".aws" / "sso" / "cache"


# ---------------------------------------------------------------------
# DB discovery
# ---------------------------------------------------------------------
def default_db_paths() -> list[Path]:
    paths: list[Path] = []
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "9router" / "db" / "data.sqlite")
        home = Path(os.path.expandvars(r"%USERPROFILE%"))
        paths.append(home / ".9router" / "db" / "data.sqlite")
    else:
        home = Path.home()
        paths.append(home / ".9router" / "db" / "data.sqlite")
        if sys.platform == "darwin":
            paths.append(
                home / "Library" / "Application Support" / "9router" / "db" / "data.sqlite"
            )
        elif sys.platform.startswith("linux"):
            paths.append(home / ".config" / "9router" / "db" / "data.sqlite")
            paths.append(home / ".local" / "share" / "9router" / "db" / "data.sqlite")
    return paths


def find_db() -> Optional[Path]:
    for p in default_db_paths():
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------
# 9router Kiro rows
# ---------------------------------------------------------------------
@dataclass
class KiroRow:
    id: str
    provider: str
    auth_type: str
    name: Optional[str]
    email: Optional[str]
    data: dict


def _is_kiro_row(provider: str, auth_type: str, data: dict) -> bool:
    p = (provider or "").lower()
    a = (auth_type or "").lower()
    t = str(data.get("type", "")).lower()
    psd = data.get("providerSpecificData") or {}
    if t == "kiro" or "kiro" in p:
        return True
    blob = (str(data.get("profile_arn", "")) + str(psd.get("profileArn", ""))
            + str(psd.get("startUrl", "")) + str(data.get("start_url", ""))).lower()
    if "codewhisperer" in blob or "awsapps.com" in blob:
        return True
    if a == "idc" or str(psd.get("authMethod", "")).lower() == "idc":
        return True
    return False


def list_kiro_rows(db_path: Path) -> list[KiroRow]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            "SELECT id, provider, authType, name, email, data FROM providerConnections"
        )
        out: list[KiroRow] = []
        for row_id, provider, auth_type, name, email, data_text in cur:
            try:
                data = json.loads(data_text) if data_text else {}
            except Exception:
                data = {}
            if not isinstance(data, dict):
                continue
            if _is_kiro_row(provider or "", auth_type or "", data):
                out.append(KiroRow(id=row_id, provider=provider or "",
                                   auth_type=auth_type or "", name=name,
                                   email=email, data=data))
        return out
    finally:
        conn.close()


def _detect_shape(data: dict) -> str:
    """'oauth' (camelCase top-level + providerSpecificData) hoac 'idc' (snake_case)."""
    if isinstance(data.get("providerSpecificData"), dict):
        return "oauth"
    if "access_token" in data or data.get("auth_method") == "idc":
        return "idc"
    if "accessToken" in data:
        return "oauth"
    return "idc"


def _row_profile_arn(data: dict) -> str:
    psd = data.get("providerSpecificData")
    if isinstance(psd, dict) and psd.get("profileArn"):
        return str(psd["profileArn"])
    return str(data.get("profile_arn") or data.get("profileArn") or "")


def _row_start_url(data: dict) -> str:
    psd = data.get("providerSpecificData")
    if isinstance(psd, dict) and psd.get("startUrl"):
        return str(psd["startUrl"])
    return str(data.get("startUrl") or data.get("start_url") or "")


def _row_access_token(data: dict) -> str:
    return str(data.get("accessToken") or data.get("access_token") or "")


def _row_refresh_token(data: dict) -> str:
    return str(data.get("refreshToken") or data.get("refresh_token") or "")


def export_account_key(export: "KiroExport") -> str:
    """Khoa 1 account trong lo inject — email/token, KHONG chi profileArn.

    Nhieu user IAM cung IDC thuong CHUNG 1 profileArn (enterprise) nhung token khac nhau.
    """
    email = (export.email or "").strip().lower()
    if email:
        return f"email:{email}"
    rt = (export.refresh_token or "").strip()
    if rt:
        return f"rt:{rt[:80]}"
    at = (export.access_token or "").strip()
    if at:
        return f"at:{at[:80]}"
    arn = (export.profile_arn or "").strip()
    return f"arn:{arn}" if arn else "unknown"


def idc_directory(text: str) -> str:
    """Trich directory id 'd-xxxxxxxxxx' tu startUrl/UserId/start_url.

    'https://d-9066713dd7.awsapps.com/start' -> 'd-9066713dd7'
    'd-9066713dd7.b4981428-...'              -> 'd-9066713dd7'
    """
    if not text:
        return ""
    s = str(text)
    i = s.find("d-")
    if i < 0:
        return ""
    j = i + 2
    while j < len(s) and (s[j].isalnum()):
        j += 1
    return s[i:j]


def row_profile_arn(row_or_data) -> str:
    """Public helper: profileArn cua 1 KiroRow hoac data dict ('' neu null)."""
    data = row_or_data.data if isinstance(row_or_data, KiroRow) else row_or_data
    return _row_profile_arn(data or {})


def row_can_refresh(row_or_data) -> bool:
    """True neu row co du refreshToken + clientId + clientSecret de 9router tu
    refresh token (durable). False = cookie-only (chet sau ~1h, khong refresh)."""
    data = (row_or_data.data if isinstance(row_or_data, KiroRow) else row_or_data) or {}
    psd = data.get("providerSpecificData") or {}
    refresh = data.get("refreshToken") or data.get("refresh_token")
    cid = psd.get("clientId") or data.get("clientId") or data.get("client_id")
    csec = psd.get("clientSecret") or data.get("clientSecret") or data.get("client_secret")
    return bool(refresh and cid and csec)


def row_oidc_region(row_or_data) -> str:
    """OIDC/AWS region trong 9router (providerSpecificData.region)."""
    data = row_or_data.data if isinstance(row_or_data, KiroRow) else row_or_data
    data = data or {}
    psd = data.get("providerSpecificData") or {}
    return resolve_oidc_region(
        oidc_region=str(psd.get("oidcRegion") or data.get("oidc_region") or ""),
        psd_region=str(psd.get("region") or data.get("region") or ""),
    )


def row_kiro_region(row_or_data) -> str:
    """Kiro Q API region (providerSpecificData.kiroRegion), khong phai OIDC."""
    data = row_or_data.data if isinstance(row_or_data, KiroRow) else row_or_data
    data = data or {}
    psd = data.get("providerSpecificData") or {}
    return resolve_kiro_region(
        kiro_region=str(psd.get("kiroRegion") or data.get("kiro_region") or ""),
        region=str(data.get("kiro_region") or ""),
    )


def describe_row(r: KiroRow) -> str:
    arn = _row_profile_arn(r.data)
    short = arn.split("/")[-1] if arn else "NULL"
    d = idc_directory(_row_start_url(r.data))
    shape = _detect_shape(r.data)
    return (f"{r.id[:8]}..  {r.name or '?'}  shape={shape}  "
            f"oidc={row_oidc_region(r)}  kiro={row_kiro_region(r)}  "
            f"dir={d or '?'}  profile={short}  email={r.email or '?'}")


# ---------------------------------------------------------------------
# Parse an account export (Cookie-Editor array OR kiro-auth-token.json)
# ---------------------------------------------------------------------
@dataclass
class KiroExport:
    access_token: str = ""
    refresh_token: str = ""
    profile_arn: str = ""
    expires_at: str = ""
    idp: str = ""            # AWSIdC / Google / Github
    region: str = ""         # Kiro Q API region (Tool 2 field "region")
    oidc_region: str = ""    # IAM/OIDC region (Tool 2 field "oidc_region")
    start_url: str = ""      # https://d-xxxx.awsapps.com/start
    start_url_dir: str = ""  # d-xxxxxxxxxx
    user_id: str = ""
    auth_method: str = ""    # idc / social
    client_id: str = ""
    client_secret: str = ""
    machine_id: str = ""
    email: str = ""
    provider_name: str = ""  # Enterprise / Google ...
    source: str = ""         # 'cookie' | 'account'

    def can_create(self) -> bool:
        """Du de TAO connection moi (dung duoc ngay >= 1h)."""
        return bool(self.access_token and self.profile_arn)

    def can_refresh(self) -> bool:
        """Du field de 9router tu refresh token khi het han."""
        return bool(self.refresh_token and self.client_id and self.client_secret)


def _pick(cookies, name):
    for c in cookies:
        if isinstance(c, dict) and c.get("name") == name:
            return c
    return None


def _looks_like_cookies(data: list) -> bool:
    return any(
        isinstance(c, dict) and "name" in c and ("value" in c or "domain" in c)
        for c in data
    )


def _parse_account_dict(d: dict, source: str = "account") -> KiroExport:
    """Parse 1 dict account: kiro-auth-token.json (camelCase) HOAC JSON mua san
    (snake_case: access_token/client_id/client_secret/start_url/machine_id...).
    Cung chap nhan ca 9router 'data' blob co providerSpecificData nested.
    """
    def g(*keys):
        for k in keys:
            v = d.get(k)
            if v:
                return v
        return ""

    psd = d.get("providerSpecificData") if isinstance(d.get("providerSpecificData"), dict) else {}

    access = g("accessToken", "access_token")
    refresh = g("refreshToken", "refresh_token")
    arn = g("profileArn", "profile_arn") or psd.get("profileArn") or ""
    expires = g("expiresAt", "expires_at")
    client_id = g("clientId", "client_id") or psd.get("clientId") or ""
    client_secret = g("clientSecret", "client_secret") or psd.get("clientSecret") or ""
    machine_id = g("machineId", "machine_id")
    oidc_region = (
        g("oidc_region", "oidcRegion")
        or psd.get("oidcRegion")
        or g("IdcRegion")
        or ""
    )
    kiro_region = (
        g("kiro_region", "kiroRegion")
        or psd.get("kiroRegion")
        or g("region")
        or ""
    )
    if not oidc_region and psd.get("region") and not psd.get("kiroRegion"):
        # Row 9router cu: providerSpecificData.region = OIDC (us-east-1)
        oidc_region = str(psd.get("region"))
    if not kiro_region:
        kiro_region = DEFAULT_KIRO_REGION
    if not oidc_region:
        oidc_region = DEFAULT_OIDC_REGION
    auth_method = g("authMethod", "auth_method") or psd.get("authMethod") or ""
    start_url = g("startUrl", "start_url") or psd.get("startUrl") or ""
    email = g("email")
    provider_name = g("provider")

    d_dir = idc_directory(start_url) or idc_directory(arn)
    if not start_url and d_dir:
        start_url = f"https://{d_dir}.awsapps.com/start"
    if not auth_method:
        auth_method = "idc" if (start_url or client_id) else "social"

    return KiroExport(
        access_token=access or "", refresh_token=refresh or "", profile_arn=arn or "",
        expires_at=expires or "", region=kiro_region, oidc_region=oidc_region,
        start_url=start_url, start_url_dir=d_dir,
        auth_method=auth_method, client_id=client_id or "", client_secret=client_secret or "",
        machine_id=machine_id or "", email=email or "", provider_name=provider_name or "",
        idp=provider_name or "", source=source,
    )


def read_local_sso_creds(cache_dir: Optional[Path] = None) -> Optional[dict]:
    """Ghep kiro-auth-token.json + OIDC registration (<sha1>.json) trong SSO cache
    thanh 1 dict account day du (co client_id/client_secret -> durable).

    None neu chua login Kiro IDE. Tra ve dict snake_case dung cho _parse_account_dict.
    """
    cache = Path(cache_dir) if cache_dir else LOCAL_SSO_CACHE
    tok_file = cache / "kiro-auth-token.json"
    if not tok_file.exists():
        return None
    try:
        tok = json.loads(tok_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    # Tim OIDC registration file co clientId+clientSecret, uu tien expiresAt xa nhat (con han)
    reg: dict = {}
    best_exp = ""
    for f in cache.glob("*.json"):
        if f.name == "kiro-auth-token.json" or f.name.endswith(".meta.json"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("clientId") and d.get("clientSecret"):
            exp = str(d.get("expiresAt", ""))
            if reg == {} or exp > best_exp:
                reg, best_exp = d, exp

    return {
        "access_token": tok.get("accessToken"),
        "refresh_token": tok.get("refreshToken"),
        "profile_arn": tok.get("profileArn"),
        "expires_at": tok.get("expiresAt"),
        "auth_method": tok.get("authMethod"),
        "provider": tok.get("provider"),
        "client_id": reg.get("clientId"),
        "client_secret": reg.get("clientSecret"),
        "region": DEFAULT_KIRO_REGION,
        "oidc_region": tok.get("region") or reg.get("region") or DEFAULT_OIDC_REGION,
        "start_url": tok.get("startUrl") or reg.get("startUrl") or "",
        "machine_id": tok.get("machineId") or "",
    }


def build_local_export(cache_dir: Optional[Path] = None) -> Optional[KiroExport]:
    """KiroExport tu account dang login Kiro IDE (local SSO cache). None neu chua login."""
    creds = read_local_sso_creds(cache_dir)
    if not creds or not creds.get("access_token"):
        return None
    return _parse_account_dict(creds, source="local-login")


def parse_kiro_export(path: Path | str) -> KiroExport:
    """Parse mot trong cac dinh dang:
        - Cookie-Editor export (array cookie tu app.kiro.dev)
        - JSON account mua san (array 1 phan tu hoac dict, snake_case day du)
        - kiro-auth-token.json (dict camelCase)
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if isinstance(data, list):
        if _looks_like_cookies(data):
            def val(n):
                c = _pick(data, n)
                return c.get("value") if c else ""
            idp = val("Idp")
            user_id = val("UserId")
            access = val("AccessToken")
            arn = val("ProfileArn")
            oidc_reg = val("IdcRegion") or DEFAULT_OIDC_REGION
            refresh = val("RefreshToken")  # social only; IDC cookie khong co
            d = idc_directory(user_id) or idc_directory(arn)
            start_url = f"https://{d}.awsapps.com/start" if d else ""
            auth_method = "idc" if (idp == "AWSIdC" or val("ApplicationArn")) else "social"
            return KiroExport(
                access_token=access or "", refresh_token=refresh or "",
                profile_arn=arn or "", idp=idp or "", region=DEFAULT_KIRO_REGION,
                oidc_region=oidc_reg,
                start_url=start_url, start_url_dir=d, user_id=user_id or "",
                auth_method=auth_method, source="cookie",
            )
        # array account mua san -> dung phan tu dict dau tien
        acct = next((x for x in data if isinstance(x, dict)), None)
        if acct is None:
            raise ValueError("JSON array rong hoac khong hop le.")
        return _parse_account_dict(acct, source="account")

    if isinstance(data, dict):
        return _parse_account_dict(data, source="account")

    raise ValueError("File khong phai cookie array / account JSON / kiro-auth-token dict.")


# ---------------------------------------------------------------------
# Match an export to the right 9router row(s)
# ---------------------------------------------------------------------
@dataclass
class MatchResult:
    exact: list[KiroRow] = field(default_factory=list)   # token hoac directory khop
    reason: str = ""


def match_export_to_rows(rows: list[KiroRow], export: KiroExport) -> MatchResult:
    """Tim row khop: access token -> email -> refresh_token -> profileArn (1 row)."""
    # 1. Access token trung (chac chan dung account)
    if export.access_token:
        tok = [r for r in rows if _row_access_token(r.data) == export.access_token]
        if tok:
            return MatchResult(exact=tok, reason="access token trung khop")
    # 2. Email trung (moi IAM user — profileArn co the giong nhau)
    if export.email:
        em = export.email.strip().lower()
        by_email = [r for r in rows if (r.email or "").strip().lower() == em]
        if by_email:
            return MatchResult(exact=by_email, reason="email trung khop")
    # 3. refresh_token trung
    if export.refresh_token:
        by_rt = [r for r in rows
                 if _row_refresh_token(r.data) == export.refresh_token]
        if by_rt:
            return MatchResult(exact=by_rt, reason="refresh_token trung khop")
    # 4. profileArn trung — chi khi DUY NHAT 1 row (tranh ghi de nham account khac)
    if export.profile_arn:
        by_arn = [r for r in rows if row_profile_arn(r) == export.profile_arn]
        if len(by_arn) == 1:
            return MatchResult(exact=by_arn, reason="profileArn trung khop (1 row)")
    # 5. IDC directory — chi khi DUY NHAT 1 row trong directory
    if export.start_url_dir:
        dirs = [r for r in rows
                if idc_directory(_row_start_url(r.data)) == export.start_url_dir]
        if len(dirs) == 1:
            return MatchResult(exact=dirs,
                               reason=f"IDC directory {export.start_url_dir} (1 row)")
    return MatchResult(exact=[], reason="khong tu dong match duoc — tao connection moi")


# ---------------------------------------------------------------------
# Apply the fix to a row
# ---------------------------------------------------------------------
def apply_export_to_row(
    db_path: Path,
    row_id: str,
    export: KiroExport,
    update_access_token: bool = True,
    access_ttl_minutes: int = 45,
) -> dict:
    """Ghi profileArn (+ optionally access token khop) vao dung shape cua row.

    Tra ve dict {'old_profile_arn', 'new_profile_arn', 'updated_access', 'shape'}.
    """
    if not export.profile_arn:
        raise ValueError(
            "Export khong co profileArn (ProfileArn cookie). Khong the fix 403.\n"
            "Hay export lai cookie tu app.kiro.dev (phai co cookie 'ProfileArn')."
        )

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("SELECT data FROM providerConnections WHERE id=?", (row_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Khong tim thay row id={row_id}")
        data = json.loads(row[0])
        shape = _detect_shape(data)
        old_arn = _row_profile_arn(data)

        now = dt.datetime.now(dt.timezone.utc)
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        expires = (now + dt.timedelta(minutes=access_ttl_minutes)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z")

        oidc_reg = export.oidc_region or DEFAULT_OIDC_REGION
        kiro_reg = export.region or DEFAULT_KIRO_REGION
        if shape == "oauth":
            psd = dict(data.get("providerSpecificData") or {})
            psd["profileArn"] = export.profile_arn
            psd["region"] = oidc_reg
            psd["kiroRegion"] = kiro_reg
            psd["oidcRegion"] = oidc_reg
            if export.auth_method:
                psd["authMethod"] = export.auth_method
            if export.client_id:
                psd["clientId"] = export.client_id
            if export.client_secret:
                psd["clientSecret"] = export.client_secret
            if export.start_url:
                psd["startUrl"] = export.start_url
            data["providerSpecificData"] = psd
            if update_access_token and export.access_token:
                data["accessToken"] = export.access_token
                data["expiresAt"] = expires
                if export.refresh_token:
                    data["refreshToken"] = export.refresh_token
            data["testStatus"] = "active"
        else:  # idc / snake_case
            data["profile_arn"] = export.profile_arn
            data["region"] = oidc_reg
            data["kiro_region"] = kiro_reg
            data["oidc_region"] = oidc_reg
            if export.client_id:
                data["client_id"] = export.client_id
            if export.client_secret:
                data["client_secret"] = export.client_secret
            if export.start_url:
                data["start_url"] = export.start_url
            if update_access_token and export.access_token:
                data["access_token"] = export.access_token
                data["expires_at"] = expires
                data["last_refresh"] = now_iso
                if export.refresh_token:
                    data["refresh_token"] = export.refresh_token

        # Clear error/backoff so 9router retries cleanly
        for k in ("errorCode", "backoffLevel", "consecutiveUseCount",
                  "lastErrorAt", "disabledUntil"):
            data.pop(k, None)

        conn.execute(
            "UPDATE providerConnections SET data=?, updatedAt=? WHERE id=?",
            (json.dumps(data, ensure_ascii=False), now_iso, row_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "old_profile_arn": old_arn or None,
        "new_profile_arn": export.profile_arn,
        "updated_access": bool(update_access_token and export.access_token),
        "shape": shape,
    }


# ---------------------------------------------------------------------
# Create a brand-new 9router Kiro connection (khong can login truoc)
# ---------------------------------------------------------------------
def create_connection(
    db_path: Path,
    export: KiroExport,
    name: Optional[str] = None,
    priority: Optional[int] = None,
    access_ttl_minutes: int = 45,
) -> dict:
    """INSERT 1 providerConnections row Kiro moi tu export (JSON mua san / cookie).

    - JSON day du (co refresh_token + client_id + client_secret) -> connection
      hoan chinh, 9router tu refresh duoc.
    - Cookie-only (chi access + profileArn) -> tao duoc nhung KHONG refresh
      (dung tot ~1h cho den khi access token het han).
    """
    if not export.can_create():
        raise ValueError("Can it nhat access_token + profileArn de tao connection moi.")

    now = dt.datetime.now(dt.timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    can_refresh = export.can_refresh()
    if can_refresh:
        # force 9router refresh ngay lan dung dau -> token tuoi (JSON mua san co the cu)
        expires = now_iso
    else:
        expires = (now + dt.timedelta(minutes=access_ttl_minutes)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z")

    oidc_reg = export.oidc_region or DEFAULT_OIDC_REGION
    kiro_reg = export.region or DEFAULT_KIRO_REGION
    psd = {
        "profileArn": export.profile_arn,
        "region": oidc_reg,
        "kiroRegion": kiro_reg,
        "oidcRegion": oidc_reg,
        "authMethod": export.auth_method or "idc",
    }
    if export.client_id:
        psd["clientId"] = export.client_id
    if export.client_secret:
        psd["clientSecret"] = export.client_secret
    if export.start_url:
        psd["startUrl"] = export.start_url
    if export.machine_id:
        psd["machineId"] = export.machine_id

    data = {
        "accessToken": export.access_token,
        "refreshToken": export.refresh_token or "",
        "expiresAt": expires,
        "testStatus": "active",
        "expiresIn": 3600,
        "providerSpecificData": psd,
    }

    cid = str(uuid.uuid4())
    nm = name or export.email or (
        export.profile_arn.split("/")[-1] if export.profile_arn else "Kiro")

    conn = sqlite3.connect(str(db_path))
    try:
        if priority is None:
            r = conn.execute(
                "SELECT COALESCE(MAX(priority), 0) + 1 FROM providerConnections"
            ).fetchone()
            priority = int(r[0]) if r and r[0] is not None else 1
        conn.execute(
            "INSERT INTO providerConnections "
            "(id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, "kiro", "oauth", nm, export.email or None, priority, 1,
             json.dumps(data, ensure_ascii=False), now_iso, now_iso),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "id": cid, "name": nm, "priority": priority,
        "can_refresh": can_refresh, "profile_arn": export.profile_arn,
    }


# ---------------------------------------------------------------------
# Live verification (exact call that 403s)
# ---------------------------------------------------------------------
def verify_token_profile(
    access_token: str,
    profile_arn: str,
    region: str = "",
    timeout: float = 30.0,
):
    """POST generateAssistantResponse. Tra ve (http_status, message).

    200 -> token + profileArn OK, 9router se hien quota.
    403 -> sai/null profileArn hoac token het han/invalid.
    """
    reg = resolve_kiro_region(region=region, profile_arn=profile_arn)
    url = kiro_q_endpoint(reg)
    body = {
        "conversationState": {
            "chatTriggerType": "MANUAL",
            "currentMessage": {
                "userInputMessage": {
                    "content": "hi", "origin": "IDE",
                    "userInputMessageContext": {},
                }
            },
            "history": [],
        },
    }
    if profile_arn:
        body["profileArn"] = profile_arn
    raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=raw, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "kiro-swapper/1.0")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            return r.status, f"OK — token + profileArn hop le (q.{reg})."
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read(800).decode("utf-8", "replace"))
            msg = payload.get("message", "")
        except Exception:
            msg = ""
        return e.code, msg or f"HTTP {e.code}"
    except Exception as e:
        return -1, f"network error: {e}"


# ---------------------------------------------------------------------
# 9router process control (auto restart so it re-reads the DB)
# ---------------------------------------------------------------------
# 9router chay nhu npm global package:
#   node <APPDATA>\npm\node_modules\9router\cli.js --tray --skip-update -p <port>
#     +-- node ...\9router\app\server.js        (server, giu DB)
#     +-- powershell ...\9router\src\cli\tray\tray.ps1   (tray icon)
#     +-- ...\9router\bin\cloudflared.exe        (tunnel)

_NINE_MARKERS = ("cli.js", "server.js", "cloudflared", "tray.ps1", "node_modules")


def _proc_cmdline(p: "psutil.Process") -> str:
    try:
        return " ".join(p.cmdline())
    except Exception:
        return ""


def find_9router_processes(exclude_pids: Optional[set] = None) -> list:
    """Tat ca tien trinh thuoc 9router (cli.js, server.js, tray.ps1, cloudflared)."""
    exclude = exclude_pids or set()
    exclude.add(os.getpid())
    out = []
    for p in psutil.process_iter(["pid", "name"]):
        if p.pid in exclude:
            continue
        cl = _proc_cmdline(p).lower()
        if "9router" in cl and any(mk in cl for mk in _NINE_MARKERS):
            out.append(p)
    return out


def is_9router_running() -> bool:
    return bool(find_9router_processes())


def capture_9router_launch() -> Optional[tuple]:
    """Chup (exe, argv, cwd) cua tien trinh root `cli.js` khi no con song."""
    for p in find_9router_processes():
        cl = _proc_cmdline(p).lower()
        if "cli.js" in cl:
            try:
                argv = p.cmdline()
            except Exception:
                continue
            try:
                exe = p.exe()
            except Exception:
                exe = argv[0] if argv else "node"
            try:
                cwd = p.cwd()
            except Exception:
                cwd = None
            return (exe, argv, cwd)
    return None


def stop_9router(log: Callable[[str], None] = print) -> int:
    """Kill toan bo cay tien trinh 9router. Tra ve so process da kill."""
    procs = find_9router_processes()
    killed = 0
    for p in procs:
        try:
            p.kill()
            killed += 1
        except Exception as e:
            log(f"WARN khong kill duoc 9router pid={p.pid}: {e}")
    if killed:
        time.sleep(1.5)
        log(f"da kill {killed} tien trinh 9router")
    else:
        log("9router khong chay (khong co gi de kill)")
    return killed


def _detached_flags() -> int:
    if sys.platform.startswith("win"):
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP -> chay nen, song doc lap
        return 0x00000008 | 0x00000200
    return 0


def start_9router(launch: Optional[tuple] = None,
                  log: Callable[[str], None] = print) -> bool:
    """Chay lai 9router. Uu tien dung lenh da chup; fallback npm shim / cli.js."""
    flags = _detached_flags()
    # 1. dung lai dung lenh root da chup
    if launch:
        exe, argv, cwd = launch
        try:
            subprocess.Popen(argv, cwd=cwd or None, creationflags=flags,
                             close_fds=True)
            log(f"da chay lai 9router: {' '.join(argv)}")
            return True
        except Exception as e:
            log(f"WARN relaunch theo lenh chup loi: {e}")

    port_args = ["--tray", "--skip-update", "-p", "20128"]
    popen_kw: dict = {"close_fds": True}
    if flags:
        popen_kw["creationflags"] = flags
    if sys.platform != "win32":
        popen_kw["start_new_session"] = True

    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA", "")
        shim = Path(appdata) / "npm" / "9router.cmd"
        if shim.exists():
            try:
                subprocess.Popen(["cmd", "/c", str(shim)] + port_args, **popen_kw)
                log(f"da chay lai 9router qua shim: {shim}")
                return True
            except Exception as e:
                log(f"WARN shim loi: {e}")
        cli = Path(appdata) / "npm" / "node_modules" / "9router" / "cli.js"
    else:
        home = Path.home()
        shims = [
            home / ".npm-global" / "bin" / "9router",
            Path("/usr/local/bin/9router"),
            home / ".local" / "bin" / "9router",
        ]
        for shim in shims:
            if shim.exists():
                try:
                    subprocess.Popen([str(shim)] + port_args, **popen_kw)
                    log(f"da chay lai 9router qua shim: {shim}")
                    return True
                except Exception as e:
                    log(f"WARN shim loi: {e}")
        cli_candidates = [
            home / ".npm-global" / "lib" / "node_modules" / "9router" / "cli.js",
            Path("/usr/local/lib/node_modules/9router/cli.js"),
            home / ".nvm" / "versions" / "node",
        ]
        cli = next((c for c in cli_candidates[:2] if c.exists()), None)
        if cli is None:
            nvm_root = cli_candidates[2]
            if nvm_root.exists():
                for node_dir in sorted(nvm_root.iterdir(), reverse=True):
                    candidate = node_dir / "lib" / "node_modules" / "9router" / "cli.js"
                    if candidate.exists():
                        cli = candidate
                        break

    if cli and Path(cli).exists():
        try:
            subprocess.Popen(["node", str(cli)] + port_args, **popen_kw)
            log(f"da chay lai 9router: node {cli}")
            return True
        except Exception as e:
            log(f"WARN node cli.js loi: {e}")
    log("KHONG chay lai duoc 9router (khong tim thay shim/cli.js). Hay mo tay.")
    return False


def restart_9router(log: Callable[[str], None] = print) -> tuple:
    """Chup lenh -> kill -> chay lai. Tra ve (so_da_kill, da_start_ok)."""
    launch = capture_9router_launch()
    if launch:
        log(f"chup lenh launch 9router: {' '.join(launch[1])}")
    killed = stop_9router(log=log)
    started = start_9router(launch=launch, log=log)
    return killed, started


# ---------------------------------------------------------------------
# Backward-compat: push active kiro-auth-token to all matching Kiro rows
# ---------------------------------------------------------------------
@dataclass
class ImportResult:
    db_path: Path
    updated: list[str]
    skipped: list[tuple[str, str]]
    created: list[str]


def import_active_token(token: dict, db_path: Optional[Path] = None,
                        target_ids: Optional[list[str]] = None) -> ImportResult:
    """(Legacy) Push 1 active kiro-auth-token dict toi cac Kiro row.

    Uu tien dung fix theo cookie export (apply_export_to_row) thay vi ham nay.
    """
    if db_path is None:
        db_path = find_db()
        if db_path is None:
            raise FileNotFoundError(
                "Khong tim thay 9router DB. Da kiem tra:\n  - "
                + "\n  - ".join(str(p) for p in default_db_paths()))

    export = KiroExport(
        access_token=token.get("accessToken") or token.get("access_token") or "",
        refresh_token=token.get("refreshToken") or token.get("refresh_token") or "",
        profile_arn=token.get("profileArn") or token.get("profile_arn") or "",
        source="auth-token",
    )
    rows = list_kiro_rows(db_path)
    if target_ids is not None:
        ids = set(target_ids)
        rows = [r for r in rows if r.id in ids]

    updated, skipped = [], []
    for r in rows:
        try:
            apply_export_to_row(db_path, r.id, export, update_access_token=True)
            updated.append(r.id)
        except Exception as e:
            skipped.append((r.id, str(e)))
    return ImportResult(db_path=db_path, updated=updated, skipped=skipped, created=[])


__all__ = [
    "default_db_paths", "find_db", "list_kiro_rows", "KiroRow",
    "describe_row", "idc_directory", "row_profile_arn", "row_can_refresh",
    "KiroExport", "parse_kiro_export",
    "LOCAL_SSO_CACHE", "read_local_sso_creds", "build_local_export",
    "MatchResult", "match_export_to_rows",
    "apply_export_to_row", "create_connection", "verify_token_profile",
    "ImportResult", "import_active_token",
    "find_9router_processes", "is_9router_running", "capture_9router_launch",
    "stop_9router", "start_9router", "restart_9router",
]
