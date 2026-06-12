# -*- coding: utf-8 -*-
"""
device_code_auth.py — Login Kiro qua AWS SSO OIDC device-code flow,
xuat ra JSON DURABLE day du (refresh_token + client_id + client_secret + profile_arn).

Clone dung luong 9router /api/oauth/kiro/device-code:
    1. RegisterClient        -> client_id + client_secret  (DURABLE)
    2. StartDeviceAuthorization -> user_code + verification_uri (login browser)
    3. CreateToken (poll)    -> access_token + refresh_token + expiresIn (DURABLE)
    4. ListAvailableProfiles -> profile_arn  (de KHONG bi 403)

Khac voi web-refresh (cookie ~7 ngay): token o day co refresh_token that ->
9router tu refresh HANG THANG.

Config OIDC (trich tu source 9router chunks/5339.js):
    register:    https://oidc.{region}.amazonaws.com/client/register
    deviceauth:  https://oidc.{region}.amazonaws.com/device_authorization
    token:       https://oidc.{region}.amazonaws.com/token
    clientName:  kiro-oauth-client   (public)
    scopes:      codewhisperer:completions/analysis/conversations
    grantTypes:  device_code, refresh_token
    issuerUrl:   https://identitycenter.amazonaws.com/ssoins-722374e8c3c8e6c6
"""
from __future__ import annotations

import datetime as dt
import json
import ssl
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# --- Config (clone tu 9router) ---
KIRO_CLIENT_NAME = "kiro-oauth-client"
KIRO_CLIENT_TYPE = "public"
KIRO_SCOPES = [
    "codewhisperer:completions",
    "codewhisperer:analysis",
    "codewhisperer:conversations",
]
KIRO_GRANT_TYPES = [
    "urn:ietf:params:oauth:grant-type:device_code",
    "refresh_token",
]
KIRO_ISSUER_URL = "https://identitycenter.amazonaws.com/ssoins-722374e8c3c8e6c6"
BUILDER_ID_START_URL = "https://view.awsapps.com/start"

# HAI region KHAC NHAU:
# - OIDC (login IAM device-code): phai trung region IAM Identity Center cua ban
#   (IDC d-9066713dd7 thuong la us-east-1). Dung eu-central-1 o day -> HTTP 400 invalid_request.
# - Kiro Q API (quota 9router / ListAvailableProfiles): eu-central-1 cho workspace EU.
DEFAULT_OIDC_REGION = "us-east-1"
DEFAULT_KIRO_REGION = "eu-central-1"
REGION_OPTIONS = (
    "us-east-1",
    "eu-central-1",
    "eu-west-1",
    "ap-southeast-1",
)
KIRO_REGION_OPTIONS = REGION_OPTIONS  # alias

# ListAvailableProfiles (de lay profileArn) — CodeWhisperer/Q endpoint
CW_ENDPOINT_TMPL = "https://q.{region}.amazonaws.com/"
CW_LIST_PROFILES_TARGET = "AmazonCodeWhispererService.ListAvailableProfiles"
Q_GENERATE_TARGET = "generateAssistantResponse"


def normalize_region(region: str, default: str) -> str:
    r = (region or default).strip()
    return r if r in REGION_OPTIONS else default


def normalize_oidc_region(region: str) -> str:
    return normalize_region(region, DEFAULT_OIDC_REGION)


def normalize_kiro_region(region: str) -> str:
    return normalize_region(region, DEFAULT_KIRO_REGION)


def region_from_profile_arn(arn: str) -> str:
    """Trich region tu arn:aws:codewhisperer:REGION:... (neu co)."""
    parts = (arn or "").split(":")
    if len(parts) >= 4 and parts[2] == "codewhisperer" and parts[3]:
        return parts[3]
    return ""


def kiro_q_url(region: str, path: str = "") -> str:
    r = normalize_kiro_region(region)
    base = CW_ENDPOINT_TMPL.format(region=r)
    return base + path.lstrip("/") if path else base


def _oidc_base(region: str) -> str:
    return f"https://oidc.{normalize_oidc_region(region)}.amazonaws.com"


def _post_json(url: str, body: dict, headers: Optional[dict] = None,
               timeout: float = 30.0) -> tuple[int, dict]:
    raw = json.dumps(body).encode("utf-8")
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=raw, method="POST", headers=h)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            txt = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(txt)
            except Exception:
                return r.status, {"_raw": txt}
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(txt)
        except Exception:
            return e.code, {"_raw": txt}


