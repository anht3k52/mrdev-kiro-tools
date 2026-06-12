# -*- coding: utf-8 -*-
"""TOOL 2 — AWS Auto Login -> lay JSON durable
Doc file account (Excel/txt: email | password) -> mo Chrome SACH (Playwright)
-> tu login AWS IAM Identity Center (tu doi mat khau lan dau neu can) -> xuat JSON
durable (refresh_token + client_id + secret + profileArn) HANG LOAT, chay DA LUONG.

Chay:  python auto_login_gui.py   (hoac bam RUN.bat)
Lan dau: chay CAI_DAT.bat de cai thu vien + Chromium.
"""
from __future__ import annotations

import datetime as dt
import json
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import os
import sys

# Khi dong goi .exe (Nuitka): tro Playwright toi thu muc 'ms-playwright'.
# - Ban STANDALONE (1 folder): ms-playwright nam CANH file .exe.
# - Ban ONEFILE (1 file .exe): ms-playwright duoc bung ra thu muc TAM, nam
#   canh module dang chay (__file__), khong phai canh sys.argv[0].
# Chay .py binh thuong thi khong dung den (dung browser cache mac dinh).
if getattr(sys, "frozen", False) or "__compiled__" in globals():
    # Ban build qua plugin "playwright" cua Nuitka: trinh duyet duoc nhung vao
    #   <playwright>/driver/package/.local-browsers  -> dat PLAYWRIGHT_BROWSERS_PATH=0
    #   de playwright dung dung cho do (chay duoc ca onefile lan standalone).
    # Fallback: ban cu copy thu muc "ms-playwright" canh .exe / canh module.
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        _bundled = None
        try:
            import playwright as _pw
            _cand = (Path(_pw.__file__).resolve().parent
                     / "driver" / "package" / ".local-browsers")
            if _cand.exists() and any(_cand.iterdir()):
                _bundled = _cand
        except Exception:
            _bundled = None
        if _bundled is not None:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        else:
            _MSPW = None
            for _base in (Path(__file__).resolve().parent,
                          Path(sys.argv[0]).resolve().parent):
                _p = _base / "ms-playwright"
                if _p.exists():
                    _MSPW = _p
                    break
            if _MSPW is not None:
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_MSPW)

