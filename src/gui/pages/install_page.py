"""
Install page — prerequisites checklist + one-click Claude Code install + live log.
"""

import threading
import shutil
import subprocess
import customtkinter as ctk

from ..app import (
    BasePage, C,
    card_frame, label, dim_label, sub_label,
    accent_button, ghost_button, chip, hairline,
)


class StepRow(ctk.CTkFrame):
    """A single prerequisite row with status dot + name + install hint."""

    def __init__(self, parent, name, required):
        super().__init__(parent, fg_color="transparent")
        self._dot = ctk.CTkLabel(
            self, text="◌", font=ctk.CTkFont(size=14),
            text_color=C["dim"], width=20,
        )
        self._dot.pack(side="left")

        lf = ctk.CTkFrame(self, fg_color="transparent")
        lf.pack(side="left", padx=12, fill="x", expand=True)
        label(lf, name, size=13).pack(anchor="w")
        req_text = "Required" if required else "Optional"
        self._hint = sub_label(lf, req_text, size=11)
        self._hint.pack(anchor="w")

    def set_found(self, found: bool, version: str = "", hint: str = ""):
        if found:
            self._dot.configure(text="✓", text_color=C["green"])
            self._hint.configure(text=version or "Found", text_color=C["green"])
        else:
            self._dot.configure(text="✗", text_color=C["red"])
            self._hint.configure(
                text=hint[:80] if hint else "Not found",
                text_color=C["yellow"],
            )

    def set_pending(self):
        self._dot.configure(text="⟳", text_color=C["accent"])
        self._hint.configure(text="Checking…", text_color=C["dim"])


class InstallPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False
        self._busy  = False

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        self._run_prereq_check()

    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Install Claude Code",
            "Verify prerequisites and install the Claude Code CLI with one click.",
        )

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=32, pady=(0, 24))
        outer.columnconfigure(0, weight=2)
        outer.columnconfigure(1, weight=3)

        # ── Left: prerequisites ───────────────────────────────────────
        prereq_card = card_frame(outer)
        prereq_card.grid(row=0, column=0, padx=(0, 12), sticky="nsew")

        head = ctk.CTkFrame(prereq_card, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 4))
        label(head, "Prerequisites", size=14, weight="bold").pack(side="left")
        chip(head, "auto-checked", color=C["accent"],
             bg="#0e2522").pack(side="left", padx=10)

        sub_label(prereq_card,
                  "Anything missing? We'll show install hints.",
                  size=11).pack(anchor="w", padx=18, pady=(0, 8))

        self._step_rows = {}
        prereq_names = [
            ("Python 3", True),
            ("Node.js (>=18)", True),
            ("npm", True),
            ("git", False),
            ("curl", False),
        ]
        for name, required in prereq_names:
            row = StepRow(prereq_card, name, required)
            row.pack(fill="x", padx=18, pady=6)

            self._step_rows[name] = row

        ctk.CTkFrame(prereq_card, fg_color="transparent", height=6).pack()
        self._check_btn = ghost_button(
            prereq_card, "⟳  Recheck",
            self._run_prereq_check, width=120, color=C["accent"],
        )
        self._check_btn.pack(padx=18, pady=14, anchor="w")

        # ── Right: install panel ──────────────────────────────────────
        right = ctk.CTkFrame(outer, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        install_card = card_frame(right)
        install_card.pack(fill="x", pady=(0, 12))

        head2 = ctk.CTkFrame(install_card, fg_color="transparent")
        head2.pack(fill="x", padx=18, pady=(16, 4))
        label(head2, "Claude Code CLI", size=14, weight="bold").pack(side="left")
        self._status_chip_holder = ctk.CTkFrame(head2, fg_color="transparent")
        self._status_chip_holder.pack(side="left", padx=10)

        self._claude_status = dim_label(install_card, "Checking…", size=12)
        self._claude_status.pack(anchor="w", padx=18, pady=(0, 12))

        btn_row = ctk.CTkFrame(install_card, fg_color="transparent")
        btn_row.pack(anchor="w", padx=18, pady=(0, 16))
        self._install_btn = accent_button(
            btn_row, "⬇  Install Claude Code", self._do_install, width=220,
        )
        self._install_btn.pack(side="left")
        self._update_btn = ghost_button(
            btn_row, "⟳  Update", self._do_update, width=110,
            color=C["accent"],
        )
        self._update_btn.pack(side="left", padx=8)

        # Log
        log_card = card_frame(right)
        log_card.pack(fill="both", expand=True)
        head3 = ctk.CTkFrame(log_card, fg_color="transparent")
        head3.pack(fill="x", padx=18, pady=(12, 4))
        label(head3, "Live log", size=13, weight="bold",
              color=C["dim"]).pack(side="left")
        ghost_button(head3, "Clear",
                     self._clear_log, width=70, color=C["sub"]).pack(side="right")

        self._log = ctk.CTkTextbox(
            log_card,
            fg_color=C["bg"],
            text_color=C["text"],
            font=ctk.CTkFont(family="Menlo", size=12),
            corner_radius=8,
            border_width=1,
            border_color=C["border"],
            height=320,
            state="disabled",
            wrap="word",
        )
        self._log.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    # ------------------------------------------------------------------

    def _set_status_chip(self, text, color, bg):
        for w in self._status_chip_holder.winfo_children():
            w.destroy()
        chip(self._status_chip_holder, text, color=color,
             bg=bg).pack(side="left")

    def _run_prereq_check(self):
        for row in self._step_rows.values():
            row.set_pending()

        def _check():
            from ...setup.prerequisites import PrerequisiteChecker
            statuses = PrerequisiteChecker().check_all()
            self.app.after(0, lambda: self._apply_prereq(statuses))

        threading.Thread(target=_check, daemon=True).start()
        self._refresh_claude_btn()

    def _apply_prereq(self, statuses):
        for s in statuses:
            row = self._step_rows.get(s.name)
            if row:
                row.set_found(s.found, version=s.version or "",
                              hint=s.install_hint)
        self._refresh_claude_btn()

    def _refresh_claude_btn(self):
        installed = shutil.which("claude") is not None
        if installed:
            try:
                r = subprocess.run(
                    ["claude", "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                ver = (r.stdout.strip().splitlines()[0]
                       if r.returncode == 0 else "unknown")
            except Exception:
                ver = "unknown"
            self._claude_status.configure(
                text=f"Installed — {ver}", text_color=C["green"])
            self._install_btn.configure(state="disabled",
                                        text="Already Installed")
            self._set_status_chip("Installed", C["green"], "#0e2a1c")
        else:
            self._claude_status.configure(
                text="Not installed yet.", text_color=C["dim"])
            self._install_btn.configure(state="normal",
                                        text="⬇  Install Claude Code")
            self._set_status_chip("Missing", C["yellow"], "#2a1f0a")

    def _do_install(self):
        if self._busy:
            return
        self._busy = True
        self._install_btn.configure(state="disabled", text="Installing…")
        self._clear_log()

        def _run():
            from ...setup.claude_installer import ClaudeCodeInstaller
            installer = ClaudeCodeInstaller(on_log=self._append_log)
            ok = installer.install()
            if ok:
                installer.verify()
            self.app.after(0, self._on_install_done)

        threading.Thread(target=_run, daemon=True).start()

    def _on_install_done(self):
        self._busy = False
        self._refresh_claude_btn()
        installed = __import__("shutil").which("claude") is not None
        if installed:
            self.app.show_toast("Claude Code installed successfully!", kind="success")
            try:
                self.app.sidebar.refresh_status()
            except Exception:
                pass
        else:
            self.app.show_toast("Installation may have failed — check the log",
                                kind="warn")

    def _do_update(self):
        if self._busy:
            return
        self._busy = True
        self._update_btn.configure(state="disabled")
        self._clear_log()

        def _run():
            from ...setup.claude_installer import ClaudeCodeInstaller
            ClaudeCodeInstaller(on_log=self._append_log).update()
            self.app.after(0, lambda: self._update_btn.configure(state="normal"))
            self.app.after(0, lambda: setattr(self, "_busy", False))

        threading.Thread(target=_run, daemon=True).start()

    def _append_log(self, msg: str):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", msg + "\n")
            self._log.see("end")
            self._log.configure(state="disabled")
        self.app.after(0, _do)

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
