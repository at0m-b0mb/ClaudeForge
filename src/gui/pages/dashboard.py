"""
Dashboard page — welcome screen, system summary, quick actions.
"""

import shutil
import customtkinter as ctk
from ..app import BasePage, C, card_frame, label, dim_label, accent_button, badge, status_dot


class DashboardPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        self._refresh_status()

    def on_hardware_ready(self):
        if self._built:
            self._refresh_status()

    def _build(self):
        self.page_header(
            "Welcome to ClaudeForge",
            "Set up Claude Code on any machine in minutes.",
        )

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=28, pady=0)

        # ── Top row: system summary + Claude status ───────────────────
        top_row = ctk.CTkFrame(outer, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 16))
        top_row.columnconfigure(0, weight=3)
        top_row.columnconfigure(1, weight=2)

        # System summary card
        self._sys_card = card_frame(top_row)
        self._sys_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        label(self._sys_card, "System", size=12, color=C["dim"]).pack(anchor="w", padx=16, pady=(14, 2))
        self._sys_title = label(self._sys_card, "Scanning hardware…", size=16, weight="bold")
        self._sys_title.pack(anchor="w", padx=16)
        self._sys_sub = dim_label(self._sys_card, "")
        self._sys_sub.pack(anchor="w", padx=16, pady=(2, 14))

        # Claude Code status card
        self._claude_card = card_frame(top_row)
        self._claude_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        label(self._claude_card, "Claude Code", size=12, color=C["dim"]).pack(anchor="w", padx=16, pady=(14, 2))
        self._claude_status_frame = ctk.CTkFrame(self._claude_card, fg_color="transparent")
        self._claude_status_frame.pack(anchor="w", padx=16, pady=(2, 14))
        self._refresh_claude_status()

        # ── Quick action cards ────────────────────────────────────────
        label(outer, "Quick Actions", size=15, weight="bold").pack(anchor="w", pady=(0, 10))

        grid = ctk.CTkFrame(outer, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure((0, 1, 2, 3), weight=1)

        actions = [
            ("💻", "Scan Hardware",    "Detect CPU, RAM & GPU",            lambda: self.app.show_page("hardware")),
            ("⚡", "Run Benchmark",    "Score your machine's performance",  lambda: self.app.show_page("benchmark")),
            ("📦", "Install Claude",   "Full Claude Code setup",            lambda: self.app.show_page("install")),
            ("🔗", "Manage Aliases",   "Create claude-local command",       lambda: self.app.show_page("alias")),
        ]
        for i, (icon, title, sub, cmd) in enumerate(actions):
            self._action_card(grid, i, icon, title, sub, cmd)

        # ── What's new / tips ─────────────────────────────────────────
        label(outer, "Getting Started", size=15, weight="bold").pack(anchor="w", pady=(24, 10))
        tips_card = card_frame(outer)
        tips_card.pack(fill="x", pady=(0, 24))

        tips = [
            ("1", "Run Hardware Scan to detect your CPU, RAM, and GPU."),
            ("2", "Run Benchmark to get a performance score and model recommendations."),
            ("3", "Open Install to set up Claude Code CLI with one click."),
            ("4", "Open Aliases to create a `claude-local` command for offline use."),
        ]
        for num, tip in tips:
            row = ctk.CTkFrame(tips_card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=5)
            badge(row, num, C["accent"]).pack(side="left")
            dim_label(row, f"  {tip}", size=12).pack(side="left", anchor="w")

    def _action_card(self, grid, col, icon, title, subtitle, command):
        card = card_frame(grid)
        card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")
        card.configure(cursor="hand2")
        card.bind("<Button-1>", lambda e: command())

        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=28)).pack(pady=(18, 4))
        label(card, title, size=13, weight="bold").pack()
        dim_label(card, subtitle, size=11, wraplength=130).pack(pady=(2, 16))

    def _refresh_status(self):
        if self.app.system_info:
            info = self.app.system_info
            self._sys_title.configure(text=info.os_name)
            cpu = info.cpu
            self._sys_sub.configure(
                text=f"{cpu.model}  ·  {info.ram_total_gb:.0f} GB RAM"
                     + (f"  ·  {info.gpus[0].name}" if info.gpus else "")
            )
        self._refresh_claude_status()

    def _refresh_claude_status(self):
        for w in self._claude_status_frame.winfo_children():
            w.destroy()
        installed = shutil.which("claude") is not None
        dot = status_dot(self._claude_status_frame, installed,
                         "Installed" if installed else "Not installed")
        dot.pack(anchor="w")
        if installed:
            import subprocess
            try:
                r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
                ver = r.stdout.strip().splitlines()[0] if r.returncode == 0 else ""
                if ver:
                    dim_label(self._claude_status_frame, ver, size=11).pack(anchor="w", pady=(2, 0))
            except Exception:
                pass
        else:
            dim_label(self._claude_status_frame, 'Go to Install →', size=11).pack(anchor="w", pady=(2, 0))
