"""
Models page — display model recommendations after benchmark.
"""

import customtkinter as ctk
from ..app import BasePage, C, card_frame, label, dim_label, accent_button, badge


STRATEGY_DESC = {
    "api_only":        ("☁  Cloud Only",       C["accent"],  "Your hardware is best paired with the Anthropic cloud API."),
    "local_capable":   ("⚡  Hybrid Mode",      C["yellow"],  "You can run small local models alongside the cloud API."),
    "local_preferred": ("🖥  Local-First Mode", C["purple"],  "Your GPU can run large models locally for full privacy."),
}


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
            "Model Recommendations",
            "Based on your hardware, these models are the best fit for you.",
        )
        self._run_btn = accent_button(
            self, "⚡  Run Benchmark First",
            lambda: self.app.show_page("benchmark"), width=200,
        )
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=28)
        self._refresh()

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

        self.app.recommendation = ModelRecommender().recommend(
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
