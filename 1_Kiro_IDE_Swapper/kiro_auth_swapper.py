"""Rotate account Kiro IDE bang cach swap file `kiro-auth-token.json`.

PHAT HIEN:
    Kiro IDE (Electron app) luu auth o file TEXT JSON KHONG ma hoa:
        %USERPROFILE%\\.aws\\sso\\cache\\kiro-auth-token.json
    Format:
        {
            "accessToken": "aoaAAAAA...",       <- cookie 'AccessToken' tu app.kiro.dev
            "refreshToken": "aorAAAAA...",      <- cookie 'RefreshToken' tu app.kiro.dev
            "profileArn": "arn:aws:codewhisperer:us-east-1:699475941385:profile/<id>",
            "expiresAt": "2026-05-14T07:29:35.179Z",
            "authMethod": "social",             <- "social" cho Google/Github
            "provider": "Google"
        }
    Chi can ghi de file nay -> kill Kiro.exe -> mo lai Kiro = login luon.

Module nay cung cap:
    - read_active_token() / write_active_token()
    - backup_active(name)   -> luu vao backup folder
    - rotate_to_file(path)  -> kill Kiro -> copy file -> launch
    - rotate_from_cookie_json(path, profile_arn) -> build tu cookie JSON roi rotate
    - build_from_cookies(cookies_list, profile_arn=...) -> dict
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Callable, Iterable, Optional

import psutil


# ---------------------------------------------------------------------
# Default paths (Windows / macOS / Linux)
# ---------------------------------------------------------------------
def _user_home() -> Path:
    return Path.home()


def default_kiro_sso_cache() -> Path:
    return _user_home() / ".aws" / "sso" / "cache"


def default_kiro_app() -> Path:
    if sys.platform == "darwin":
        for p in (Path("/Applications/Kiro.app"), _user_home() / "Applications" / "Kiro.app"):
            if p.exists():
                return p
        return Path("/Applications/Kiro.app")
    if sys.platform.startswith("win"):
        return Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Kiro\Kiro.exe"))
    home = _user_home()
    for p in (
        home / ".local" / "share" / "Kiro" / "kiro",
        home / ".local" / "share" / "Kiro" / "Kiro",
        home / ".local" / "bin" / "kiro",
        Path("/usr/bin/kiro"),
        Path("/opt/Kiro/kiro"),
        Path("/opt/kiro/kiro"),
    ):
        if p.exists():
            return p
    return home / ".local" / "share" / "Kiro" / "kiro"


HOME = _user_home()
KIRO_AUTH_TOKEN_PATH = default_kiro_sso_cache() / "kiro-auth-token.json"
KIRO_EXE_DEFAULT = default_kiro_app()

# Default ARN cho CodeWhisperer Free tier
DEFAULT_PROFILE_ARN = "arn:aws:codewhisperer:us-east-1:699475941385:profile/EHGA3GRVQMUK"


# ---------------------------------------------------------------------
# Active token I/O
# ---------------------------------------------------------------------

def read_active_token(path: Path = KIRO_AUTH_TOKEN_PATH) -> Optional[dict]:
    """Doc kiro-auth-token.json hien tai. None neu chua login."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _secure_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if sys.platform != "win32":
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass


def client_id_hash(client_id: str) -> str:
    """SHA1(clientId) — ten file OIDC registration trong SSO cache."""
    return hashlib.sha1(client_id.encode("utf-8")).hexdigest()


def write_device_registration(
    client_id: str,
    client_secret: str,
    cache_dir: Optional[Path] = None,
    expires_at: Optional[str] = None,
) -> Path:
    """Ghi ~/.aws/sso/cache/{clientIdHash}.json (bat buoc cho IDC login + refresh)."""
    cache = Path(cache_dir) if cache_dir else default_kiro_sso_cache()
    cid_hash = client_id_hash(client_id)
    if not expires_at:
        expires_at = _reg_expiry_from_secret(client_secret)
    reg_path = cache / f"{cid_hash}.json"
    _secure_write_json(reg_path, {
        "clientId": client_id,
        "clientSecret": client_secret,
        "expiresAt": expires_at,
    })
    return reg_path


