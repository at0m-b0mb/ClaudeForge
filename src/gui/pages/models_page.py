"""
Models page — recommendations + full model catalog browser, redesigned.
"""

import threading
import customtkinter as ctk

from ..app import (
    BasePage, C,
    card_frame, label, dim_label, sub_label,
    accent_button, ghost_button, chip, badge, hairline,
)


STRATEGY = {
    "api_only": (
        "☁  Cloud Only",
        C["accent"],
        "#0e2522",
        "Your hardware is best paired with the Anthropic cloud API.",
    ),
    "local_capable": (
        "⚡  Hybrid Mode",
        C["yellow"],
        "#2a1f0a",
        "You can run small local models alongside the cloud API.",
    ),
    "local_preferred": (
        "🖥  Local-First Mode",
        C["purple"],
        "#1d1230",
        "Your GPU can run large models locally for full privacy.",
    ),
}

TIER_FG = {"fast": C["green"], "balanced": C["accent"], "powerful": C["purple"]}
QUALITY_FG = {
    "excellent": C["green"], "very good": C["green"],
    "good": C["accent"], "fair": C["yellow"], "basic": C["dim"],
}


class ModelCard(ctk.CTkFrame):
    """Recommendation model card (highlight + name + desc + tags)."""

    def __init__(self, parent, name, desc, tags, highlight=False,
                 pricing=None, **kw):
        super().__init__(
            parent,
            fg_color=C["card"],
            corner_radius=14,
            border_width=2 if highlight else 1,
            border_color=C["accent"] if highlight else C["border"],
            **kw,
        )
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 4))
        label(top, name, size=14, weight="bold").pack(side="left")
        if highlight:
            badge(top, "Recommended", C["accent"]).pack(side="right")

        dim_label(self, desc, size=12, wraplength=300).pack(
            padx=18, anchor="w", pady=(4, 10))

        tag_row = ctk.CTkFrame(self, fg_color="transparent")
        tag_row.pack(padx=18, anchor="w", pady=(0, 14))
        for t in tags:
            chip(tag_row, t, color=C["accent_lt"],
                 bg="#0e2522").pack(side="left", padx=(0, 6))

        if pricing:
            ctk.CTkFrame(self, fg_color="transparent", height=2).pack()
            hairline(self, pad_x=18)
            sub_label(self, f"  Pricing: ${pricing.get('input_per_mtok', 0):.2f}"
                            f" in / ${pricing.get('output_per_mtok', 0):.2f} out"
                            f" per MTok", size=10).pack(anchor="w", padx=18,
                                                        pady=(8, 12))


class CatalogRow(ctk.CTkFrame):
    """Wide row for full model catalog browse."""

    def __init__(self, parent, name, tier_label, tier_color, desc,
                 meta_chips, right_chips=None, footnote=""):
        super().__init__(
            parent,
            fg_color=C["card"],
            corner_radius=12,
            border_width=1,
            border_color=C["border"],
        )

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=12)
        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=0)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")

        name_row = ctk.CTkFrame(left, fg_color="transparent")
        name_row.pack(anchor="w")
        label(name_row, name, size=14, weight="bold").pack(side="left")
        chip(name_row, tier_label, color=tier_color,
             bg=C["card_hi"]).pack(side="left", padx=10)

        dim_label(left, desc, size=12, wraplength=620).pack(
            anchor="w", pady=(4, 6))

        meta_row = ctk.CTkFrame(left, fg_color="transparent")
        meta_row.pack(anchor="w")
        for m in meta_chips:
            if not m:
                continue
            ctk.CTkLabel(
                meta_row, text=f"  {m}  ",
                font=ctk.CTkFont(size=10),
                text_color=C["dim"], fg_color=C["bg_alt"],
                corner_radius=6,
            ).pack(side="left", padx=(0, 6))

        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.grid(row=0, column=1, sticky="ne", padx=(20, 0))
        if right_chips:
            for r in right_chips:
                chip(right, r, color=C["accent"], bg="#0e2522").pack(
                    anchor="e", pady=2)
        if footnote:
            sub_label(right, footnote, size=10).pack(anchor="e", pady=(6, 0))


class ModelsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False

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
            "Personalised recommendations and the full model catalog.",
        )

        # Tab bar
        tabs = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=12,
                            border_width=1, border_color=C["border"])
        tabs.pack(anchor="w", padx=32, pady=(0, 16))
        self._tab_rec = self._tab_btn(tabs, "🎯  Recommendations", "recommendations")
        self._tab_browse = self._tab_btn(tabs, "📚  Browse all models", "browse")
        self._tab_rec.pack(side="left", padx=4, pady=4)
        self._tab_browse.pack(side="left", padx=4, pady=4)

        # Frames
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._browse_content = ctk.CTkFrame(self, fg_color="transparent")

        self._active_tab = "recommendations"
        self._set_tab("recommendations")

    def _tab_btn(self, parent, text, tab_key):
        return ctk.CTkButton(
            parent, text=text,
            fg_color="transparent", hover_color=C["card_hi"],
            text_color=C["dim"], font=ctk.CTkFont(size=12),
            corner_radius=8, height=32, width=190,
            command=lambda: self._set_tab(tab_key),
        )

    def _set_tab(self, tab_key: str):
        self._active_tab = tab_key
        active   = dict(fg_color=C["accent"], text_color=C["ink"],
                        font=ctk.CTkFont(size=12, weight="bold"))
        inactive = dict(fg_color="transparent", text_color=C["dim"],
                        font=ctk.CTkFont(size=12, weight="normal"))

        if tab_key == "recommendations":
            self._tab_rec.configure(**active)
            self._tab_browse.configure(**inactive)
            self._browse_content.pack_forget()
            self._content.pack(fill="both", expand=True, padx=32)
            self._refresh()
        else:
            self._tab_browse.configure(**active)
            self._tab_rec.configure(**inactive)
            self._content.pack_forget()
            self._browse_content.pack(fill="both", expand=True, padx=32)
            self._build_browse()

    # ------------------------------------------------------------------
    # Recommendations tab
    # ------------------------------------------------------------------

    def _refresh(self):
        if self._active_tab != "recommendations":
            return
        for w in self._content.winfo_children():
            w.destroy()

        if not self.app.bench_result or not self.app.system_info:
            empty = card_frame(self._content)
            empty.pack(fill="x", pady=(0, 16))
            ctk.CTkFrame(empty, fg_color="transparent", height=18).pack()
            ctk.CTkLabel(empty, text="🎯", font=ctk.CTkFont(size=42),
                         text_color=C["accent"]).pack()
            label(empty, "No recommendations yet", size=18,
                  weight="bold").pack(pady=(8, 4))
            dim_label(empty,
                "Run the benchmark first so we can tailor model picks to your hardware.",
                size=12, wraplength=520).pack(pady=(0, 14))
            accent_button(empty, "▶  Run Benchmark",
                          lambda: self.app.show_page("benchmark"),
                          width=200).pack(pady=(0, 22))
            return

        self._compute_and_display()

    def _compute_and_display(self):
        from ...models.recommender import ModelRecommender
        info   = self.app.system_info
        result = self.app.bench_result
        vram_mb = max((g.vram_mb for g in info.gpus), default=0)

        self.app.recommendation = ModelRecommender().recommend(
            benchmark_tier=result.tier,
            overall_score=result.overall_score,
            ram_gb=info.ram_total_gb,
            vram_mb=vram_mb,
            is_apple_silicon=info.cpu.is_apple_silicon,
        )
        rec = self.app.recommendation

        strat_label, strat_color, strat_bg, strat_desc = STRATEGY.get(
            rec.strategy, ("Custom", C["dim"], C["card_hi"], rec.reasoning))

        # Strategy banner
        banner = ctk.CTkFrame(
            self._content, fg_color=strat_bg, corner_radius=14,
            border_width=1, border_color=strat_color,
        )
        banner.pack(fill="x", pady=(0, 18))
        inner = ctk.CTkFrame(banner, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=14)
        label(inner, strat_label, size=15, weight="bold",
              color=strat_color).pack(anchor="w")
        dim_label(inner, strat_desc, size=12,
                  wraplength=900).pack(anchor="w", pady=(4, 0))

        # Reasoning
        dim_label(self._content, rec.reasoning, size=12,
                  wraplength=900).pack(anchor="w", pady=(0, 18))

        # Claude API row
        label(self._content, "Claude API Models", size=15,
              weight="bold").pack(anchor="w", pady=(0, 10))
        api_row = ctk.CTkFrame(self._content, fg_color="transparent")
        api_row.pack(fill="x", pady=(0, 20))
        api_row.columnconfigure((0, 1), weight=1)

        pm = rec.primary_api_model
        ModelCard(
            api_row, pm.display_name, pm.description,
            pm.strengths[:3], highlight=True, pricing=pm.pricing,
        ).grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        if rec.alternative_api_model:
            am = rec.alternative_api_model
            ModelCard(
                api_row, am.display_name, am.description,
                am.strengths[:3], highlight=False, pricing=am.pricing,
            ).grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        # Local models
        if rec.local_models:
            label(self._content, "Runnable Local Models  (via Ollama)",
                  size=15, weight="bold").pack(anchor="w", pady=(0, 10))
            local_row = ctk.CTkFrame(self._content, fg_color="transparent")
            local_row.pack(fill="x", pady=(0, 20))
            cols = min(3, len(rec.local_models))
            for i in range(cols):
                local_row.columnconfigure(i, weight=1)
            for i, m in enumerate(rec.local_models[:3]):
                vram_tag = (f"{m.vram_required_mb // 1024} GB VRAM"
                            if m.vram_required_mb else "CPU")
                ModelCard(
                    local_row, m.display_name, m.description,
                    [m.quality, m.speed, vram_tag],
                    highlight=(i == 0),
                ).grid(row=0, column=i, padx=6, sticky="nsew")

        # Tips
        if rec.tips:
            label(self._content, "Tips for your hardware",
                  size=15, weight="bold").pack(anchor="w", pady=(0, 8))
            tips_card = card_frame(self._content)
            tips_card.pack(fill="x", pady=(0, 24))
            for tip in rec.tips:
                row = ctk.CTkFrame(tips_card, fg_color="transparent")
                row.pack(fill="x", padx=18, pady=6)
                ctk.CTkLabel(row, text="✦", text_color=C["accent"],
                             font=ctk.CTkFont(size=12)).pack(
                    side="left", anchor="n")
                dim_label(row, "  " + tip, size=12,
                          wraplength=860).pack(side="left", anchor="w")
            ctk.CTkFrame(tips_card, fg_color="transparent", height=8).pack()

    # ------------------------------------------------------------------
    # Browse tab
    # ------------------------------------------------------------------

    def _build_browse(self):
        for w in self._browse_content.winfo_children():
            w.destroy()

        from ...models.database import ModelDatabase
        self._browse_db = ModelDatabase()
        db = self._browse_db

        # ── Toolbar: search + source label + refresh ──────────────────
        toolbar = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 14))
        toolbar.columnconfigure(1, weight=1)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_rows())

        search_box = ctk.CTkEntry(
            toolbar,
            textvariable=self._search_var,
            placeholder_text="🔍  Search models…",
            fg_color=C["card"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["sub"],
            font=ctk.CTkFont(size=13),
            height=36, corner_radius=10,
        )
        search_box.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipadx=4)

        self._src_label = dim_label(toolbar, f"Source: {db.last_fetch_source()}", size=11)
        self._src_label.grid(row=0, column=1, sticky="w")

        ghost_button(toolbar, "⟳  Refresh",
                     self._do_refresh_models, width=130, color=C["accent"]
                     ).grid(row=0, column=2)

        # ── Rows container (we rebuild this on filter) ─────────────────
        self._rows_container = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        self._rows_container.pack(fill="both", expand=True)

        self._all_row_data = []  # (display_widget_factory, search_text)
        self._row_widgets  = []  # built CTkFrame widgets

        # Build Claude API rows
        self._browse_section_labels = {}
        self._claude_section_idx = len(self._all_row_data)

        for m in db.claude_api_models:
            tier_color = TIER_FG.get(m.tier, C["dim"])
            ctx = f"{m.context_window // 1000}K ctx"
            out = f"{m.output_tokens // 1000}K output"
            bench = m.benchmark or {}
            meta = [
                m.id, ctx, out,
                f"HumanEval {bench.get('humaneval', '?')}%" if bench else None,
                f"SWE-bench {bench.get('swe_bench', '?')}%" if 'swe_bench' in bench else None,
            ]
            footnote = ""
            if m.pricing:
                inp  = m.pricing.get("input_per_mtok", 0)
                outp = m.pricing.get("output_per_mtok", 0)
                footnote = f"${inp:.2f} / ${outp:.2f} per MTok"
            search_key = f"{m.display_name} {m.id} {m.description} {m.tier}".lower()
            self._all_row_data.append(({
                "name": m.display_name, "tier_label": m.tier.title(),
                "tier_color": tier_color, "desc": m.description,
                "meta_chips": meta, "right_chips": m.strengths[:3],
                "footnote": footnote,
            }, search_key, "claude"))

        self._local_section_idx = len(self._all_row_data)

        for m in db.local_models:
            qc = QUALITY_FG.get(m.quality, C["dim"])
            vram_str = (f"{m.vram_required_mb / 1024:.0f} GB VRAM"
                        if m.vram_required_mb else "CPU only")
            ctx_str = f"{m.context_window // 1000}K ctx" if m.context_window else ""
            bench = m.benchmark or {}
            meta = [
                f"ID: {m.id}", vram_str, f"{m.ram_required_gb:.0f} GB RAM",
                m.speed.title() if m.speed else None, ctx_str,
                f"HumanEval {bench.get('humaneval', '?')}%" if bench else None,
            ]
            right = [m.use_case] if m.use_case else None
            search_key = (f"{m.display_name} {m.id} {m.description} "
                          f"{m.quality} {m.speed} {m.use_case or ''}").lower()
            self._all_row_data.append(({
                "name": m.display_name, "tier_label": m.quality.title(),
                "tier_color": qc, "desc": m.description,
                "meta_chips": meta, "right_chips": right,
                "footnote": m.ollama_pull or "",
            }, search_key, "local"))

        self._filter_rows()

    def _filter_rows(self):
        query = self._search_var.get().strip().lower() if hasattr(self, "_search_var") else ""

        # Destroy old widgets
        for w in getattr(self, "_row_widgets", []):
            try:
                w.destroy()
            except Exception:
                pass
        self._row_widgets = []

        shown_claude = False
        shown_local  = False

        for kw, search_key, section in self._all_row_data:
            if query and query not in search_key:
                continue
            parent = self._rows_container

            if section == "claude" and not shown_claude:
                hdr = label(parent, "Claude API Models", size=15, weight="bold")
                hdr.pack(anchor="w", pady=(0, 10))
                self._row_widgets.append(hdr)
                shown_claude = True

            if section == "local" and not shown_local:
                hdr = label(parent, "Local Models  (via Ollama)", size=15, weight="bold")
                hdr.pack(anchor="w", pady=(20, 10))
                self._row_widgets.append(hdr)
                shown_local = True

            row = CatalogRow(parent, **kw)
            row.pack(fill="x", pady=4)
            self._row_widgets.append(row)

        if not self._row_widgets:
            empty = label(self._rows_container, "No models match your search.",
                          size=14, color=C["dim"])
            empty.pack(pady=40)
            self._row_widgets.append(empty)

        spacer = ctk.CTkFrame(self._rows_container,
                              fg_color="transparent", height=24)
        spacer.pack()
        self._row_widgets.append(spacer)

    def _do_refresh_models(self):
        if hasattr(self, "_src_label"):
            self._src_label.configure(text="Fetching live model data…")

        def _run():
            try:
                from ...models.database import ModelDatabase
                db = ModelDatabase()
                result = db.refresh(
                    api_key=None, force=True,
                    on_progress=lambda m: self.app.after(
                        0, lambda msg=m: self._src_label.configure(text=msg)),
                )
                self.app.after(0, lambda: self._on_refresh_done(result))
            except Exception as exc:
                self.app.after(
                    0, lambda e=exc: self._src_label.configure(
                        text=f"Refresh failed: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _on_refresh_done(self, result):
        errors = ", ".join(result.errors) if result.errors else ""
        msg = f"Source: {result.source}"
        if errors:
            msg += f"  ·  {errors}"
        if hasattr(self, "_src_label"):
            self._src_label.configure(text=msg)
        self._build_browse()
        if result.errors:
            self.app.show_toast(f"Partial refresh — {errors[:60]}", kind="warn")
        else:
            self.app.show_toast("Model catalog refreshed", kind="success")