@dataclass
class DeviceAuthStart:
    """Ket qua buoc StartDeviceAuthorization — hien cho user de login."""
    ok: bool
    client_id: str = ""
    client_secret: str = ""
    device_code: str = ""
    user_code: str = ""
    verification_uri: str = ""
    verification_uri_complete: str = ""
    expires_in: int = 0
    interval: int = 5
    oidc_region: str = DEFAULT_OIDC_REGION
    kiro_region: str = DEFAULT_KIRO_REGION
    auth_method: str = "idc"
    start_url: str = ""
    error: str = ""

    @property
    def region(self) -> str:
        """Backward compat: OIDC region dung cho poll token."""
        return self.oidc_region


@dataclass
class DurableExport:
    """JSON durable day du sau khi login xong."""
    access_token: str = ""
    refresh_token: str = ""
    expires_in: int = 0
    expires_at: str = ""
    profile_arn: str = ""
    client_id: str = ""
    client_secret: str = ""
    region: str = DEFAULT_KIRO_REGION
    oidc_region: str = DEFAULT_OIDC_REGION
    auth_method: str = "idc"
    start_url: str = ""
    email: str = ""
    error: str = ""

    def is_durable(self) -> bool:
        return bool(self.refresh_token and self.client_id and self.client_secret)

    def to_full_json(self) -> dict:
        """Dinh dang snake_case full — parse_kiro_export doc duoc + durable."""
        return {
            "type": "kiro",
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "expires_at": self.expires_at,
            "profile_arn": self.profile_arn,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "region": self.region,
            "oidc_region": self.oidc_region,
            "auth_method": self.auth_method,
            "start_url": self.start_url,
            "email": self.email,
        }


def register_and_start(
    oidc_region: str = DEFAULT_OIDC_REGION,
    kiro_region: str = DEFAULT_KIRO_REGION,
    auth_method: str = "idc",
    start_url: str = "",
    log: Callable[[str], None] = print,
    *,
    region: str = "",  # deprecated alias -> oidc_region
) -> DeviceAuthStart:
    """Buoc 1+2: RegisterClient + StartDeviceAuthorization.

    Tra ve DeviceAuthStart co user_code + verification_uri_complete de login browser.
    """
    if region:
        oidc_region = region
    oidc_region = normalize_oidc_region(oidc_region)
    kiro_region = normalize_kiro_region(kiro_region)
    log(f"device-code: OIDC={oidc_region} (login IAM) · Kiro Q={kiro_region} (9router quota)")
    auth_method = "idc" if auth_method == "idc" else "builder-id"
    start_url = (start_url or "").strip() or BUILDER_ID_START_URL

    # 1. RegisterClient
    log("device-code: RegisterClient ...")
    reg_status, reg = _post_json(
        _oidc_base(oidc_region) + "/client/register",
        {
            "clientName": KIRO_CLIENT_NAME,
            "clientType": KIRO_CLIENT_TYPE,
            "scopes": KIRO_SCOPES,
            "grantTypes": KIRO_GRANT_TYPES,
            "issuerUrl": KIRO_ISSUER_URL,
        },
    )
    client_id = reg.get("clientId")
    client_secret = reg.get("clientSecret")
    if reg_status >= 400 or not client_id or not client_secret:
        return DeviceAuthStart(
            ok=False,
            error=f"RegisterClient that bai (HTTP {reg_status}): "
                  f"{reg.get('_raw') or reg}",
        )
    log(f"  client_id: {client_id[:20]}...  (secret len={len(client_secret)})")

    # 2. StartDeviceAuthorization
    log("device-code: StartDeviceAuthorization ...")
    da_status, da = _post_json(
        _oidc_base(oidc_region) + "/device_authorization",
        {
            "clientId": client_id,
            "clientSecret": client_secret,
            "startUrl": start_url,
        },
    )
    device_code = da.get("deviceCode")
    user_code = da.get("userCode")
    if da_status >= 400 or not device_code:
        hint = ""
        if da_status == 400 and oidc_region != DEFAULT_OIDC_REGION:
            hint = (f" (Go y: OIDC region phai trung IAM Identity Center — "
                    f"thu {DEFAULT_OIDC_REGION} o muc 'OIDC region (login IAM)')")
        elif da_status == 400:
            hint = " (Kiem tra IDC start URL co dung d-xxx.awsapps.com/start khong)"
        return DeviceAuthStart(
            ok=False,
            error=f"DeviceAuthorization that bai (HTTP {da_status}): "
                  f"{da.get('_raw') or da}{hint}",
        )
    log(f"  user_code: {user_code}")
    log(f"  verify: {da.get('verificationUriComplete')}")

    return DeviceAuthStart(
        ok=True,
        client_id=client_id,
        client_secret=client_secret,
        device_code=device_code,
        user_code=user_code or "",
        verification_uri=da.get("verificationUri", ""),
        verification_uri_complete=da.get("verificationUriComplete", ""),
        expires_in=int(da.get("expiresIn") or 600),
        interval=int(da.get("interval") or 5),
        oidc_region=oidc_region,
        kiro_region=kiro_region,
        auth_method=auth_method,
        start_url=start_url,
    )