def persist_kiro_auth(
    token: dict,
    *,
    client_id: str = "",
    client_secret: str = "",
    start_url: str = "",
    cache_dir: Optional[Path] = None,
    active_path: Optional[Path] = None,
) -> Path:
    """Ghi kiro-auth-token.json (+ OIDC reg neu IDC) theo dung schema Kiro IDE."""
    cache = Path(cache_dir) if cache_dir else default_kiro_sso_cache()
    out = Path(active_path) if active_path else cache / "kiro-auth-token.json"
    data = dict(token)

    cid = client_id or data.pop("clientId", "") or data.pop("_clientId", "")
    csec = client_secret or data.pop("clientSecret", "") or data.pop("_clientSecret", "")
    auth = str(data.get("authMethod", "")).lower()
    is_idc = auth in ("idc", "idcenter") or (cid and csec)

    if is_idc and cid and csec:
        cid_hash = client_id_hash(cid)
        data["clientIdHash"] = cid_hash
        data["authMethod"] = "IdC"
        if not data.get("provider") or data.get("provider") == "Google":
            data["provider"] = "Enterprise"
        data.setdefault("region", "us-east-1")
        if start_url:
            data["startUrl"] = start_url
        data.pop("clientId", None)
        data.pop("clientSecret", None)
        write_device_registration(cid, csec, cache_dir=cache)
    else:
        data["authMethod"] = "social"
        for k in ("clientIdHash", "clientId", "clientSecret", "startUrl", "region"):
            data.pop(k, None)

    _secure_write_json(out, data)
    return out


def write_active_token(data: dict, path: Path = KIRO_AUTH_TOKEN_PATH) -> None:
    """Ghi token vao active path. Tu dong ghi OIDC registration neu la account IDC."""
    persist_kiro_auth(
        data,
        client_id=data.get("clientId", "") or data.get("_clientId", ""),
        client_secret=data.get("clientSecret", "") or data.get("_clientSecret", ""),
        start_url=data.get("startUrl", "") or data.get("start_url", ""),
        active_path=path,
        cache_dir=path.parent,
    )


def delete_active_token(path: Path = KIRO_AUTH_TOKEN_PATH) -> bool:
    if path.exists():
        try:
            path.unlink()
            return True
        except Exception:
            return False
    return False


# ---------------------------------------------------------------------
# Process control
# ---------------------------------------------------------------------

def _is_kiro_process(name: str, cmdline: str) -> bool:
    n = (name or "").lower()
    cl = (cmdline or "").lower()
    if sys.platform == "darwin":
        return n in ("kiro", "kiro helper", "kiro helper (renderer)") or "/kiro.app/" in cl
    if sys.platform.startswith("win"):
        return n == "kiro.exe" or "kiro.exe" in cl
    return n == "kiro" or "/kiro" in cl


def kill_kiro_processes(log: Callable[[str], None] = print) -> int:
    killed = 0
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info.get("name") or ""
            try:
                cmdline = " ".join(proc.cmdline())
            except Exception:
                cmdline = ""
        except Exception:
            continue
        if not _is_kiro_process(name, cmdline):
            continue
        try:
            proc.kill()
            killed += 1
        except Exception as e:
            log(f"WARN cannot kill pid={proc.info.get('pid')}: {e}")
    if killed:
        time.sleep(1.5)
        log(f"da kill {killed} tien trinh Kiro")
    return killed


def launch_kiro(exe_path: Path = KIRO_EXE_DEFAULT, log: Callable[[str], None] = print) -> bool:
    p = Path(exe_path)
    if sys.platform == "darwin":
        if p.suffix == ".app" and p.exists():
            try:
                subprocess.Popen(["open", "-a", str(p)])
                log(f"da launch {p.name}")
                return True
            except Exception as e:
                log(f"WARN launch loi: {e}")
                return False
        try:
            subprocess.Popen(["open", "-a", "Kiro"])
            log("da launch Kiro (open -a Kiro)")
            return True
        except Exception as e:
            log(f"WARN launch loi: {e}")
            return False
    if p.exists():
        try:
            subprocess.Popen([str(p)], cwd=str(p.parent), start_new_session=True)
            log(f"da launch {p.name}")
            return True
        except Exception as e:
            log(f"WARN launch loi: {e}")
            return False
    if sys.platform.startswith("linux"):
        for cmd in (["kiro"], ["xdg-open", "kiro://"]):
            try:
                subprocess.Popen(cmd, start_new_session=True)
                log(f"da launch Kiro ({' '.join(cmd)})")
                return True
            except Exception:
                continue
    log(f"WARN khong tim thay Kiro tai {p}")
    return False


