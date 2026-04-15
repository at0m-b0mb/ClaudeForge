"""
Models page — model recommendations + full model catalog browser.
"""

import customtkinter as ctk
from ..app import BasePage, C, card_frame, label, dim_label, accent_button, badge


STRATEGY_DESC = {
    "api_only":        ("☁  Cloud Only",       C["accent"],  "Your hardware is best paired with the Anthropic cloud API."),
    "local_capable":   ("⚡  Hybrid Mode",      C["yellow"],  "You can run small local models alongside the cloud API."),
    "local_preferred": ("🖥  Local-First Mode", C["purple"],  "Your GPU can run large models locally for full privacy."),
}

# When no GPU is present, a model is considered runnable on CPU only if its
# declared RAM requirement fits within this fraction of total system RAM.
# The 0.6 factor (60 %) leaves headroom for the OS and other processes.
_CPU_ONLY_RAM_FACTOR = 0.6


class ModelCard(ctk.CTkFrame):
    def __init__(self, parent, name, desc, tags, highlight=False, **kw):
        super().__init__(
            parent,
            fg_color=C["card"],
            corner_radius=12,
            border_width=2 if highlight else 1,
            border_color=C["accent"] if highlight else C["border"],
            **kw,
        )
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 4))
        label(top, name, size=14, weight="bold").pack(side="left")
        if highlight:
            badge(top, "Recommended", C["accent"]).pack(side="right")

        dim_label(self, desc, size=12, wraplength=260).pack(padx=16, anchor="w", pady=(0, 8))

        tag_row = ctk.CTkFrame(self, fg_color="transparent")
        tag_row.pack(padx=16, anchor="w", pady=(0, 14))
        for t in tags:
            ctk.CTkLabel(
                tag_row, text=f" {t} ",
                font=ctk.CTkFont(size=10),
                text_color=C["accent"],
                fg_color="#1a2a28",
                corner_radius=4,
            ).pack(side="left", padx=3)


class ModelsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False
        self._current_db = None       # Most recently refreshed ModelDatabase
        self._browse_refreshed = False  # True after the first live Ollama fetch

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        self._refresh()

    def on_benchmark_ready(self):
        if self._built:
            self._refresh()

    def on_hardware_ready(self):
        if self._built:
            self._refresh()

    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Models",
            "Recommendations for your hardware, plus the full model catalog.",
        )

        # Tab bar
        tab_bar = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=10)
        tab_bar.pack(fill="x", padx=28, pady=(0, 16))
        self._tab_rec    = self._tab_btn(tab_bar, "🎯  Recommendations", "recommendations")
        self._tab_browse = self._tab_btn(tab_bar, "📚  Browse All Models", "browse")
        self._tab_rec.pack(side="left", padx=4, pady=4)
        self._tab_browse.pack(side="left", padx=4, pady=4)

        self._run_btn = accent_button(
            self, "⚡  Run Benchmark First",
            lambda: self.app.show_page("benchmark"), width=200,
        )

        # Rec content frame
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=28)

        # Browse content frame (hidden until Browse tab clicked)
        self._browse_content = ctk.CTkFrame(self, fg_color="transparent")

        self._active_tab = "recommendations"
        self._set_tab("recommendations")
        self._refresh()

    def _tab_btn(self, parent, text, tab_key):
        return ctk.CTkButton(
            parent, text=text,
            fg_color="transparent", hover_color=C["nav_hover"],
            text_color=C["dim"], font=ctk.CTkFont(size=13),
            corner_radius=8, height=34,
            command=lambda: self._set_tab(tab_key),
        )

    def _set_tab(self, tab_key: str):
        self._active_tab = tab_key
        active_style   = dict(fg_color=C["accent"], text_color="#0d1117",
                              font=ctk.CTkFont(size=13, weight="bold"))
        inactive_style = dict(fg_color="transparent", text_color=C["dim"],
                              font=ctk.CTkFont(size=13, weight="normal"))

        if tab_key == "recommendations":
            self._tab_rec.configure(**active_style)
            self._tab_browse.configure(**inactive_style)
            self._browse_content.pack_forget()
            self._content.pack(fill="both", expand=True, padx=28)
        else:
            self._tab_browse.configure(**active_style)
            self._tab_rec.configure(**inactive_style)
            self._content.pack_forget()
            self._run_btn.pack_forget()
            self._browse_content.pack(fill="both", expand=True, padx=28)
            self._build_browse()
            # Auto-refresh from Ollama the first time the browse tab is opened
            if not self._browse_refreshed:
                self._browse_refreshed = True
                self._do_refresh_models(force=False)

    def _build_browse(self, db=None):
        """Populate the Browse All Models frame (idempotent)."""
        for w in self._browse_content.winfo_children():
            w.destroy()

        from ...models.database import ModelDatabase
        if db is None:
            db = self._current_db if self._current_db is not None else ModelDatabase()
        self._current_db = db

        # Get installed model IDs and hardware info for compatibility checks
        installed_ids = set(db.installed_model_ids())
        system_info = self.app.system_info
        if system_info:
            vram_mb = max((g.vram_mb for g in system_info.gpus), default=0)
            ram_gb  = system_info.ram_total_gb
        else:
            vram_mb = None
            ram_gb  = None

        # Refresh button + source label
        refresh_row = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        refresh_row.pack(fill="x", pady=(0, 12))
        src_text = f"Data source: {db.last_fetch_source()}"
        if installed_ids:
            src_text += f"  ·  {len(installed_ids)} installed locally"
        src_text += "  ·  Click to refresh from Ollama"
        self._src_label = dim_label(refresh_row, src_text, size=11)
        self._src_label.pack(side="left")
        ctk.CTkButton(
            refresh_row, text="⟳ Refresh Models", width=130, height=28,
            fg_color=C["card"], hover_color=C["border"],
            text_color=C["accent"], border_width=1, border_color=C["border"],
            corner_radius=8, font=ctk.CTkFont(size=11),
            command=lambda: self._do_refresh_models(force=True),
        ).pack(side="right")

        # ── Claude API models ─────────────────────────────────────────
        label(self._browse_content, "Claude API Models",
              size=15, weight="bold").pack(anchor="w", pady=(0, 10))

        tier_colors = {"fast": C["green"], "balanced": C["accent"], "powerful": C["purple"]}
        for m in db.claude_api_models:
            row_card = card_frame(self._browse_content)
            row_card.pack(fill="x", pady=4)
            left = ctk.CTkFrame(row_card, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=16, pady=12)

            name_row = ctk.CTkFrame(left, fg_color="transparent")
            name_row.pack(anchor="w")
            label(name_row, m.display_name, size=13, weight="bold").pack(side="left")
            tc = tier_colors.get(m.tier, C["dim"])
            ctk.CTkLabel(name_row, text=f"  {m.tier.upper()}",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=tc).pack(side="left", pady=2)

            dim_label(left, m.description, size=12).pack(anchor="w", pady=(2, 0))

            # Requirements + benchmark row
            meta_row = ctk.CTkFrame(left, fg_color="transparent")
            meta_row.pack(anchor="w", pady=(3, 0))
            ctx_str   = f"{m.context_window // 1000}K ctx"
            out_str   = f"{m.output_tokens // 1000}K output"
            bench     = m.benchmark
            bench_str = f"HumanEval {bench.get('humaneval', '?')}%" if bench else ""
            swe_str   = f"SWE-bench {bench.get('swe_bench', '?')}%" if bench and 'swe_bench' in bench else ""
            for piece in [m.id, ctx_str, out_str, bench_str, swe_str]:
                if not piece:
                    continue
                ctk.CTkLabel(meta_row, text=f" {piece} ",
                             font=ctk.CTkFont(size=10),
                             text_color=C["dim"], fg_color=C["card"],
                             corner_radius=4).pack(side="left", padx=2)

            right = ctk.CTkFrame(row_card, fg_color="transparent")
            right.pack(side="right", padx=16, pady=12)
            for strength in m.strengths[:3]:
                ctk.CTkLabel(right, text=f" {strength} ",
                             font=ctk.CTkFont(size=10),
                             text_color=C["accent"], fg_color="#1a2a28",
                             corner_radius=4).pack(anchor="e", pady=1)
            if m.pricing:
                inp = m.pricing.get("input_per_mtok", 0)
                out = m.pricing.get("output_per_mtok", 0)
                dim_label(right, f"${inp:.2f} / ${out:.2f} per MTok", size=10).pack(anchor="e", pady=(4, 0))

        # ── Local / Ollama models ─────────────────────────────────────
        label(self._browse_content, "Local Models  (via Ollama)",
              size=15, weight="bold").pack(anchor="w", pady=(20, 10))

        quality_colors = {
            "excellent": C["green"], "very good": C["green"],
            "good": C["accent"], "fair": C["yellow"], "basic": C["dim"],
        }
        for m in db.local_models:
            is_installed = m.id in installed_ids

            # Hardware compatibility check
            is_compatible = None
            if vram_mb is not None and ram_gb is not None:
                if vram_mb > 0:
                    is_compatible = (m.vram_required_mb <= vram_mb
                                     and m.ram_required_gb <= ram_gb)
                else:
                    is_compatible = m.ram_required_gb <= ram_gb * _CPU_ONLY_RAM_FACTOR

            row_card = card_frame(
                self._browse_content,
                border_color=C["accent"] if is_installed else C["border"],
            )
            row_card.pack(fill="x", pady=4)
            left = ctk.CTkFrame(row_card, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=16, pady=12)

            name_row = ctk.CTkFrame(left, fg_color="transparent")
            name_row.pack(anchor="w")
            label(name_row, m.display_name, size=13, weight="bold").pack(side="left")
            qc = quality_colors.get(m.quality, C["dim"])
            ctk.CTkLabel(name_row, text=f"  {m.quality.upper()}",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=qc).pack(side="left", pady=2)
            if is_installed:
                badge(name_row, "INSTALLED", C["green"]).pack(side="left", padx=6)

            dim_label(left, m.description, size=12).pack(anchor="w", pady=(2, 0))

            meta_row = ctk.CTkFrame(left, fg_color="transparent")
            meta_row.pack(anchor="w", pady=(3, 0))
            vram_str = f"{m.vram_required_mb / 1024:.0f} GB VRAM" if m.vram_required_mb else "CPU only"
            ctx_str  = f"{m.context_window // 1000}K ctx" if m.context_window else ""
            bench    = m.benchmark
            he_str   = f"HumanEval {bench.get('humaneval', '?')}%" if bench else ""
            for piece in [f"ID: {m.id}", vram_str, f"{m.ram_required_gb:.0f} GB RAM",
                          m.speed.title(), ctx_str, he_str]:
                if not piece:
                    continue
                ctk.CTkLabel(meta_row, text=f" {piece} ",
                             font=ctk.CTkFont(size=10),
                             text_color=C["dim"], fg_color=C["card"],
                             corner_radius=4).pack(side="left", padx=2)

            right = ctk.CTkFrame(row_card, fg_color="transparent")
            right.pack(side="right", padx=16, pady=12)

            # Compatibility badge (only when hardware info is available)
            if is_compatible is True:
                ctk.CTkLabel(right, text="✓ Compatible",
                             font=ctk.CTkFont(size=10, weight="bold"),
                             text_color=C["green"]).pack(anchor="e", pady=(0, 4))
            elif is_compatible is False:
                ctk.CTkLabel(right, text="✗ Insufficient VRAM/RAM",
                             font=ctk.CTkFont(size=10, weight="bold"),
                             text_color=C["red"]).pack(anchor="e", pady=(0, 4))

            dim_label(right, m.use_case, size=11, wraplength=160).pack(anchor="e")
            if m.ollama_pull:
                dim_label(right, m.ollama_pull, size=10).pack(anchor="e", pady=(4, 0))

            # Delete button — only for models already installed locally
            if is_installed:
                ctk.CTkButton(
                    right, text="🗑 Delete", width=80, height=26,
                    fg_color="transparent", hover_color="#2d1515",
                    text_color=C["red"], border_width=1, border_color=C["red"],
                    corner_radius=6, font=ctk.CTkFont(size=10),
                    command=lambda mid=m.id: self._do_delete_model(mid),
                ).pack(anchor="e", pady=(6, 0))

        # bottom padding
        ctk.CTkFrame(self._browse_content, fg_color="transparent", height=24).pack()

    def _do_refresh_models(self, force: bool = True):
        """Fetch live model data from Anthropic + Ollama in a background thread.

        When *force* is False the cached result is used if it is still fresh
        (respects the CACHE_TTL_HOURS setting in model_fetcher.py).
        """
        import threading
        if hasattr(self, "_src_label"):
            self._src_label.configure(text="Fetching live model data…")

        def _update_status(msg: str):
            if hasattr(self, "_src_label"):
                self._src_label.configure(text=msg)

        def _run():
            try:
                from ...models.database import ModelDatabase
                db = ModelDatabase()
                result = db.refresh(
                    api_key=None,
                    force=force,
                    on_progress=lambda m: self.app.after(0, lambda msg=m: _update_status(msg)),
                )
                self.app.after(0, lambda: self._on_refresh_done(db, result))
            except Exception as exc:
                self.app.after(0, lambda e=exc: _update_status(f"Refresh failed: {e}"))
        threading.Thread(target=_run, daemon=True).start()

    def _on_refresh_done(self, db, result):
        self._current_db = db
        installed_count = len(db.installed_model_ids())
        errors = ", ".join(result.errors) if result.errors else ""
        src_msg = f"Data source: {result.source}"
        if installed_count:
            src_msg += f"  ·  {installed_count} installed locally"
        if errors:
            src_msg += f"  ·  {errors}"
        if hasattr(self, "_src_label"):
            self._src_label.configure(text=src_msg)
        # Re-build the browse panel with the freshly fetched data
        self._build_browse(db=db)

    def _do_delete_model(self, model_id: str):
        """Delete a locally installed Ollama model in a background thread."""
        import threading

        def _update_status(msg: str):
            if hasattr(self, "_src_label"):
                self._src_label.configure(text=msg)

        def _run():
            try:
                from ...setup.alias_manager import AliasManager
                self.app.after(0, lambda: _update_status(f"Deleting {model_id}…"))
                ok = AliasManager(
                    on_log=lambda m: self.app.after(0, lambda msg=m: _update_status(msg))
                ).delete_model(model_id)
                if ok:
                    self.app.after(0, lambda: _update_status(
                        f"Deleted {model_id}. Refreshing list…"
                    ))
                    # Force-refresh so the deleted model is no longer shown
                    self.app.after(200, lambda: self._do_refresh_models(force=True))
                else:
                    self.app.after(0, lambda: _update_status(
                        f"Delete failed for {model_id}. Is Ollama running?"
                    ))
            except Exception as exc:
                self.app.after(0, lambda e=exc: _update_status(f"Delete failed: {e}"))
        threading.Thread(target=_run, daemon=True).start()

    def _refresh(self):
        if not self.app.bench_result or not self.app.system_info:
            self._run_btn.pack(pady=20)
            for w in self._content.winfo_children():
                w.destroy()
            dim_label(self._content,
                "Run the Benchmark first so we can tailor recommendations to your machine.",
                size=13, wraplength=500).pack(pady=20)
            return

        self._run_btn.pack_forget()
        self._compute_and_display()

    def _compute_and_display(self):
        from ...models.recommender import ModelRecommender
        info   = self.app.system_info
        result = self.app.bench_result
        vram_mb = max((g.vram_mb for g in info.gpus), default=0)

        # Use the most recently refreshed database so recommendations include
        # any locally installed Ollama models the user actually has.
        self.app.recommendation = ModelRecommender(db=self._current_db).recommend(
            benchmark_tier=result.tier,
            overall_score=result.overall_score,
            ram_gb=info.ram_total_gb,
            vram_mb=vram_mb,
            is_apple_silicon=info.cpu.is_apple_silicon,
        )
        rec = self.app.recommendation

        for w in self._content.winfo_children():
            w.destroy()

        # Strategy banner
        strat_label, strat_color, strat_desc = STRATEGY_DESC.get(
            rec.strategy, ("", C["dim"], rec.reasoning)
        )
        banner = ctk.CTkFrame(self._content, fg_color=C["card"], corner_radius=12,
                              border_width=1, border_color=strat_color)
        banner.pack(fill="x", pady=(0, 20))
        top = ctk.CTkFrame(banner, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 4))
        label(top, strat_label, size=14, weight="bold", color=strat_color).pack(side="left")
        dim_label(banner, strat_desc, size=12, wraplength=800).pack(padx=16, anchor="w", pady=(0, 12))

        # Reasoning
        dim_label(self._content, rec.reasoning, size=12, wraplength=800).pack(anchor="w", pady=(0, 16))

        # Claude API section
        label(self._content, "Claude API Models", size=15, weight="bold").pack(anchor="w", pady=(0, 10))
        api_row = ctk.CTkFrame(self._content, fg_color="transparent")
        api_row.pack(fill="x", pady=(0, 20))
        api_row.columnconfigure((0, 1), weight=1)

        pm = rec.primary_api_model
        ModelCard(
            api_row, pm.display_name, pm.description,
            pm.strengths[:3], highlight=True,
        ).grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        if rec.alternative_api_model:
            am = rec.alternative_api_model
            ModelCard(
                api_row, am.display_name, am.description,
                am.strengths[:3], highlight=False,
            ).grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        # Local models section
        if rec.local_models:
            label(self._content, "Runnable Local Models (via Ollama)",
                  size=15, weight="bold").pack(anchor="w", pady=(0, 10))
            local_row = ctk.CTkFrame(self._content, fg_color="transparent")
            local_row.pack(fill="x", pady=(0, 20))
            cols = min(3, len(rec.local_models))
            for i in range(cols):
                local_row.columnconfigure(i, weight=1)
            for i, m in enumerate(rec.local_models[:3]):
                vram_tag = f"{m.vram_required_mb // 1024} GB VRAM" if m.vram_required_mb else "CPU"
                ModelCard(
                    local_row, m.display_name,
                    m.description,
                    [m.quality, m.speed, vram_tag],
                    highlight=(i == 0),
                ).grid(row=0, column=i, padx=6, sticky="nsew")

        # Tips
        if rec.tips:
            label(self._content, "Tips", size=15, weight="bold").pack(anchor="w", pady=(0, 8))
            tips_card = ctk.CTkFrame(self._content, fg_color=C["card"], corner_radius=12,
                                     border_width=1, border_color=C["border"])
            tips_card.pack(fill="x", pady=(0, 24))
            for tip in rec.tips:
                row = ctk.CTkFrame(tips_card, fg_color="transparent")
                row.pack(fill="x", padx=16, pady=5)
                ctk.CTkLabel(row, text="•", text_color=C["accent"],
                             font=ctk.CTkFont(size=14)).pack(side="left")
                dim_label(row, f"  {tip}", size=12, wraplength=760).pack(side="left", anchor="w")
