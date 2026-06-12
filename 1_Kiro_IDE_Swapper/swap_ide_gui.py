# -*- coding: utf-8 -*-
"""TOOL 1 — Kiro IDE Swapper
Doi nhanh account Kiro IDE bang cach inject file JSON (kiro-auth-token.json hoac
cookie export tu app.kiro.dev) -> kill Kiro.exe -> mo lai = login luon.

Chay:  python swap_ide_gui.py   (hoac bam RUN.bat)
"""
from __future__ import annotations

import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk


def _is_bundled() -> bool:
    """True khi chay tu .exe (Nuitka/PyInstaller), khong phai python script."""
    if getattr(sys, "frozen", False):
        return True
    stem = Path(sys.executable).stem.lower()
    return stem not in ("python", "python3", "pythonw", "py") and not stem.startswith("python")


# tkinterdnd2 hay treo khi load tkdnd trong onefile exe -> chi bat khi chay source
_HAS_DND = False
if not _is_bundled():
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        _HAS_DND = True
    except Exception:
        pass

from kiro_auth_swapper import (
    KIRO_AUTH_TOKEN_PATH, KIRO_EXE_DEFAULT,
    read_active_token, describe_token, expiry_status,
    backup_active, restore_from_file, rotate_smart,
    is_cookie_json, is_auth_token_json, is_durable_json,
)
from i18n import t, set_lang, get_lang, LANG_DISPLAY, DISPLAY_TO_CODE, LANG_ORDER

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DEFAULT_DIR = "accounts"
_BASES = (ctk.CTk, TkinterDnD.DnDWrapper) if _HAS_DND else (ctk.CTk,)