# ---------------------------------------------------------------------
# Sidecar metadata (per-account profileArn cache + nickname)
# ---------------------------------------------------------------------
# Cookie file `xxx.json` -> sidecar `xxx.json.meta.json` containing:
#   { "profileArn": "arn:aws:codewhisperer:...:profile/<id>",
#     "nickname":   "optional friendly name",
#     "note":       "optional free text" }
# Sidecar is also used for kiro-auth-token files if user wants to override.

META_SUFFIX = ".meta.json"


def meta_path_for(account_path: Path | str) -> Path:
    """Return the sidecar metadata path for an account file."""
    p = Path(account_path)
    return p.with_name(p.name + META_SUFFIX)


def is_meta_file(path: Path | str) -> bool:
    return str(path).endswith(META_SUFFIX)


def load_account_meta(account_path: Path | str) -> dict:
    """Load sidecar metadata. Empty dict if missing or invalid."""
    mp = meta_path_for(account_path)
    if not mp.exists():
        return {}
    try:
        data = json.loads(mp.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_account_meta(account_path: Path | str, meta: dict) -> Path:
    """Write sidecar metadata. Creates parent dir if needed."""
    mp = meta_path_for(account_path)
    mp.parent.mkdir(parents=True, exist_ok=True)
    # Only persist known/scalar fields to keep file tidy
    cleaned = {k: v for k, v in meta.items() if v not in (None, "")}
    mp.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")
    return mp


def delete_account_meta(account_path: Path | str) -> bool:
    mp = meta_path_for(account_path)
    if mp.exists():
        try:
            mp.unlink()
            return True
        except Exception:
            return False
    return False


# ---------------------------------------------------------------------
# Cookies (EditThisCookie format) -> Kiro auth token JSON
# ---------------------------------------------------------------------

def _pick_cookie(cookies: Iterable[dict], name: str) -> Optional[dict]:
    """Tim cookie theo ten chinh xac."""
    for c in cookies:
        if str(c.get("name", "")).strip() == name:
            return c
    return None


def profile_arn_from_cookies(cookies: Iterable[dict]) -> Optional[str]:
    """Lay profileArn THAT cua account tu cookie 'ProfileArn' trong file export.

    Cookie value cua app.kiro.dev co the bi URL-encode
    (vd 'arn%3Aaws%3Acodewhisperer%3A...'), nen decode lai.
    Tra None neu khong co cookie ProfileArn.
    """
    c = _pick_cookie(cookies, "ProfileArn")
    if not c or not c.get("value"):
        return None
    val = str(c["value"]).strip()
    if "%" in val:
        try:
            val = urllib.parse.unquote(val)
        except Exception:
            pass
    return val or None


def build_from_cookies(
    cookies: list[dict],
    profile_arn: Optional[str] = None,
    provider: Optional[str] = None,
    expires_at: Optional[str] = None,
) -> dict:
    """Build kiro-auth-token dict tu cookie JSON cua app.kiro.dev.

    Required cookies:
        AccessToken, RefreshToken
    Optional:
        Idp (Google/Github), ProfileArn (THAT cua account)

    profileArn resolve theo thu tu:
        1. profile_arn arg (neu truyen vao)
        2. cookie 'ProfileArn' trong chinh file export (dung account!)
        3. DEFAULT_PROFILE_ARN (fallback cuoi, co the sai)

    Cookie format theo EditThisCookie / Cookie-Editor extension.
    """
    acc = _pick_cookie(cookies, "AccessToken")
    refresh = _pick_cookie(cookies, "RefreshToken")
    if not acc or not acc.get("value"):
        raise ValueError("Cookie 'AccessToken' khong co trong JSON")
    if not refresh or not refresh.get("value"):
        raise ValueError("Cookie 'RefreshToken' khong co trong JSON")

    # Uu tien profileArn THAT tu cookie file (tranh dung sai account)
    if profile_arn is None:
        profile_arn = profile_arn_from_cookies(cookies) or DEFAULT_PROFILE_ARN

    if provider is None:
        idp_cookie = _pick_cookie(cookies, "Idp")
        provider = (idp_cookie.get("value") if idp_cookie else None) or "Google"

    if expires_at is None:
        exp_unix = acc.get("expirationDate")
        if exp_unix:
            iso = dt.datetime.utcfromtimestamp(float(exp_unix)).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )
        else:
            future = dt.datetime.utcnow() + dt.timedelta(hours=1)
            iso = future.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        expires_at = iso

    return {
        "accessToken": acc["value"],
        "refreshToken": refresh["value"],
        "profileArn": profile_arn,
        "expiresAt": expires_at,
        "authMethod": "social",
        "provider": provider,
    }