def poll_for_token(
    start: DeviceAuthStart,
    fetch_profile: bool = True,
    stop_event=None,
    log: Callable[[str], None] = print,
) -> DurableExport:
    """Buoc 3+4: poll CreateToken den khi user login xong, roi lay profileArn.

    Block den khi: co token / het han / stop_event set.
    """
    oidc_region = start.oidc_region
    kiro_region = start.kiro_region
    token_url = _oidc_base(oidc_region) + "/token"
    deadline = time.time() + start.expires_in
    interval = max(2, start.interval)

    log("device-code: cho ban login browser & dang poll token ...")
    access_token = refresh_token = ""
    expires_in = 0
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            return DurableExport(error="Da huy (stop).")
        status, tok = _post_json(token_url, {
            "clientId": start.client_id,
            "clientSecret": start.client_secret,
            "deviceCode": start.device_code,
            "grantType": "urn:ietf:params:oauth:grant-type:device_code",
        })
        access_token = tok.get("accessToken", "")
        if access_token:
            refresh_token = tok.get("refreshToken", "")
            expires_in = int(tok.get("expiresIn") or 3600)
            log("  -> nhan duoc token!")
            break
        err = tok.get("error", "")
        if err in ("authorization_pending", "slow_down", ""):
            if err == "slow_down":
                interval += 2
            time.sleep(interval)
            continue
        # loi that su
        return DurableExport(
            error=f"CreateToken loi: {err} - {tok.get('error_description') or tok}")
    if not access_token:
        return DurableExport(error="Het han cho login (khong nhan duoc token).")

    now = dt.datetime.now(dt.timezone.utc)
    expires_at = (now + dt.timedelta(seconds=expires_in)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z")

    exp = DurableExport(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        expires_at=expires_at,
        client_id=start.client_id,
        client_secret=start.client_secret,
        region=kiro_region,
        oidc_region=oidc_region,
        auth_method="idc" if start.auth_method == "idc" else "builder-id",
        start_url=start.start_url,
    )

    # 4. ListAvailableProfiles -> profileArn (de khong bi 403)
    if fetch_profile:
        log(f"device-code: ListAvailableProfiles (q.{kiro_region}) de lay profileArn ...")
        arn, email = list_profile_arn(access_token, kiro_region, log=log)
        if arn:
            exp.profile_arn = arn
            log(f"  profile_arn: {arn}")
        else:
            log("  WARN: chua lay duoc profileArn (co the can fix tay sau).")
        if email:
            exp.email = email

    return exp


def list_profile_arn(
    access_token: str,
    region: str = DEFAULT_KIRO_REGION,
    log: Callable[[str], None] = print,
) -> tuple[str, str]:
    """Goi ListAvailableProfiles -> (profile_arn, ''). '' neu khong lay duoc."""
    region = normalize_kiro_region(region)
    url = kiro_q_url(region)
    raw = json.dumps({"maxResults": 10}).encode("utf-8")
    req = urllib.request.Request(url, data=raw, method="POST", headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-amz-json-1.0",
        "X-Amz-Target": CW_LIST_PROFILES_TARGET,
        "User-Agent": "kiro-device-auth/1.0",
    })
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        log(f"  ListAvailableProfiles HTTP {e.code}: {body[:120]}")
        return "", ""
    except Exception as e:
        log(f"  ListAvailableProfiles loi: {e}")
        return "", ""

    profiles = data.get("profiles") or []
    if not profiles:
        return "", ""
    # uu tien profile co arn
    for p in profiles:
        arn = p.get("arn") or p.get("profileArn")
        if arn:
            return arn, ""
    return "", ""


__all__ = [
    "DeviceAuthStart", "DurableExport",
    "register_and_start", "poll_for_token", "list_profile_arn",
    "KIRO_CLIENT_NAME", "BUILDER_ID_START_URL",
    "DEFAULT_OIDC_REGION", "DEFAULT_KIRO_REGION",
    "REGION_OPTIONS", "KIRO_REGION_OPTIONS",
    "normalize_oidc_region", "normalize_kiro_region", "normalize_region",
    "region_from_profile_arn", "kiro_q_url",
]
