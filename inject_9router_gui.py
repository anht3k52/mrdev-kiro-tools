# -*- coding: utf-8 -*-
"""TOOL 3 — 9router Injector (Fix 403)
KEO-THA (hoac chon) file JSON durable/cookie vao -> tu parse -> match dung connection
9router -> ghi profileArn (fix 403) HOAC tao connection moi -> tu restart 9router.

Chay:  python inject_9router_gui.py   (hoac bam RUN.bat)
"""
from __future__ import annotations

import re
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

BOT_URL = "https://web.telegram.org/a/#8632172880"
_EMAIL_FROM_FNAME = re.compile(r"kiro-durable-(.+?)-\d{8}_\d{6}_\d+\.json$", re.I)


def _email_from_filename(name: str) -> str:
    m = _EMAIL_FROM_FNAME.match(name)
    return m.group(1) if m else ""


try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _HAS_DND = True
except Exception:
    _HAS_DND = False

from nine_router import (
    find_db, list_kiro_rows, describe_row, row_profile_arn, row_can_refresh,
    parse_kiro_export, match_export_to_rows, apply_export_to_row, create_connection,
    verify_token_profile, capture_9router_launch, stop_9router, start_9router,
    export_account_key,
)
from i18n import t, set_lang, get_lang, LANG_DISPLAY, DISPLAY_TO_CODE, LANG_ORDER

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_BASES = (ctk.CTk, TkinterDnD.DnDWrapper) if _HAS_DND else (ctk.CTk,)