def build_from_cookie_json_file(
    cookie_json_path: Path | str,
    profile_arn: Optional[str] = None,
) -> dict:
    """Load cookie JSON (EditThisCookie format) roi build kiro auth token.

    profile_arn=None -> tu lay tu cookie 'ProfileArn' trong file (dung account).
    """
    cookies = json.loads(Path(cookie_json_path).read_text(encoding="utf-8"))
    if not isinstance(cookies, list):
        raise ValueError(f"Cookie JSON phai la array, got {type(cookies).__name__}")
    return build_from_cookies(cookies, profile_arn=profile_arn)


def is_cookie_json(path: Path | str) -> bool:
    """Doan xem file JSON la cookie array hay kiro-auth-token."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(data, list):
        return False
    return any(
        isinstance(c, dict) and "name" in c and ("value" in c or "domain" in c)
        for c in data
    )


def is_auth_token_json(path: Path | str) -> bool:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return False
    return isinstance(data, dict) and "accessToken" in data and "refreshToken" in data


def _first_durable_obj(data) -> Optional[dict]:
    """Lay object durable dau tien tu array/dict (snake_case access_token...)."""
    if isinstance(data, list):
        for o in data:
            if isinstance(o, dict) and (o.get("access_token") or o.get("accessToken")):
                return o
        return None
    if isinstance(data, dict) and (data.get("access_token") or data.get("accessToken")):
        return data
    return None


def is_durable_json(path: Path | str) -> bool:
    """JSON durable cua Tool 2 / IDC: array (hoac dict) snake_case co access_token +
    refresh_token + profile_arn (KHONG phai cookie array, KHONG phai kiro-auth-token)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return False
    o = _first_durable_obj(data)
    if not o:
        return False
    rt = o.get("refresh_token") or o.get("refreshToken")
    pa = o.get("profile_arn") or o.get("profileArn")
    return bool(rt and pa)