class App(*_BASES):
    def __init__(self) -> None:
        super().__init__()
        self.title(t("Tool 1 — Kiro IDE Swapper"))
        self.geometry("980x720")
        self.minsize(860, 600)
        self.update_idletasks()

        self._dnd_ok = False
        if _HAS_DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self._dnd_ok = True
            except Exception:
                self._dnd_ok = False
        self._running = False
        self._selected: str | None = None
        self._buttons: list = []

        self._build()
        self._refresh_active()
        self._refresh_list()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        head = ctk.CTkFrame(self, corner_radius=8)
        head.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(head, text=t("🔄 KIRO IDE SWAPPER"),
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=12, pady=8)
        self._lang_menu = ctk.CTkOptionMenu(head, values=LANG_ORDER, width=120,
                                            command=self._on_lang_change)
        self._lang_menu.set(LANG_DISPLAY[get_lang()])
        self._lang_menu.pack(side="right", padx=12, pady=8)
        self._active_lbl = ctk.CTkLabel(head, text="", anchor="e", justify="right",
                                        font=ctk.CTkFont(family="Consolas", size=12))
        self._active_lbl.pack(side="right", padx=12)

        # Active token row
        row0 = ctk.CTkFrame(self, fg_color="transparent")
        row0.pack(fill="x", padx=12, pady=(2, 2))
        ctk.CTkButton(row0, text=t("↻ Refresh"), width=100, command=self._refresh_all).pack(side="left")
        b = ctk.CTkButton(row0, text=t("💾 Backup account dang login..."), width=240,
                          fg_color="#16a085", hover_color="#138d75", command=self._backup)
        b.pack(side="left", padx=6)
        self._buttons.append(b)

        # Settings
        st = ctk.CTkFrame(self, corner_radius=8)
        st.pack(fill="x", padx=10, pady=4)
        if sys.platform == "darwin":
            kiro_lbl = "Kiro.app:"
        elif sys.platform.startswith("linux"):
            kiro_lbl = "Kiro:"
        else:
            kiro_lbl = "Kiro.exe:"
        ctk.CTkLabel(st, text=kiro_lbl).grid(row=0, column=0, sticky="w", padx=(10, 4), pady=4)
        self._exe = ctk.CTkEntry(st, width=560)
        self._exe.insert(0, str(KIRO_EXE_DEFAULT))
        self._exe.grid(row=0, column=1, sticky="we", pady=4)
        ctk.CTkButton(st, text="...", width=40, command=self._browse_exe).grid(row=0, column=2, padx=6)
        self._relaunch = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(st, text=t("Mo lai Kiro sau khi swap"), variable=self._relaunch
                        ).grid(row=0, column=3, padx=10)
        st.grid_columnconfigure(1, weight=1)

        # Drop zone
        drop = ctk.CTkFrame(self, corner_radius=10, fg_color="#1f3a5f")
        drop.pack(fill="x", padx=10, pady=6)
        txt = (t("📥 KEO-THA file JSON vao day de SWAP ngay")
               if self._dnd_ok else
               t("📥 Bam 'Swap file JSON...' de chon file (cai tkinterdnd2 de keo-tha)"))
        ctk.CTkLabel(drop, text=txt, font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#5dade2").pack(pady=14)
        if self._dnd_ok:
            try:
                drop.drop_target_register(DND_FILES)
                drop.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        # Folder + actions
        fr = ctk.CTkFrame(self, fg_color="transparent")
        fr.pack(fill="x", padx=12, pady=(2, 2))
        ctk.CTkLabel(fr, text=t("Folder account:")).pack(side="left")
        self._folder = ctk.CTkEntry(fr, width=320)
        self._folder.insert(0, DEFAULT_DIR)
        self._folder.pack(side="left", padx=6)
        ctk.CTkButton(fr, text="...", width=40, command=self._browse_folder).pack(side="left")
        ctk.CTkButton(fr, text=t("↻ Scan"), width=90, command=self._refresh_list).pack(side="left", padx=6)
        b2 = ctk.CTkButton(fr, text=t("📂 Swap file JSON..."), width=180,
                           fg_color="#2471a3", hover_color="#1a5276", command=self._swap_file)
        b2.pack(side="right")
        self._buttons.append(b2)

        # List
        lst = ctk.CTkFrame(self, corner_radius=8)
        lst.pack(fill="both", expand=True, padx=10, pady=(2, 4))
        ctk.CTkLabel(lst, text=t("Cac file account trong folder (chon roi Swap):"),
                     font=ctk.CTkFont(weight="bold", size=13)).pack(anchor="w", padx=10, pady=(8, 2))
        self._list = ctk.CTkScrollableFrame(lst, label_text="")
        self._list.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        rowb = ctk.CTkFrame(lst, fg_color="transparent")
        rowb.pack(fill="x", padx=10, pady=(0, 8))
        self._rotate_btn = ctk.CTkButton(rowb, text=t("⟳ SWAP sang account da chon"), height=40,
                                         fg_color="#1e8449", hover_color="#196f3d",
                                         command=self._swap_selected)
        self._rotate_btn.pack(side="left")
        self._sel_lbl = ctk.CTkLabel(rowb, text=t("(chua chon)"), anchor="w")
        self._sel_lbl.pack(side="left", padx=12)

        # Log
        lf = ctk.CTkFrame(self, corner_radius=8)
        lf.pack(fill="both", expand=False, padx=10, pady=(0, 10))
        ctk.CTkLabel(lf, text=t("Log:"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(6, 0))
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
        snap = {"exe": self._exe.get(), "folder": self._folder.get(),
                "relaunch": self._relaunch.get()}
        set_lang(code)
        for w in self.winfo_children():
            w.destroy()
        self._buttons = []
        self._selected = None
        self._build()
        try:
            self._exe.delete(0, "end"); self._exe.insert(0, snap["exe"])
            self._folder.delete(0, "end"); self._folder.insert(0, snap["folder"])
            self._relaunch.set(snap["relaunch"])
        except Exception:
            pass
        self.title(t("Tool 1 — Kiro IDE Swapper"))
        self._refresh_active()
        self._refresh_list()

    # ------------------------------------------------------------------
    def _active_path(self) -> Path:
        return KIRO_AUTH_TOKEN_PATH

    def _refresh_all(self) -> None:
        self._refresh_active()
        self._refresh_list()

    def _refresh_active(self) -> None:
        tok = read_active_token(self._active_path())
        if not tok:
            self._active_lbl.configure(text=t("Active: (chua login Kiro IDE)"), text_color="#e67e22")
            return
        _, label, color = expiry_status(tok)
        self._active_lbl.configure(
            text=f"Active: {describe_token(tok)}   [{label}]", text_color=color)

    def _refresh_list(self) -> None:
        for w in self._list.winfo_children():
            w.destroy()
        folder = Path(self._folder.get().strip() or DEFAULT_DIR)
        if not folder.exists():
            ctk.CTkLabel(self._list, text=t("(folder chua ton tai: {path})").format(path=folder),
                         font=ctk.CTkFont(slant="italic")).pack(pady=12)
            return
        files = sorted([p for p in folder.glob("*.json")
                        if not p.name.endswith(".meta.json")])
        if not files:
            ctk.CTkLabel(self._list, text=t("(khong co file .json)"),
                         font=ctk.CTkFont(slant="italic")).pack(pady=12)
            return
        for p in files:
            self._add_row(p)

    def _add_row(self, p: Path) -> None:
        try:
            if is_auth_token_json(p):
                kind, col = "auth-token", "#27ae60"
            elif is_durable_json(p):
                kind, col = "durable", "#8e44ad"
            elif is_cookie_json(p):
                kind, col = "cookie", "#2980b9"
            else:
                kind, col = "?", "#7f8c8d"
        except Exception:
            kind, col = "?", "#7f8c8d"
        row = ctk.CTkFrame(self._list, corner_radius=4)
        row.pack(fill="x", padx=2, pady=2)
        ctk.CTkLabel(row, text=kind, width=80, height=22, fg_color=col, corner_radius=4,
                     font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(6, 8), pady=4)
        ctk.CTkLabel(row, text=p.name, anchor="w",
                     font=ctk.CTkFont(family="Consolas", size=11)).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(row, text=t("Chon"), width=70,
                      command=lambda pp=str(p): self._select(pp)).pack(side="right", padx=6)

    def _select(self, path: str) -> None:
        self._selected = path
        self._sel_lbl.configure(text=t("Da chon:") + f" {Path(path).name}", text_color="#2ecc71")

    # ------------------------------------------------------------------
    def _swap_selected(self) -> None:
        if not self._selected:
            messagebox.showwarning(t("Chua chon"), t("Hay bam 'Chon' o 1 dong truoc."))
            return
        self._do_swap(self._selected)

    def _swap_file(self) -> None:
        p = filedialog.askopenfilename(
            title="Chon file JSON (kiro-auth-token hoac cookie export)",
            filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if p:
            self._do_swap(p)

    def _on_drop(self, event) -> None:
        data = event.data
        path = data.strip()
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        path = path.split("} {")[0].strip("{}").strip()
        if path:
            self._do_swap(path)

    def _do_swap(self, src: str) -> None:
        if self._running:
            return
        if not Path(src).exists():
            messagebox.showerror(t("Khong thay file"), src)
            return
        if not messagebox.askyesno(
            t("Xac nhan SWAP"),
            t("Doi account Kiro IDE sang:") + f"\n{Path(src).name}\n\n"
            + (t("Kiro se TAT (luu cong viec truoc!) roi mo lai.")
               if sys.platform == "darwin" or sys.platform.startswith("linux")
               else t("Kiro.exe se TAT (luu cong viec truoc!) roi mo lai."))
            + "\n" + t("Tiep tuc?")):
            return
        self._set_running(True)
        self._log(f"=== SWAP -> {Path(src).name} ===")
        relaunch = self._relaunch.get()
        exe = self._exe.get().strip() or str(KIRO_EXE_DEFAULT)
        backup_dir = Path(self._folder.get().strip() or DEFAULT_DIR)

        def work():
            try:
                rotate_smart(src, relaunch=relaunch, exe_path=Path(exe),
                             active_path=self._active_path(), backup_dir=backup_dir,
                             log=self._log_ts)
                self.after(0, self._done, None)
            except Exception as e:
                self.after(0, self._done, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, err) -> None:
        self._set_running(False)
        self._refresh_all()
        if err:
            messagebox.showerror(t("Loi swap"), err)
        else:
            messagebox.showinfo(t("Xong"), t("Da swap. Mo Kiro IDE de kiem tra."))

    def _backup(self) -> None:
        if not read_active_token(self._active_path()):
            messagebox.showwarning(t("Chua login"), t("Khong co account dang login de backup."))
            return
        name = simpledialog.askstring(t("Backup"), t("Dat ten cho account dang login:"), parent=self)
        if not name:
            return
        try:
            dst = backup_active(name, Path(self._folder.get().strip() or DEFAULT_DIR),
                                self._active_path())
            self._log(f"backup -> {dst}")
            self._refresh_list()
            messagebox.showinfo(t("Da backup"), str(dst))
        except Exception as e:
            messagebox.showerror(t("Loi backup"), str(e))

    def _browse_exe(self) -> None:
        if sys.platform == "darwin":
            p = filedialog.askdirectory(title="Chon Kiro.app (thu muc .app)")
        elif sys.platform.startswith("linux"):
            p = filedialog.askopenfilename(
                title="Chon file kiro (binary)",
                filetypes=[("All", "*.*")])
        else:
            p = filedialog.askopenfilename(
                title="Chon Kiro.exe",
                filetypes=[("exe", "*.exe"), ("All", "*.*")])
        if p:
            self._exe.delete(0, "end")
            self._exe.insert(0, p)

    def _browse_folder(self) -> None:
        p = filedialog.askdirectory(title="Chon folder account")
        if p:
            self._folder.delete(0, "end")
            self._folder.insert(0, p)
            self._refresh_list()

    # ------------------------------------------------------------------
    def _set_running(self, r: bool) -> None:
        self._running = r
        state = "disabled" if r else "normal"
        self._rotate_btn.configure(state=state)
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
    try:
        App().mainloop()
    except Exception:
        if _is_bundled():
            try:
                messagebox.showerror(
                    "Kiro IDE Swapper — loi",
                    traceback.format_exc(limit=8),
                )
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