class App(*_BASES):
    def __init__(self) -> None:
        super().__init__()
        self._dnd_ok = False
        if _HAS_DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self._dnd_ok = True
            except Exception:
                self._dnd_ok = False

        self.title(t("Tool 3 — 9router Injector") + "   |   Telegram: @BotbanloBot")
        self.geometry("1020x760")
        self.minsize(900, 640)
        self._running = False
        self._buttons: list = []
        self._list = None
        self._build()
        self._refresh_panel()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        _brand = ctk.CTkLabel(self, text="Telegram: @BotbanloBot  (bam de mo)",
                              text_color="#3498db", cursor="hand2",
                              font=ctk.CTkFont(size=13, weight="bold", underline=True))
        _brand.pack(side="bottom", pady=(2, 6))
        _brand.bind("<Button-1>", lambda e=None: webbrowser.open(BOT_URL))
        head = ctk.CTkFrame(self, corner_radius=8)
        head.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(head, text=t("⚡ 9ROUTER INJECTOR — Fix 403"),
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=12, pady=8)
        self._lang_menu = ctk.CTkOptionMenu(head, values=LANG_ORDER, width=120,
                                            command=self._on_lang_change)
        self._lang_menu.set(LANG_DISPLAY[get_lang()])
        self._lang_menu.pack(side="right", padx=8, pady=8)
        self._restart_btn = ctk.CTkButton(head, text=t("⟳ Restart 9router"), width=160,
                                           command=self._restart_only)
        self._restart_btn.pack(side="right", padx=8)
        self._buttons.append(self._restart_btn)
        ctk.CTkButton(head, text=t("↻ Refresh"), width=100, command=self._refresh_panel
                      ).pack(side="right")

        self._db_lbl = ctk.CTkLabel(self, text="", anchor="w", justify="left",
                                    font=ctk.CTkFont(family="Consolas", size=11))
        self._db_lbl.pack(fill="x", padx=14, pady=(0, 2))

        # options
        opt = ctk.CTkFrame(self, fg_color="transparent")
        opt.pack(fill="x", padx=12, pady=2)
        self._restart_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt, text=t("Tu restart 9router sau khi inject"), variable=self._restart_var
                        ).pack(side="left")
        self._verify_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt, text=t("Live verify (goi API, chac chan 200)"), variable=self._verify_var
                        ).pack(side="left", padx=(20, 0))
        b = ctk.CTkButton(opt, text=t("📥 Chon file JSON..."), width=170, fg_color="#16a085",
                          hover_color="#138d75", command=self._browse)
        b.pack(side="right")
        self._buttons.append(b)

        # drop zone
        drop = ctk.CTkFrame(self, corner_radius=10, fg_color="#14543a")
        drop.pack(fill="x", padx=10, pady=6)
        txt = (t("📥 KEO-THA (vut) file JSON vao day → tu Import + Fix 403 (tao moi neu chua co)")
               if self._dnd_ok else
               t("📥 Bam 'Chon file JSON...' (cai tkinterdnd2 de keo-tha)"))
        ctk.CTkLabel(drop, text=txt, font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#2ecc71").pack(pady=18)
        if self._dnd_ok:
            try:
                drop.drop_target_register(DND_FILES)
                drop.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        # connections list
        lst = ctk.CTkFrame(self, corner_radius=8)
        lst.pack(fill="both", expand=True, padx=10, pady=(2, 4))
        ctk.CTkLabel(lst, text=t("Kiro connections trong 9router (trang thai profileArn):"),
                     font=ctk.CTkFont(weight="bold", size=13)).pack(anchor="w", padx=10, pady=(8, 2))
        self._list = ctk.CTkScrollableFrame(lst, label_text="")
        self._list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # log
        lf = ctk.CTkFrame(self, corner_radius=8)
        lf.pack(fill="both", expand=False, padx=10, pady=(0, 10))
        ctk.CTkLabel(lf, text="Log:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(6, 0))
        self._log_box = ctk.CTkTextbox(lf, height=130, font=ctk.CTkFont(family="Consolas", size=11))
        self._log_box.pack(fill="both", expand=True, padx=10, pady=(2, 8))
        self._log_box.configure(state="disabled")

    def _on_lang_change(self, display: str) -> None:
        code = DISPLAY_TO_CODE.get(display, "vi")
        if self._running:
            self._lang_menu.set(LANG_DISPLAY[get_lang()])
            return
        if code == get_lang():
            return
        snap = {"restart": self._restart_var.get(), "verify": self._verify_var.get()}
        set_lang(code)
        for w in self.winfo_children():
            w.destroy()
        self._buttons = []
        self._build()
        try:
            self._restart_var.set(snap["restart"])
            self._verify_var.set(snap["verify"])
        except Exception:
            pass
        self.title(t("Tool 3 — 9router Injector") + "   |   Telegram: @BotbanloBot")
        self._refresh_panel()

    # ------------------------------------------------------------------
    def _refresh_panel(self) -> None:
        for w in self._list.winfo_children():
            w.destroy()
        db = find_db()
        if not db:
            self._db_lbl.configure(
                text=t("DB 9router: KHONG TIM THAY — mo 9router 1 lan roi Refresh"),
                text_color="#e74c3c")
            ctk.CTkLabel(self._list, text=t("(khong co DB 9router)"),
                         font=ctk.CTkFont(slant="italic")).pack(pady=12)
            return
        try:
            rows = list_kiro_rows(db)
        except Exception as e:
            self._db_lbl.configure(text=f"DB loi: {e}", text_color="#e74c3c")
            return
        nul = sum(1 for r in rows if not row_profile_arn(r))
        eph = sum(1 for r in rows if row_profile_arn(r) and not row_can_refresh(r))
        arns = [row_profile_arn(r) for r in rows if row_profile_arn(r)]
        dup = len(arns) - len(set(arns))
        dup_note = (f" · ⚠ {dup} " + t("acc CHUNG QUOTA") + f" ({len(set(arns))} profileArn)") if dup else ""
        color = "#e67e22" if (nul or eph or dup) else "#2ecc71"
        self._db_lbl.configure(
            text=(f"DB: {db}\n{len(rows)} Kiro · {nul} thieu profileArn (403) · "
                  f"{eph} cookie-only (chet ~1h){dup_note}"),
            text_color=color)
        if not rows:
            ctk.CTkLabel(self._list,
                         text=t("(chua co connection Kiro — vut 1 file JSON vao de TAO MOI)"),
                         font=ctk.CTkFont(slant="italic")).pack(pady=12)
            return
        for r in rows:
            self._add_row(r)

    def _add_row(self, r) -> None:
        ok = bool(row_profile_arn(r))
        durable = row_can_refresh(r)
        if not ok:
            badge, col = "403", "#c0392b"
        elif durable:
            badge, col = "🟢 OK", "#27ae60"
        else:
            badge, col = "~1h", "#e67e22"
        row = ctk.CTkFrame(self._list, corner_radius=4)
        row.pack(fill="x", padx=2, pady=2)
        ctk.CTkLabel(row, text=badge, width=52, height=22, fg_color=col, corner_radius=4,
                     font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(6, 8), pady=4)
        note = "" if durable else "   ⚠ cookie-only (~1h)"
        ctk.CTkLabel(row, text=describe_row(r) + note, anchor="w",
                     font=ctk.CTkFont(family="Consolas", size=11),
                     text_color=(None if durable else "#e67e22")).pack(
            side="left", fill="x", expand=True, padx=(0, 8))

    # ------------------------------------------------------------------
    def _browse(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Chon file JSON (durable hoac cookie export)",
            filetypes=[("JSON", "*.json *.txt"), ("All", "*.*")])
        if paths:
            self._handle(list(paths))

    def _on_drop(self, event) -> None:
        out, cur, brace = [], "", False
        for ch in event.data:
            if ch == "{":
                brace, cur = True, ""
            elif ch == "}":
                brace = False
                if cur:
                    out.append(cur)
                cur = ""
            elif ch == " " and not brace:
                if cur:
                    out.append(cur)
                cur = ""
            else:
                cur += ch
        if cur:
            out.append(cur)
        if out:
            self._handle(out)

    def _handle(self, paths: list) -> None:
        parsed, problems = [], []
        for p in paths:
            label = Path(p).name
            try:
                export = parse_kiro_export(p)
            except Exception as e:
                problems.append((label, f"parse loi: {e}"))
                continue
            if not export.can_create():
                problems.append((label, "thieu access_token hoac profileArn"))
                continue
            if not export.email:
                export.email = _email_from_filename(label)
            parsed.append((label, Path(p).stem, export))
        self._run(parsed, problems)

    def _run(self, parsed: list, problems: list) -> None:
        if self._running:
            return
        db = find_db()
        if not db:
            messagebox.showerror(t("Khong tim thay 9router DB"),
                                 t("Mo 9router it nhat 1 lan (de co DB)."))
            return
        try:
            rows = list_kiro_rows(db)
        except Exception as e:
            messagebox.showerror(t("Loi doc DB"), str(e))
            return
        plan_update, plan_create, plan_skip = [], [], []
        seen_create_keys: set[str] = set()
        for label, name, export in parsed:
            m = match_export_to_rows(rows, export)
            if m.exact:
                plan_update.append((label, name, export, m.exact))
                continue
            acct_key = export_account_key(export)
            if acct_key in seen_create_keys:
                plan_skip.append((label, export.email or acct_key))
                continue
            seen_create_keys.add(acct_key)
            plan_create.append((label, name, export))
        if not plan_update and not plan_create:
            skip_txt = ("\n\n" + t("Bo qua trung:") + "\n"
                        + "\n".join(f"  • {lb}: {who}" for lb, who in plan_skip)
                        if plan_skip else "")
            messagebox.showwarning(t("Khong xu ly duoc gi"),
                                   (skip_txt + "\n" if skip_txt else "")
                                   + ("\n".join(f"• {lb}: {r}" for lb, r in problems) or "(no input)"))
            return
        lines = []
        for label, name, export, targets in plan_update:
            short = export.profile_arn.split("/")[-1]
            for r in targets:
                lines.append(f"  • [{t('CAP NHAT')}] {label} → {r.name or r.id[:8]} (...{short})")
        for label, name, export in plan_create:
            short = export.profile_arn.split("/")[-1]
            tag = "DURABLE ✓" if export.can_refresh() else (t("tam ~1h") + " ⚠")
            who = export.email or name
            lines.append(f"  • [{t('TAO MOI')} · {tag}] {label} → {who} (...{short})")
        for label, who in plan_skip:
            lines.append(f"  • [{t('BO QUA TRUNG')}] {label} → {who}")
        skip_note = ""
        if plan_skip:
            skip_note = "\n\n" + t("Da bo qua {n} file trung account trong lo nay (cung email/token).").format(
                n=len(plan_skip))
        shared_arn = len({e.profile_arn for _, _, e in plan_create}) < len(plan_create)
        if shared_arn and plan_create:
            skip_note += "\n" + t("CANH BAO: nhieu account CHUNG profileArn — quota Kiro giong nhau, nhung moi connection co token rieng.")
        extra = (("\n\n" + t("Bo qua:") + "\n"
                  + "\n".join(f"  • {lb}: {r}" for lb, r in problems)) if problems else "")
        if not messagebox.askyesno(
            t("Xac nhan Inject → 9router"),
            t("{u} cap nhat, {c} tao moi:").format(u=len(plan_update), c=len(plan_create))
            + "\n" + "\n".join(lines) + skip_note
            + (("\n\n" + t("Sau do TU RESTART 9router.")) if self._restart_var.get() else "")
            + extra + "\n\n" + t("Tiep tuc?")):
            return
        self._set_running(True)
        threading.Thread(target=self._worker,
                         args=(db, plan_update, plan_create, problems,
                               bool(self._restart_var.get()), bool(self._verify_var.get())),
                         daemon=True).start()

    def _worker(self, db, plan_update, plan_create, problems, auto_restart, do_verify) -> None:
        try:
            launch = None
            if auto_restart:
                launch = capture_9router_launch()
                self._log_ts("9router: stop de ghi DB...")
                stop_9router(self._log_ts)
            updated = created = fail = 0
            for label, name, export, targets in plan_update:
                if do_verify and export.access_token:
                    s, msg = verify_token_profile(
                        export.access_token, export.profile_arn, export.region)
                    self._log_ts(f"verify {label}: HTTP {s} — {msg}")
                for r in targets:
                    try:
                        res = apply_export_to_row(db, r.id, export, update_access_token=True)
                        updated += 1
                        self._log_ts(f"UPDATE {r.id[:8]}.. {res['old_profile_arn']} -> {res['new_profile_arn']}")
                    except Exception as e:
                        fail += 1
                        self._log_ts(f"UPDATE FAIL {r.id[:8]}..: {e}")
            created_keys: set[str] = set()
            for label, name, export in plan_create:
                acct_key = export_account_key(export)
                if acct_key in created_keys:
                    self._log_ts(f"SKIP {label}: trung account ({export.email or acct_key})")
                    continue
                if do_verify and export.access_token:
                    s, msg = verify_token_profile(
                        export.access_token, export.profile_arn, export.region)
                    self._log_ts(f"verify {label}: HTTP {s} — {msg}")
                try:
                    res = create_connection(db, export, name=name)
                    created_keys.add(acct_key)
                    created += 1
                    self._log_ts(f"CREATE {res['id'][:8]}.. name={res['name']} "
                                 f"profile=...{res['profile_arn'].split('/')[-1]} "
                                 f"refresh={'yes(DURABLE)' if res['can_refresh'] else 'NO(~1h)'}")
                except Exception as e:
                    fail += 1
                    self._log_ts(f"CREATE FAIL {label}: {e}")
            started = None
            if auto_restart:
                self._log_ts("9router: start lai...")
                started = start_9router(launch, self._log_ts)
            self.after(0, self._done, updated, created, fail, auto_restart, started)
        except Exception as e:
            self.after(0, self._done_err, str(e))

    def _restart_only(self) -> None:
        if self._running:
            return
        self._set_running(True)
        self._log("=== Restart 9router ===")

        def work():
            try:
                launch = capture_9router_launch()
                stop_9router(self._log_ts)
                started = start_9router(launch, self._log_ts)
                self.after(0, self._done, 0, 0, 0, True, started)
            except Exception as e:
                self.after(0, self._done_err, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, updated, created, fail, auto_restart, started) -> None:
        self._set_running(False)
        self._refresh_panel()
        msg = t("Cap nhat {u} · Tao moi {c}.").format(u=updated, c=created)
        if fail:
            msg += f"  ({t('Loi')}: {fail})"
        if auto_restart:
            msg += ("\n\n" + t("9router da restart — doi vai giay, quota se hien.")
                    if started else "\n\n⚠ Khong tu restart duoc — mo tay.")
        else:
            msg += "\n\n⚠ " + t("Nho restart 9router de doc lai DB.")
        messagebox.showinfo(t("9router — xong"), msg)

    def _done_err(self, err) -> None:
        self._set_running(False)
        self._refresh_panel()
        messagebox.showerror(t("Loi"), str(err))

    # ------------------------------------------------------------------
    def _set_running(self, r: bool) -> None:
        self._running = r
        state = "disabled" if r else "normal"
        for b in self._buttons:
            try:
                b.configure(state=state)
            except Exception:
                pass

    def _log(self, m: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", m + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _log_ts(self, m: str) -> None:
        self.after(0, self._log, m)


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