import device_code_auth as dca
import idc_browser_login as idc
from i18n import t, set_lang, get_lang, LANG_DISPLAY, DISPLAY_TO_CODE, LANG_ORDER

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DEFAULT_OUT = "output_json"
BOT_URL = "https://web.telegram.org/a/#8632172880"


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(t("Tool 2 — AWS Auto Login") + "   |   Telegram: @BotbanloBot")
        self.geometry("1020x760")
        self.minsize(900, 640)
        self._running = False
        self._stop = threading.Event()
        self._file_lock = threading.Lock()
        self._count_lock = threading.Lock()
        self._buttons: list = []
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        _brand = ctk.CTkLabel(self, text=t("Telegram: @BotbanloBot") + "  " + t("(bam de mo)"),
                              text_color="#3498db", cursor="hand2",
                              font=ctk.CTkFont(size=13, weight="bold", underline=True))
        _brand.pack(side="bottom", pady=(2, 6))
        _brand.bind("<Button-1>", lambda e=None: webbrowser.open(BOT_URL))
        head = ctk.CTkFrame(self, corner_radius=8)
        head.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(head, text=t("🤖 AWS AUTO LOGIN → JSON DURABLE"),
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=12, pady=8)
        self._lang_menu = ctk.CTkOptionMenu(head, values=LANG_ORDER, width=120,
                                            command=self._on_lang_change)
        self._lang_menu.set(LANG_DISPLAY[get_lang()])
        self._lang_menu.pack(side="right", padx=12, pady=8)

        # File account
        f1 = ctk.CTkFrame(self, corner_radius=8)
        f1.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(f1, text=t("File account (xlsx: Email|Password · txt: email:password):")
                     ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 0))
        self._file = ctk.CTkEntry(f1, width=720)
        self._file.grid(row=1, column=0, sticky="we", padx=(10, 4), pady=6)
        ctk.CTkButton(f1, text=t("📂 Chon file..."), width=140, command=self._browse_file
                      ).grid(row=1, column=1, padx=6)
        f1.grid_columnconfigure(0, weight=1)

        # Output folder
        f2 = ctk.CTkFrame(self, corner_radius=8)
        f2.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(f2, text=t("Thu muc xuat JSON:")).grid(row=0, column=0, sticky="w", padx=10, pady=6)
        self._out = ctk.CTkEntry(f2, width=560)
        self._out.insert(0, DEFAULT_OUT)
        self._out.grid(row=0, column=1, sticky="we", pady=6)
        ctk.CTkButton(f2, text="...", width=40, command=self._browse_out).grid(row=0, column=2, padx=6)
        f2.grid_columnconfigure(1, weight=1)

        # Params
        f3 = ctk.CTkFrame(self, corner_radius=8)
        f3.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(f3, text=t("IDC start URL:")).grid(row=0, column=0, sticky="w", padx=10, pady=6)
        self._start_url = ctk.CTkEntry(f3, width=420)
        self._start_url.insert(0, idc.DEFAULT_IDC_START_URL)
        self._start_url.grid(row=0, column=1, sticky="w", pady=6)
        ctk.CTkLabel(f3, text=t("OIDC region (login IAM):")).grid(row=0, column=2, sticky="w", padx=(16, 4))
        self._oidc_region = ctk.CTkOptionMenu(f3, values=list(dca.REGION_OPTIONS), width=130)
        self._oidc_region.set(dca.DEFAULT_OIDC_REGION)
        self._oidc_region.grid(row=0, column=3, sticky="w", pady=6)

        ctk.CTkLabel(f3, text=t("Kiro region (9router quota):")).grid(row=1, column=0, sticky="w", padx=10, pady=6)
        self._kiro_region = ctk.CTkOptionMenu(f3, values=list(dca.REGION_OPTIONS), width=130)
        self._kiro_region.set(dca.DEFAULT_KIRO_REGION)
        self._kiro_region.grid(row=1, column=1, sticky="w", pady=6)

        ctk.CTkLabel(f3, text=t("Mat khau moi (doi lan dau):")).grid(row=1, column=2, sticky="w", padx=(16, 4))
        self._new_pw = ctk.CTkEntry(f3, width=180)
        self._new_pw.insert(0, idc.DEFAULT_NEW_PASSWORD)
        self._new_pw.grid(row=1, column=3, sticky="w", pady=6)

        ctk.CTkLabel(f3, text=t("Mat khau dang nhap (tuy chinh):")).grid(
            row=2, column=0, sticky="w", padx=10, pady=6)
        self._login_pw = ctk.CTkEntry(f3, width=220, show="*")
        self._login_pw.grid(row=2, column=1, sticky="w", pady=6)
        self._override_login_pw = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            f3, text=t("Ghi de password trong file (da doi pass)"),
            variable=self._override_login_pw,
        ).grid(row=2, column=2, columnspan=2, sticky="w", padx=(16, 0))

        ctk.CTkLabel(f3, text=t("Luong song song:")).grid(row=3, column=0, sticky="w", padx=10, pady=6)
        self._threads = ctk.CTkEntry(f3, width=60, justify="center")
        self._threads.insert(0, "3")
        self._threads.grid(row=3, column=1, sticky="w", pady=6)
        self._headless = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f3, text=t("Headless (an browser)"), variable=self._headless
                        ).grid(row=3, column=2, columnspan=2, sticky="w", padx=(16, 0))

        # Run row
        f4 = ctk.CTkFrame(self, fg_color="transparent")
        f4.pack(fill="x", padx=12, pady=(2, 4))
        self._run_btn = ctk.CTkButton(f4, text=t("🚀 BAT DAU AUTO LOGIN"), height=42, width=280,
                                      fg_color="#1e8449", hover_color="#196f3d", command=self._start)
        self._run_btn.pack(side="left")
        self._buttons.append(self._run_btn)
        self._stop_btn = ctk.CTkButton(f4, text=t("⛔ Dung"), height=42, width=110,
                                       fg_color="#922b21", hover_color="#7b241c",
                                       command=self._do_stop, state="disabled")
        self._stop_btn.pack(side="left", padx=8)
        self._prog = ctk.CTkLabel(f4, text="", anchor="w", font=ctk.CTkFont(size=13, weight="bold"))
        self._prog.pack(side="left", padx=12)

        # Hint
        ctk.CTkLabel(
            self,
            text=t("Tu nhan dien 2 dang: account moi (bi bat doi pass) & account da doi pass. "
                   "Da doi pass roi -> tick 'Ghi de password' va nhap mat khau hien tai. "
                   "Account fresh khong MFA login 100% tu dong. Neu gap captcha (account bi nghi ngo) "
                   "-> tat Headless de giai tay."),
            text_color="#5dade2", font=ctk.CTkFont(size=10, slant="italic"),
            anchor="w", justify="left", wraplength=980,
        ).pack(fill="x", padx=14, pady=(0, 4))

        # Log
        lf = ctk.CTkFrame(self, corner_radius=8)
        lf.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        ctk.CTkLabel(lf, text=t("Log:"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(6, 0))
        self._log_box = ctk.CTkTextbox(lf, font=ctk.CTkFont(family="Consolas", size=11))
        self._log_box.pack(fill="both", expand=True, padx=10, pady=(2, 8))
        self._log_box.configure(state="disabled")

    def _on_lang_change(self, display: str) -> None:
        code = DISPLAY_TO_CODE.get(display, "vi")
        if self._running:
            self._lang_menu.set(LANG_DISPLAY[get_lang()])
            return
        if code == get_lang():
            return
        snap = {"file": self._file.get(), "out": self._out.get(),
                "url": self._start_url.get(), "pw": self._new_pw.get(),
                "login_pw": self._login_pw.get(),
                "override_login_pw": self._override_login_pw.get(),
                "region": self._kiro_region.get(),
                "oidc_region": self._oidc_region.get(),
                "threads": self._threads.get(), "headless": self._headless.get()}
        set_lang(code)
        for w in self.winfo_children():
            w.destroy()
        self._buttons = []
        self._build()
        try:
            self._file.delete(0, "end"); self._file.insert(0, snap["file"])
            self._out.delete(0, "end"); self._out.insert(0, snap["out"])
            self._start_url.delete(0, "end"); self._start_url.insert(0, snap["url"])
            self._new_pw.delete(0, "end"); self._new_pw.insert(0, snap["pw"])
            self._login_pw.delete(0, "end"); self._login_pw.insert(0, snap.get("login_pw", ""))
            self._override_login_pw.set(bool(snap.get("override_login_pw")))
            self._oidc_region.set(snap.get("oidc_region") or dca.DEFAULT_OIDC_REGION)
            self._kiro_region.set(snap.get("region") or dca.DEFAULT_KIRO_REGION)
            self._threads.delete(0, "end"); self._threads.insert(0, snap["threads"])
            self._headless.set(snap["headless"])
        except Exception:
            pass
        self.title(t("Tool 2 — AWS Auto Login") + "   |   Telegram: @BotbanloBot")

    # ------------------------------------------------------------------
    def _browse_file(self) -> None:
        p = filedialog.askopenfilename(
            title="Chon file account",
            filetypes=[("Account", "*.xlsx *.xlsm *.txt *.csv"), ("All", "*.*")])
        if p:
            self._file.delete(0, "end")
            self._file.insert(0, p)

    def _browse_out(self) -> None:
        p = filedialog.askdirectory(title="Chon thu muc xuat JSON")
        if p:
            self._out.delete(0, "end")
            self._out.insert(0, p)

    def _do_stop(self) -> None:
        self._stop.set()
        self._log(">>> Da yeu cau DUNG (cho cac account dang chay xong).")

    # ------------------------------------------------------------------
    def _start(self) -> None:
        if self._running:
            return
        path = self._file.get().strip()
        if not path or not Path(path).exists():
            messagebox.showerror(t("Thieu file"), t("Hay chon file account hop le."))
            return
        try:
            accounts = idc.read_accounts_file(path)
        except Exception as e:
            messagebox.showerror(t("Loi doc file"), str(e))
            return
        if not accounts:
            messagebox.showinfo(t("File trong"),
                                t("Khong doc duoc account.\nXlsx: cot A=Email, B=Password.\n"
                                  "Txt: moi dong 'email:password'."))
            return
        start_url = self._start_url.get().strip() or idc.DEFAULT_IDC_START_URL
        oidc_region = dca.normalize_oidc_region(self._oidc_region.get())
        kiro_region = dca.normalize_kiro_region(self._kiro_region.get())
        new_pw = self._new_pw.get().strip() or idc.DEFAULT_NEW_PASSWORD
        login_override = ""
        if self._override_login_pw.get():
            login_override = self._login_pw.get().strip()
            if not login_override:
                messagebox.showerror(
                    t("Thieu file"),
                    t("Bat 'ghi de password' va nhap mat khau hien tai."))
                return
        headless = self._headless.get()
        try:
            n = int(self._threads.get().strip() or "1")
        except Exception:
            n = 1
        n_workers = max(1, min(n, 12, len(accounts)))
        out_dir = Path(self._out.get().strip() or DEFAULT_OUT)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            out_dir = Path(DEFAULT_OUT); out_dir.mkdir(parents=True, exist_ok=True)

        if not messagebox.askyesno(
            t("Xac nhan"),
            t("Login {n} account?").format(n=len(accounts))
            + f"\n\nFile: {path}\nStart URL: {start_url}\n"
            + t("OIDC region:") + f" {oidc_region}\n"
            + t("Kiro region:") + f" {kiro_region}\n"
            + (t("Login password:") + " *** (ghi de file)\n" if login_override else "")
            + t("Luong song song:") + f" {n_workers}\n"
            + t("Headless:") + f" {headless}\n"
            + t("Xuat JSON ->") + f" {out_dir}"):
            return

        self._stop.clear()
        self._set_running(True)
        try:
            scr_w = self.winfo_screenwidth()
            scr_h = max(600, self.winfo_screenheight() - 60)
        except Exception:
            scr_w, scr_h = 1920, 1040
        self._log(f"=== AUTO LOGIN: {len(accounts)} account · {n_workers} luong · "
                  f"oidc={oidc_region} kiro={kiro_region} · headless={headless}"
                  + (" · login_pw=OVERRIDE" if login_override else "") + " ===")

        def work():
            counters = {"ok": 0, "fail": 0, "done": 0}
            total = len(accounts)

            def task(i, acc):
                tag = acc.email
                plog = lambda m, t=tag: self._log_ts(f"[{t}] {m}")
                if self._stop.is_set():
                    return False
                plog("=== bat dau ===")
                try:
                    return self._one(acc, start_url, oidc_region, kiro_region, new_pw, login_override,
                                     headless, out_dir, path, plog, i, n_workers, scr_w, scr_h)
                except Exception as e:
                    plog(f"LOI: {e}")
                    self._safe_write(path, acc, None, f"ERROR: {e}")
                    return False

            with ThreadPoolExecutor(max_workers=n_workers) as ex:
                futs = [ex.submit(task, i, acc) for i, acc in enumerate(accounts)]
                for fut in as_completed(futs):
                    ok = bool(fut.result())
                    with self._count_lock:
                        counters["done"] += 1
                        counters["ok" if ok else "fail"] += 1
                        d, o, f = counters["done"], counters["ok"], counters["fail"]
                    self.after(0, self._set_prog, f"{d}/{total}  OK={o} FAIL={f}")
                    self._log_ts(f">>> tien do {d}/{total} (OK={o} FAIL={f})")
            self.after(0, self._done, counters["ok"], counters["fail"])

        threading.Thread(target=work, daemon=True).start()

    def _one(self, acc, start_url, oidc_region, kiro_region, new_pw, login_override, headless,
             out_dir, file_path, plog, window_index, window_count, scr_w, scr_h) -> bool:
        login_pw = login_override or acc.password
        if login_override:
            plog("dung mat khau tuy chinh (ghi de file)")
        start = dca.register_and_start(oidc_region=oidc_region, kiro_region=kiro_region,
                                       auth_method="idc", start_url=start_url, log=plog)
        if not start.ok:
            plog(f"register fail: {start.error}")
            self._safe_write(file_path, acc, None, "REGISTER FAIL")
            return False
        outcome = idc.drive_login(
            start.verification_uri_complete, acc.email, login_pw, new_pw,
            log=plog, headless=headless, stop_event=self._stop, proxy=acc.proxy,
            window_index=window_index, window_count=window_count,
            screen_w=scr_w, screen_h=scr_h)
        if not outcome.ok:
            plog(f"login FAIL: {outcome.error}")
            self._safe_write(file_path, acc, new_pw if outcome.changed_password else None,
                             f"LOGIN FAIL: {outcome.error}")
            return False
        plog(f"login OK (doi pass={outcome.changed_password}) -> poll token...")
        exp = dca.poll_for_token(start, fetch_profile=True, stop_event=self._stop, log=plog)
        if exp.error:
            plog(f"token FAIL: {exp.error}")
            self._safe_write(file_path, acc, new_pw if outcome.changed_password else None,
                             f"TOKEN FAIL: {exp.error}")
            return False
        exp.email = acc.email
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        safe = "".join(c if c.isalnum() or c in "._-@" else "_" for c in acc.email)
        out_file = out_dir / f"kiro-durable-{safe}-{ts}.json"
        out_file.write_text(json.dumps([exp.to_full_json()], ensure_ascii=False, indent=2),
                            encoding="utf-8")
        plog(f"JSON: {out_file.name} · durable={exp.is_durable()} · "
             f"profile={'OK' if exp.profile_arn else 'NULL'}")
        self._safe_write(file_path, acc, new_pw if outcome.changed_password else None,
                         f"OK durable={exp.is_durable()} profile={'Y' if exp.profile_arn else 'N'}")
        return True

    def _safe_write(self, path, acc, new_password, result) -> None:
        with self._file_lock:
            try:
                idc.write_account_result(path, acc, new_password, result)
            except Exception:
                pass

    def _done(self, ok_n, fail_n) -> None:
        self._set_running(False)
        messagebox.showinfo(
            t("Auto login — xong"),
            t("Thanh cong:") + f" {ok_n}\n" + t("That bai:") + f" {fail_n}\n\n"
            + t("JSON da xuat vao:") + f" {self._out.get().strip() or DEFAULT_OUT}\n"
            + t("Dung Tool 3 de inject cac JSON nay vao 9router."))

    # ------------------------------------------------------------------
    def _set_running(self, r: bool) -> None:
        self._running = r
        self._run_btn.configure(state="disabled" if r else "normal")
        self._stop_btn.configure(state="normal" if r else "disabled")

    def _set_prog(self, text: str) -> None:
        self._prog.configure(text=text)

    def _log(self, m: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", m + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _log_ts(self, m: str) -> None:
        self.after(0, self._log, m)


def _selftest_browser() -> None:
    """Kiem tra playwright + Chromium chay duoc trong .exe (ghi ket qua ra file)."""
    out = Path(sys.argv[0]).resolve().parent / "selftest_result.txt"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            pg = b.new_context().new_page()
            pg.goto("about:blank")
            b.close()
        out.write_text(
            "SELFTEST_BROWSER: OK\nbrowsers_path=" +
            os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "(default)") + "\n",
            encoding="utf-8")
    except Exception as e:
        import traceback
        out.write_text("SELFTEST_BROWSER: FAIL: " + repr(e) + "\n" +
                       traceback.format_exc(), encoding="utf-8")


def _report_startup_error(exc: BaseException) -> None:
    """Ghi loi khoi dong ra file canh .exe + hien messagebox.

    Build .exe dung --windows-console-mode=disable nen neu crash luc khoi dong
    se KHONG hien gi. Ham nay giup khach thay loi + gui log de debug.
    """
    import traceback
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        log_dir = Path(sys.argv[0]).resolve().parent
    except Exception:
        log_dir = Path.cwd()
    try:
        (log_dir / "startup_error.log").write_text(
            "TOOL 2 STARTUP ERROR\n" + detail, encoding="utf-8")
    except Exception:
        pass
    try:
        import tkinter as tk
        from tkinter import messagebox as _mb
        _root = tk.Tk()
        _root.withdraw()
        _mb.showerror(
            "Tool 2 - loi khoi dong",
            "Khong mo duoc Tool 2.\n\n"
            + str(exc)
            + "\n\nDa ghi chi tiet vao file 'startup_error.log' canh file .exe.\n"
            "Thuong gap: thieu file di kem (gui THIEU folder), bi antivirus chan, "
            "hoac thieu thu muc 'ms-playwright'.")
        _root.destroy()
    except Exception:
        pass


def main() -> None:
    if "--selftest-browser" in sys.argv:
        _selftest_browser()
        return
    try:
        App().mainloop()
    except Exception as exc:  # bat moi loi khoi dong de bao khach (build tat console)
        _report_startup_error(exc)
        raise


if __name__ == "__main__":
    main()
