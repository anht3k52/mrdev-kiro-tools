# -*- coding: utf-8 -*-
"""auto_login_cli.py — Auto login Kiro IDC (device-code) hang loat tu file account.

Doc file account (xlsx: Email|Password | txt: email:password) -> mo Chromium SACH
-> tu login (tu doi pass lan dau neu can) -> poll token durable -> xuat JSON.

Vi du:
  python auto_login_cli.py --file acc.txt
  python auto_login_cli.py --file acc.xlsx --import-9router
  python auto_login_cli.py --file acc.txt --new-pass "MyNew@2026#" --headless
  python auto_login_cli.py --file acc.txt --login-pass "MatKhauHienTai@"  (da doi pass)
  python auto_login_cli.py --email a@b.com --password Temp123   (1 account nhanh)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import device_code_auth as dca
import idc_browser_login as idc


def _log(m: str) -> None:
    sys.stdout.write(m + "\n")
    sys.stdout.flush()


def run_one(acc: idc.AccountRow, start_url: str, oidc_region: str, kiro_region: str,
            new_pass: str, headless: bool,
            out_dir: Path, import_9router: bool, file_path: str | None,
            login_pass_override: str = "",
            window_index: int = 0, window_count: int = 1,
            lock=None, plog=None, debug_dir: str = "") -> bool:
    if plog is None:
        plog = _log

    def _safe_write(new_password, result):
        if not file_path:
            return
        if lock is not None:
            with lock:
                idc.write_account_result(file_path, acc, new_password, result)
        else:
            idc.write_account_result(file_path, acc, new_password, result)

    login_pw = login_pass_override or acc.password
    plog("=== bat dau ===")
    if login_pass_override:
        plog("dung mat khau tuy chinh (ghi de file)")
    start = dca.register_and_start(oidc_region=oidc_region, kiro_region=kiro_region,
                                   start_url=start_url, log=plog)
    if not start.ok:
        plog(f"register fail: {start.error}")
        _safe_write(None, "REGISTER FAIL")
        return False

    outcome = idc.drive_login(
        start.verification_uri_complete, acc.email, login_pw, new_pass,
        log=plog, headless=headless, proxy=acc.proxy,
        window_index=window_index, window_count=window_count, debug_dir=debug_dir)
    if not outcome.ok:
        plog(f"LOGIN FAIL: {outcome.error}")
        _safe_write(new_pass if outcome.changed_password else None,
                    f"LOGIN FAIL: {outcome.error}")
        return False
    plog(f"login OK (doi pass={outcome.changed_password}) -> poll token...")

    exp = dca.poll_for_token(start, fetch_profile=True, log=plog)
    if exp.error:
        plog(f"TOKEN FAIL: {exp.error}")
        _safe_write(new_pass if outcome.changed_password else None,
                    f"TOKEN FAIL: {exp.error}")
        return False
    exp.email = acc.email

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    safe = "".join(c if c.isalnum() or c in "._-@" else "_" for c in acc.email)
    out_file = out_dir / f"kiro-durable-{safe}-{ts}.json"
    out_file.write_text(json.dumps([exp.to_full_json()], ensure_ascii=False, indent=2),
                        encoding="utf-8")
    plog(f"JSON: {out_file.name} durable={exp.is_durable()} "
         f"profile_arn={exp.profile_arn or '(NULL)'}")

    note = ""
    if import_9router:
        try:
            import nine_router as nr
            db = nr.find_db()
            if db:
                if lock is not None:
                    lock.acquire()
                try:
                    kexp = nr.parse_kiro_export(str(out_file))
                    r = nr.create_connection(db, kexp)
                finally:
                    if lock is not None:
                        lock.release()
                note = f" 9router={r['id'][:8]} durable={r['can_refresh']}"
                plog(f"CREATE{note} (nho restart 9router)")
            else:
                plog("WARN: khong tim thay 9router DB")
        except Exception as e:
            plog(f"WARN 9router: {e}")

    _safe_write(new_pass if outcome.changed_password else None,
                f"OK durable={exp.is_durable()} profile={'Y' if exp.profile_arn else 'N'}{note}")
    return True


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Auto login Kiro IDC hang loat.")
    ap.add_argument("--file", help="File account .xlsx (Email|Password) hoac .txt (email:password)")
    ap.add_argument("--email", help="1 account nhanh: email")
    ap.add_argument("--password", help="1 account nhanh: password")
    ap.add_argument("--start-url", default=idc.DEFAULT_IDC_START_URL)
    ap.add_argument("--oidc-region", default=dca.DEFAULT_OIDC_REGION,
                    choices=list(dca.REGION_OPTIONS),
                    help="Region IAM Identity Center (login device-code), mac dinh us-east-1")
    ap.add_argument("--region", default=dca.DEFAULT_KIRO_REGION,
                    choices=list(dca.REGION_OPTIONS),
                    help="Kiro Q API region (9router quota), mac dinh eu-central-1")
    ap.add_argument("--new-pass", default=idc.DEFAULT_NEW_PASSWORD,
                    help="Mat khau moi khi bi bat doi lan dau")
    ap.add_argument("--login-pass", default="",
                    help="Mat khau dang nhap tuy chinh (ghi de password trong file, da doi pass)")
    ap.add_argument("--out", default="accounts", help="Thu muc xuat JSON")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--import-9router", action="store_true",
                    help="Tao connection durable trong 9router (nho restart sau do)")
    ap.add_argument("--threads", type=int, default=1,
                    help="So luong chay song song (default 1 = tuan tu)")
    ap.add_argument("--debug", action="store_true",
                    help="Chup screenshot tung buoc vao _diag_out/ de soi")
    args = ap.parse_args()
    debug_dir = "_diag_out" if args.debug else ""

    if args.file:
        accounts = idc.read_accounts_file(args.file)
    elif args.email:
        accounts = [idc.AccountRow(idx=1, email=args.email,
                                   password=args.password or "", kind="txt")]
    else:
        ap.error("Can --file HOAC --email/--password")
        return

    if not accounts:
        _log("Khong co account nao trong file."); sys.exit(1)

    login_override = (args.login_pass or "").strip()
    if login_override:
        _log("Login password: OVERRIDE (ghi de file)")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_workers = max(1, min(args.threads, len(accounts)))
    oidc_region = dca.normalize_oidc_region(args.oidc_region)
    kiro_region = dca.normalize_kiro_region(args.region)
    _log(f"Tong {len(accounts)} account · {n_workers} luong · "
         f"oidc={oidc_region} kiro={kiro_region} · "
         f"headless={args.headless} · import9router={args.import_9router}")
    ok = fail = 0

    if n_workers == 1:
        for acc in accounts:
            try:
                if run_one(acc, args.start_url, oidc_region, kiro_region, args.new_pass, args.headless,
                           out_dir, args.import_9router, args.file,
                           login_pass_override=login_override, debug_dir=debug_dir):
                    ok += 1
                else:
                    fail += 1
            except Exception as e:
                fail += 1
                _log(f"  LOI: {e}")
    else:
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        lock = threading.Lock()

        def task(i, acc):
            tag = acc.email
            plog = lambda m, t=tag: _log(f"[{t}] {m}")
            try:
                return run_one(acc, args.start_url, oidc_region, kiro_region, args.new_pass, args.headless,
                               out_dir, args.import_9router, args.file,
                               login_pass_override=login_override,
                               window_index=i, window_count=n_workers,
                               lock=lock, plog=plog, debug_dir=debug_dir)
            except Exception as e:
                _log(f"[{tag}] LOI: {e}")
                return False

        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            futs = [ex.submit(task, i, acc) for i, acc in enumerate(accounts)]
            done = 0
            for fut in as_completed(futs):
                done += 1
                if fut.result():
                    ok += 1
                else:
                    fail += 1
                _log(f">>> tien do {done}/{len(accounts)} (OK={ok} FAIL={fail})")

    _log(f"\n==== XONG: OK={ok} FAIL={fail} ====")
    if args.import_9router and ok:
        _log("Nho RESTART 9router de doc lai DB (hoac dung nut Restart trong GUI).")


if __name__ == "__main__":
    main()
