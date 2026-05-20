"""
Dashboard page — hero greeting, system summary, tier display, quick actions.
"""

import shutil
import subprocess
import customtkinter as ctk

from ..app import (
    BasePage, C, TIER_COLORS,
    card_frame, label, dim_label, sub_label,
    accent_button, ghost_button, chip, badge, status_dot, hairline,
)


class StatCard(ctk.CTkFrame):
    """Compact stat tile used in the metric grid."""

    def __init__(self, parent, icon, title, value, sub="", accent=None):
        super().__init__(
            parent,
            fg_color=C["card"],
            corner_radius=14,
            border_width=1,
            border_color=C["border"],
        )
        accent = accent or C["accent"]

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 0))
        ctk.CTkLabel(head, text=icon, font=ctk.CTkFont(size=18),
                     text_color=accent).pack(side="left")
        dim_label(head, "  " + title, size=11).pack(side="left")

        self._value_lbl = label(self, value, size=22, weight="bold")
        self._value_lbl.pack(anchor="w", padx=18, pady=(8, 2))

        self._sub_lbl = sub_label(self, sub, size=11)
        self._sub_lbl.pack(anchor="w", padx=18, pady=(0, 14))

    def update_value(self, value, sub=""):
        self._value_lbl.configure(text=value)
        self._sub_lbl.configure(text=sub)


class ActionCard(ctk.CTkFrame):
    """Clickable action tile."""

    def __init__(self, parent, icon, title, subtitle, command, accent=None):
        super().__init__(
            parent,
            fg_color=C["card"],
            corner_radius=14,
            border_width=1,
            border_color=C["border"],
            cursor="hand2",
        )
        accent = accent or C["accent"]
        self._accent = accent
        self._command = command

        ctk.CTkLabel(self, text=icon, font=ctk.CTkFont(size=26),
                     text_color=accent).pack(pady=(18, 4))
        label(self, title, size=13, weight="bold").pack()
        dim_label(self, subtitle, size=11, wraplength=160).pack(pady=(4, 18), padx=12)

        for w in (self, *self.winfo_children()):
            w.bind("<Button-1>", lambda e: self._command())
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_enter(self, _e):
        self.configure(border_color=self._accent, fg_color=C["card_hi"])

    def _on_leave(self, _e):
        self.configure(border_color=C["border"], fg_color=C["card"])


class DashboardPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        self._refresh()

    def on_hardware_ready(self):
        if self._built:
            self._refresh()

    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Welcome to ClaudeForge",
            "Detect hardware, benchmark, install Claude Code, run AI locally — all from one place.",
            right_widget_factory=self._build_tier_pill,
        )

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=32, pady=0)

        # ── Hero card: system summary + Claude status ─────────────────
        hero = card_frame(outer)
        hero.pack(fill="x", pady=(0, 18))
        hero_inner = ctk.CTkFrame(hero, fg_color="transparent")
        hero_inner.pack(fill="x", padx=22, pady=20)
        hero_inner.columnconfigure(0, weight=2)
        hero_inner.columnconfigure(1, weight=0)
        hero_inner.columnconfigure(2, weight=2)

        # Left: machine
        left = ctk.CTkFrame(hero_inner, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nw")
        sub_label(left, "MACHINE", size=10).pack(anchor="w")
        self._machine_name = label(left, "Scanning hardware…", size=20, weight="bold")
        self._machine_name.pack(anchor="w", pady=(4, 2))
        self._machine_sub = dim_label(left, "", size=12)
        self._machine_sub.pack(anchor="w")

        # Divider
        ctk.CTkFrame(hero_inner, width=1, fg_color=C["border"]).grid(
            row=0, column=1, sticky="ns", padx=28
        )

        # Right: Claude Code status
        right = ctk.CTkFrame(hero_inner, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nw")
        sub_label(right, "CLAUDE CODE", size=10).pack(anchor="w")
        self._claude_status_lbl = label(right, "Checking…", size=20, weight="bold")
        self._claude_status_lbl.pack(anchor="w", pady=(4, 2))
        self._claude_status_sub = dim_label(right, "", size=12)
        self._claude_status_sub.pack(anchor="w")

        # ── Stat grid ─────────────────────────────────────────────────
        stats_label = ctk.CTkFrame(outer, fg_color="transparent")
        stats_label.pack(fill="x", pady=(2, 10))
        label(stats_label, "At a glance", size=15, weight="bold").pack(side="left")
        sub_label(stats_label, "  ·  live system stats", size=11).pack(side="left")

        stats = ctk.CTkFrame(outer, fg_color="transparent")
        stats.pack(fill="x")
        for i in range(4):
            stats.columnconfigure(i, weight=1)

        self._cpu_card  = StatCard(stats, "⚙",  "CPU",
                                   "—", "", C["accent"])
        self._ram_card  = StatCard(stats, "🧠", "Memory",
                                   "—", "", C["indigo"])
        self._gpu_card  = StatCard(stats, "🎮", "GPU",
                                   "—", "", C["purple"])
        self._disk_card = StatCard(stats, "💾", "Storage",
                                   "—", "", C["pink"])
        for i, c in enumerate([self._cpu_card, self._ram_card,
                               self._gpu_card, self._disk_card]):
            c.grid(row=0, column=i, padx=6, sticky="nsew")

        # ── Quick actions ─────────────────────────────────────────────
        qa_label = ctk.CTkFrame(outer, fg_color="transparent")
        qa_label.pack(fill="x", pady=(24, 10))
        label(qa_label, "Quick actions", size=15, weight="bold").pack(side="left")

        actions_grid = ctk.CTkFrame(outer, fg_color="transparent")
        actions_grid.pack(fill="x")
        for i in range(4):
            actions_grid.columnconfigure(i, weight=1)

        actions = [
            ("💻", "Scan Hardware",  "Detect CPU, RAM, GPU & disk",
             lambda: self.app.show_page("hardware"),  C["accent"]),
            ("⚡", "Run Benchmark",  "Score your machine's performance",
             lambda: self.app.show_page("benchmark"), C["yellow"]),
            ("📦", "Install Claude", "One-click Claude Code CLI install",
             lambda: self.app.show_page("install"),   C["green"]),
            ("🔗", "Local Alias",    "Route Claude Code to Ollama",
             lambda: self.app.show_page("alias"),     C["purple"]),
        ]
        for i, (icon, title, sub, cmd, col) in enumerate(actions):
            ActionCard(actions_grid, icon, title, sub, cmd, col).grid(
                row=0, column=i, padx=6, pady=4, sticky="nsew"
            )

        # ── Getting started + Tips ────────────────────────────────────
        bot_row = ctk.CTkFrame(outer, fg_color="transparent")
        bot_row.pack(fill="both", expand=True, pady=(24, 24))
        bot_row.columnconfigure(0, weight=3)
        bot_row.columnconfigure(1, weight=2)

        # Getting Started
        gs_card = card_frame(bot_row)
        gs_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        head = ctk.CTkFrame(gs_card, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 4))
        label(head, "Getting Started", size=14, weight="bold").pack(side="left")
        chip(head, "4 steps", color=C["accent"]).pack(side="left", padx=10)

        steps = [
            ("1", "Hardware",  "Detect your CPU, RAM, and GPU.",            C["accent"]),
            ("2", "Benchmark", "Score your machine and get model picks.",   C["yellow"]),
            ("3", "Install",   "Set up the Claude Code CLI in one click.",  C["green"]),
            ("4", "Alias",     "Create a claude-local command for Ollama.", C["purple"]),
        ]
        for n, title, desc, col in steps:
            row = ctk.CTkFrame(gs_card, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=6)
            num = ctk.CTkFrame(row, fg_color=col, corner_radius=12,
                               width=26, height=26)
            num.pack(side="left")
            num.pack_propagate(False)
            ctk.CTkLabel(num, text=n,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=C["ink"]).pack(expand=True)
            box = ctk.CTkFrame(row, fg_color="transparent")
            box.pack(side="left", padx=14, fill="x", expand=True)
            label(box, title, size=12, weight="bold").pack(anchor="w")
            dim_label(box, desc, size=11).pack(anchor="w")
        ctk.CTkFrame(gs_card, fg_color="transparent", height=12).pack()

        # Tips
        tip_card = card_frame(bot_row)
        tip_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        head2 = ctk.CTkFrame(tip_card, fg_color="transparent")
        head2.pack(fill="x", padx=18, pady=(16, 4))
        label(head2, "Did you know?", size=14, weight="bold").pack(side="left")
        chip(head2, "Pro tip", color=C["purple"],
             bg="#1d1230").pack(side="left", padx=10)

        tips = [
            "Ollama exposes a native Anthropic-compatible API — no proxy needed.",
            "Apple Silicon unified memory is treated as GPU VRAM (~70% of RAM).",
            "claude-local and claude can coexist: cloud + offline, side by side.",
            "Use --report FILE in the CLI to export hardware + benchmark JSON.",
        ]
        for t in tips:
            row = ctk.CTkFrame(tip_card, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=6)
            ctk.CTkLabel(row, text="✦", font=ctk.CTkFont(size=12),
                         text_color=C["accent"]).pack(side="left", anchor="n")
            dim_label(row, "  " + t, size=11, wraplength=320).pack(
                side="left", anchor="w"
            )
        ctk.CTkFrame(tip_card, fg_color="transparent", height=12).pack()

    # ------------------------------------------------------------------

    def _build_tier_pill(self, parent):
        """A pill in the page header showing current tier (if known)."""
        self._tier_pill = ctk.CTkFrame(parent, fg_color=C["card"],
                                       corner_radius=20,
                                       border_width=1,
                                       border_color=C["border"])
        self._tier_pill.pack(anchor="e")
        self._tier_dot = ctk.CTkLabel(
            self._tier_pill, text="●",
            font=ctk.CTkFont(size=12),
            text_color=C["dim"],
        )
        self._tier_dot.pack(side="left", padx=(12, 0), pady=6)
        self._tier_text = ctk.CTkLabel(
            self._tier_pill, text="  Detecting machine…  ",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["dim"],
        )
        self._tier_text.pack(side="left", padx=(0, 12), pady=6)

    # ------------------------------------------------------------------

    def _refresh(self):
        info = self.app.system_info
        bench = self.app.bench_result

        if info:
            self._machine_name.configure(text=info.os_name)
            cpu = info.cpu
            sub_text = f"{cpu.physical_cores} cores  ·  {info.ram_total_gb:.0f} GB RAM"
            if info.gpus:
                sub_text += f"  ·  {info.gpus[0].name[:40]}"
            self._machine_sub.configure(text=sub_text)

            # Stat cards
            self._cpu_card.update_value(
                cpu.model[:24] + ("…" if len(cpu.model) > 24 else ""),
                f"{cpu.physical_cores}P / {cpu.logical_cores}L cores"
            )
            ram_used = info.ram_total_gb - info.ram_available_gb
            self._ram_card.update_value(
                f"{info.ram_total_gb:.0f} GB",
                f"{ram_used:.1f} GB in use"
            )
            if info.gpus:
                g = info.gpus[0]
                vram = f"{g.vram_mb / 1024:.1f} GB" if g.vram_mb else "Shared"
                self._gpu_card.update_value(vram, g.name[:30])
            else:
                self._gpu_card.update_value("None", "No discrete GPU")
            self._disk_card.update_value(
                f"{info.disk_free_gb:.0f} GB free",
                f"of {info.disk_total_gb:.0f} GB"
            )

        # Tier pill
        if hasattr(self, "_tier_pill"):
            if bench:
                col = TIER_COLORS.get(bench.tier, C["accent"])
                self._tier_dot.configure(text_color=col)
                self._tier_text.configure(
                    text=f"  {bench.tier.upper()} TIER  ·  {bench.overall_score:.0f}/100  ",
                    text_color=C["text"],
                )
            elif info:
                self._tier_dot.configure(text_color=C["yellow"])
                self._tier_text.configure(
                    text="  Ready — run benchmark  ",
                    text_color=C["text"],
                )

        self._refresh_claude_status()

    def _refresh_claude_status(self):
        installed = shutil.which("claude") is not None
        if installed:
            self._claude_status_lbl.configure(text="Installed", text_color=C["green"])
            try:
                r = subprocess.run(["claude", "--version"],
                                   capture_output=True, text=True, timeout=5)
                ver = r.stdout.strip().splitlines()[0] if r.returncode == 0 else ""
            except Exception:
                ver = ""
            self._claude_status_sub.configure(text=ver or "Ready to use")
        else:
            self._claude_status_lbl.configure(text="Not installed",
                                              text_color=C["yellow"])
            self._claude_status_sub.configure(text="Open Install → to set up")