def _reg_expiry_from_secret(client_secret: str) -> str:
    """Decode client_secret (JWT) lay expirationTimestamp -> ISO. Fallback +80 ngay."""
    try:
        payload = client_secret.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8", "replace"))
        ser = data.get("serialized")
        ts = (json.loads(ser) if isinstance(ser, str) else (ser or {})).get("expirationTimestamp")
        if ts:
            return dt.datetime.utcfromtimestamp(float(ts)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        pass
    return (dt.datetime.utcnow() + dt.timedelta(days=80)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def build_from_durable(obj: dict, provider: Optional[str] = None) -> dict:
    """Build kiro-auth-token tu JSON durable (Tool 2 / IDC).

    IDC (co client_id + client_secret): authMethod=IdC, ghi them file OIDC registration.
    Social: authMethod=social, schema 6 field nhu Kiro IDE."""
    at = obj.get("access_token") or obj.get("accessToken")
    rt = obj.get("refresh_token") or obj.get("refreshToken")
    if not at or not rt:
        raise ValueError("JSON durable thieu access_token / refresh_token")
    profile = (obj.get("profile_arn") or obj.get("profileArn") or DEFAULT_PROFILE_ARN)
    expires_at = obj.get("expires_at") or obj.get("expiresAt")
    if not expires_at:
        ei = int(obj.get("expires_in") or 3600)
        expires_at = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=ei)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z")
    client_id = obj.get("client_id") or obj.get("clientId") or ""
    client_secret = obj.get("client_secret") or obj.get("clientSecret") or ""
    auth_method = str(obj.get("auth_method") or obj.get("authMethod") or "").lower()
    start_url = obj.get("start_url") or obj.get("startUrl") or ""
    region = obj.get("region") or "us-east-1"
    is_idc = auth_method == "idc" or bool(client_id and client_secret)

    if is_idc:
        token = {
            "accessToken": at,
            "refreshToken": rt,
            "profileArn": profile,
            "expiresAt": expires_at,
            "authMethod": "IdC",
            "provider": provider or obj.get("provider") or "Enterprise",
            "region": region,
            "_clientId": client_id,
            "_clientSecret": client_secret,
        }
        if start_url:
            token["startUrl"] = start_url
        return token

    prov = provider or obj.get("provider") or "Google"
    return {
        "accessToken": at,
        "refreshToken": rt,
        "profileArn": profile,
        "expiresAt": expires_at,
        "authMethod": "social",
        "provider": prov,
    }


def build_from_durable_file(path: Path | str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    obj = _first_durable_obj(data)
    if not obj:
        raise ValueError("Khong tim thay object durable trong file")
    return build_from_durable(obj)


# ---------------------------------------------------------------------
# Backup / Restore / Rotate
# ---------------------------------------------------------------------

def backup_active(
    name: str,
    backup_dir: Path | str,
    active_path: Path = KIRO_AUTH_TOKEN_PATH,
) -> Path:
    """Copy active kiro-auth-token.json -> backup_dir/<name>.kiro-auth-token.json"""
    active = Path(active_path)
    if not active.exists():
        raise FileNotFoundError(f"Khong co active token tai {active} (chua login Kiro IDE?)")
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "._-@" else "_" for c in name)
    if not safe.endswith(".kiro-auth-token.json"):
        if safe.endswith(".json"):
            safe = safe[:-5]
        safe += ".kiro-auth-token.json"
    target = backup_dir / safe
    shutil.copy2(active, target)
    return target


def restore_from_file(
    src: Path | str,
    active_path: Path = KIRO_AUTH_TOKEN_PATH,
) -> None:
    """Copy file src -> active path (+ OIDC registration neu co clientIdHash)."""
    src = Path(src)
    if not src.exists():
        raise FileNotFoundError(f"Khong tim thay file: {src}")
    active = Path(active_path)
    active.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, active)
    if sys.platform != "win32":
        try:
            os.chmod(active, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
    try:
        tok = json.loads(active.read_text(encoding="utf-8"))
    except Exception:
        return
    cid_hash = tok.get("clientIdHash")
    if not cid_hash:
        return
    reg_src = src.parent / f"{cid_hash}.json"
    if reg_src.exists():
        reg_dst = active.parent / f"{cid_hash}.json"
        shutil.copy2(reg_src, reg_dst)
        if sys.platform != "win32":
            try:
                os.chmod(reg_dst, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass


def rotate_to_file(
    src: Path | str,
    relaunch: bool = True,
    exe_path: Path = KIRO_EXE_DEFAULT,
    active_path: Path = KIRO_AUTH_TOKEN_PATH,
    log: Callable[[str], None] = print,
) -> None:
    """Rotate Kiro IDE den account moi:
        1. Kill Kiro.exe
        2. Copy src -> active path
        3. (optional) Launch Kiro.exe
    """
    log("=== rotate Kiro IDE account ===")
    log(f"src:    {src}")
    log(f"active: {active_path}")
    kill_kiro_processes(log=log)
    restore_from_file(src, active_path=active_path)
    log("da ghi de kiro-auth-token.json")
    if relaunch:
        launch_kiro(exe_path, log=log)


def rotate_from_cookie_json(
    cookie_json_path: Path | str,
    profile_arn: Optional[str] = None,
    relaunch: bool = True,
    exe_path: Path = KIRO_EXE_DEFAULT,
    active_path: Path = KIRO_AUTH_TOKEN_PATH,
    backup_dir: Optional[Path | str] = None,
    log: Callable[[str], None] = print,
) -> None:
    """Build kiro-auth-token tu cookie JSON va rotate.

    Resolve profileArn theo thu tu uu tien:
        1. profile_arn arg truyen vao (neu khong None)
        2. Sidecar metadata <cookie>.meta.json -> "profileArn"
        3. Cookie 'ProfileArn' trong chinh file export (DUNG account)
        4. Active token hien tai (CHU Y: cua account KHAC, co the sai!)
        5. DEFAULT_PROFILE_ARN

    Optional: backup_dir -> backup active truoc khi ghi de.
    """
    if profile_arn is None:
        meta = load_account_meta(cookie_json_path)
        if meta.get("profileArn"):
            profile_arn = meta["profileArn"]
            log(f"profileArn tu sidecar: {profile_arn}")
        else:
            # Uu tien profileArn THAT nhung trong chinh cookie file
            try:
                _cookies = json.loads(
                    Path(cookie_json_path).read_text(encoding="utf-8"))
                _arn = (profile_arn_from_cookies(_cookies)
                        if isinstance(_cookies, list) else None)
            except Exception:
                _arn = None
            if _arn:
                profile_arn = _arn
                log(f"profileArn tu cookie file (dung account): {profile_arn}")
            else:
                cur = read_active_token(active_path)
                if cur and cur.get("profileArn"):
                    profile_arn = cur["profileArn"]
                    log(f"WARN profileArn fallback tu active token (co the SAI account): {profile_arn}")
                else:
                    profile_arn = DEFAULT_PROFILE_ARN
                    log(f"WARN dung DEFAULT_PROFILE_ARN (co the SAI account): {profile_arn}")

    new_token = build_from_cookie_json_file(cookie_json_path, profile_arn=profile_arn)
    log(f"new token: provider={new_token['provider']}, expiresAt={new_token['expiresAt']}")

    if backup_dir and Path(active_path).exists():
        try:
            ts = int(time.time())
            backup_path = backup_active(f"_previous_{ts}", backup_dir, active_path)
            log(f"backup active -> {backup_path.name}")
        except Exception as e:
            log(f"WARN backup loi: {e}")

    log("=== rotate Kiro IDE account ===")
    kill_kiro_processes(log=log)
    persist_kiro_auth(
        new_token,
        client_id=new_token.get("_clientId", ""),
        client_secret=new_token.get("_clientSecret", ""),
        start_url=new_token.get("startUrl", ""),
        active_path=active_path,
        cache_dir=Path(active_path).parent,
    )
    log(f"da ghi kiro-auth-token.json moi (provider={new_token['provider']})")
    if relaunch:
        launch_kiro(exe_path, log=log)


def rotate_smart(
    src: Path | str,
    profile_arn: Optional[str] = None,
    relaunch: bool = True,
    exe_path: Path = KIRO_EXE_DEFAULT,
    active_path: Path = KIRO_AUTH_TOKEN_PATH,
    backup_dir: Optional[Path | str] = None,
    log: Callable[[str], None] = print,
) -> None:
    """Auto-detect kieu file (cookie JSON / kiro-auth-token.json) roi rotate."""
    src = Path(src)
    if not src.exists():
        raise FileNotFoundError(f"Khong tim thay file: {src}")

    if is_auth_token_json(src):
        log("phat hien dinh dang kiro-auth-token.json -> rotate truc tiep")
        if backup_dir and Path(active_path).exists():
            try:
                ts = int(time.time())
                backup_active(f"_previous_{ts}", backup_dir, active_path)
            except Exception:
                pass
        rotate_to_file(src, relaunch=relaunch, exe_path=exe_path,
                       active_path=active_path, log=log)
    elif is_durable_json(src):
        log("phat hien JSON DURABLE (Tool 2 / IDC) -> build kiro-auth-token (schema social)")
        new_token = build_from_durable_file(src)
        log(f"  authMethod={new_token.get('authMethod')} provider={new_token.get('provider')} "
            f"profile=...{(new_token.get('profileArn') or '')[-12:]}")
        if backup_dir and Path(active_path).exists():
            try:
                backup_active(f"_previous_{int(time.time())}", backup_dir, active_path)
            except Exception:
                pass
        log("=== rotate Kiro IDE account ===")
        kill_kiro_processes(log=log)
        persist_kiro_auth(
            new_token,
            client_id=new_token.get("_clientId", ""),
            client_secret=new_token.get("_clientSecret", ""),
            start_url=new_token.get("startUrl", ""),
            active_path=active_path,
            cache_dir=Path(active_path).parent,
        )
        log("da ghi kiro-auth-token.json moi (tu JSON durable)")
        if relaunch:
            launch_kiro(exe_path, log=log)
    elif is_cookie_json(src):
        log("phat hien dinh dang cookie JSON (Cookie-Editor) -> build then rotate")
        rotate_from_cookie_json(src, profile_arn=profile_arn,
                                 relaunch=relaunch, exe_path=exe_path,
                                 active_path=active_path,
                                 backup_dir=backup_dir, log=log)
    else:
        raise ValueError(
            f"File khong khop dinh dang nao: {src}\n"
            "Phai la: kiro-auth-token.json (dict), cookie JSON (array tu Cookie-Editor), "
            "hoac JSON durable tu Tool 2 (array IDC)."
        )


# ---------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------

def describe_token(token: Optional[dict]) -> str:
    if not token:
        return "(chua login)"
    parts = []
    parts.append(f"provider={token.get('provider', '?')}")
    parts.append(f"authMethod={token.get('authMethod', '?')}")
    parts.append(f"expiresAt={token.get('expiresAt', '?')}")
    arn = token.get("profileArn", "")
    if arn:
        parts.append(f"profile={arn.split('/')[-1]}")
    return " | ".join(parts)


def parse_expires_at(expires_at: Optional[str]) -> Optional[dt.datetime]:
    """Parse ISO-8601 expiresAt string (e.g. '2026-05-21T06:04:58.000Z') to UTC datetime."""
    if not expires_at or not isinstance(expires_at, str):
        return None
    s = expires_at.strip()
    # Normalize: Python <3.11 fromisoformat doesn't accept trailing 'Z'.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return None


def expiry_status(token: Optional[dict], warn_hours: float = 24.0):
    """Classify auth-token expiry.

    Returns (status, label, color_hex) where status is one of:
        'valid'   -> con han > warn_hours
        'soon'    -> sap het han trong warn_hours toi
        'expired' -> da het han
        'unknown' -> khong parse duoc / khong phai auth-token
    """
    if not token or not isinstance(token, dict):
        return ("unknown", "?", "#7f8c8d")
    exp = parse_expires_at(token.get("expiresAt"))
    if exp is None:
        return ("unknown", "?", "#7f8c8d")
    now = dt.datetime.now(dt.timezone.utc) if exp.tzinfo else dt.datetime.utcnow()
    delta = exp - now
    secs = delta.total_seconds()
    if secs <= 0:
        return ("expired", "expired", "#e74c3c")
    if secs <= warn_hours * 3600:
        hrs = secs / 3600
        return ("soon", f"{hrs:.1f}h left", "#f1c40f")
    days = secs / 86400
    if days >= 1:
        label = f"{days:.1f}d left"
    else:
        label = f"{secs/3600:.1f}h left"
    return ("valid", label, "#2ecc71")


__all__ = [
    "KIRO_AUTH_TOKEN_PATH",
    "KIRO_EXE_DEFAULT",
    "DEFAULT_PROFILE_ARN",
    "default_kiro_sso_cache",
    "default_kiro_app",
    "client_id_hash",
    "write_device_registration",
    "persist_kiro_auth",
    "read_active_token",
    "write_active_token",
    "delete_active_token",
    "kill_kiro_processes",
    "launch_kiro",
    "build_from_cookies",
    "profile_arn_from_cookies",
    "build_from_cookie_json_file",
    "is_cookie_json",
    "is_auth_token_json",
    "is_durable_json",
    "build_from_durable",
    "build_from_durable_file",
    "backup_active",
    "restore_from_file",
    "rotate_to_file",
    "rotate_from_cookie_json",
    "rotate_smart",
    "describe_token",
    "parse_expires_at",
    "expiry_status",
    "META_SUFFIX",
    "meta_path_for",
    "is_meta_file",
    "load_account_meta",
    "save_account_meta",
    "delete_account_meta",
]
