"""
Benchmark page — animated CPU/memory benchmark with donut gauge + bar chart.
"""

import threading
import customtkinter as ctk

from ..app import (
    BasePage, C, TIER_COLORS,
    card_frame, label, dim_label, sub_label,
    accent_button, ghost_button, chip, hairline,
    DonutGauge, BarChart,
)


TIER_LABELS = {
    "ultra": ("Ultra Tier",    "Top-end machine — runs largest local models."),
    "high":  ("High Tier",     "Excellent for large local models and cloud."),
    "mid":   ("Mid Tier",      "Great for small local models + cloud."),
    "low":   ("Low Tier",      "Cloud-first usage recommended."),
}


class BenchmarkPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._running = False
        self._built = False

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        if self.app.bench_result:
            self._show_results(self.app.bench_result)
        else:
            self._show_placeholder()

    def on_hardware_ready(self):
        pass

    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Performance Benchmark",
            "Measures CPU and memory to score your machine and recommend models.",
            right_widget_factory=self._build_run_button,
        )

        # Status row
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=32, pady=(0, 8))
        self._status_label = dim_label(ctrl, "", size=12)
        self._status_label.pack(side="left")

        # Indeterminate progress
        self._prog = ctk.CTkProgressBar(
            self, fg_color=C["card"], progress_color=C["accent"],
            height=4, corner_radius=2,
        )
        self._prog.set(0)
        self._prog.pack(fill="x", padx=32, pady=(0, 16))
        self._prog.pack_forget()

        # Results frame (replaced on each render)
        self._results_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._results_frame.pack(fill="both", expand=True, padx=32, pady=(0, 24))

    def _build_run_button(self, parent):
        self._run_btn = accent_button(parent, "▶  Run Benchmark",
                                      self._start, width=180)
        self._run_btn.pack(anchor="e")

    # ------------------------------------------------------------------

    def _start(self):
        if self._running:
            return
        if not self.app.system_info:
            self._status_label.configure(
                text="Run a hardware scan first.", text_color=C["yellow"])
            return
        self._running = True
        self._run_btn.configure(state="disabled", text="Running…")
        self._status_label.configure(text="Warming up…", text_color=C["dim"])

        self._prog.pack(fill="x", padx=32, pady=(0, 16))
        self._prog.configure(mode="indeterminate")
        self._prog.start()

        # Clear results placeholder
        for w in self._results_frame.winfo_children():
            w.destroy()

        spinning = card_frame(self._results_frame)
        spinning.pack(fill="x")
        label(spinning, "Benchmarking your machine…",
              size=16, weight="bold").pack(padx=22, pady=(20, 6), anchor="w")
        self._busy_text = dim_label(spinning,
            "This takes ~8 seconds. Avoid running heavy apps in the meantime.",
            size=12)
        self._busy_text.pack(padx=22, pady=(0, 20), anchor="w")

        def _run():
            from ...hardware.benchmark import Benchmarker

            def on_step(msg):
                self.app.after(0,
                    lambda m=msg: self._status_label.configure(
                        text=m, text_color=C["dim"]))

            result = Benchmarker(system_info=self.app.system_info).run(
                on_progress=on_step)
            self.app.bench_result = result
            self.app.after(0, lambda: self._on_done(result))

        threading.Thread(target=_run, daemon=True).start()

    def _on_done(self, result):
        self._running = False
        self._prog.stop()
        self._prog.pack_forget()
        self._run_btn.configure(state="normal", text="▶  Run Benchmark")
        self._status_label.configure(text="✓ Benchmark complete",
                                     text_color=C["green"])
        self._show_results(result)
        if hasattr(self.app.pages.get("models"), "on_benchmark_ready"):
            self.app.pages["models"].on_benchmark_ready()
        if hasattr(self.app.pages.get("dashboard"), "on_hardware_ready"):
            self.app.pages["dashboard"].on_hardware_ready()
        tier = result.tier.upper()
        self.app.show_toast(
            f"Benchmark done — {tier} tier  ·  {result.overall_score:.0f}/100",
            kind="success",
        )
        try:
            self.app.sidebar.refresh_status()
        except Exception:
            pass

    # ------------------------------------------------------------------

    def _show_placeholder(self):
        for w in self._results_frame.winfo_children():
            w.destroy()
        card = card_frame(self._results_frame)
        card.pack(fill="x")
        ctk.CTkFrame(card, fg_color="transparent", height=18).pack()
        ctk.CTkLabel(card, text="⚡", font=ctk.CTkFont(size=48),
                     text_color=C["accent"]).pack()
        label(card, "Ready to benchmark", size=18, weight="bold").pack(pady=(8, 4))
        dim_label(card,
            "Click Run Benchmark to score your CPU, memory, and GPU. "
            "We'll use the result to recommend the best models for your machine.",
            size=12, wraplength=520).pack(pady=(0, 22))

    def _show_results(self, result):
        for w in self._results_frame.winfo_children():
            w.destroy()

        tier_color = TIER_COLORS.get(result.tier, C["accent"])

        # ── Hero overall score card ───────────────────────────────────
        hero = card_frame(self._results_frame)
        hero.pack(fill="x", pady=(0, 18))
        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)
        inner.columnconfigure(0, weight=0)
        inner.columnconfigure(1, weight=1)

        # Donut with gradient ring (low→high color)
        donut_box = ctk.CTkFrame(inner, fg_color=C["card"])
        donut_box.grid(row=0, column=0, sticky="w", padx=(0, 22))
        gradient_stops = {
            "ultra": [C["indigo"], C["accent"], C["green"]],
            "high":  [C["accent"], C["green"]],
            "mid":   [C["yellow"], C["accent"]],
            "low":   [C["red"], C["yellow"]],
        }.get(result.tier, [tier_color, tier_color])
        donut = DonutGauge(donut_box,
                           value=result.overall_score, max_val=100,
                           gradient=gradient_stops, size=180, thickness=16,
                           bg=C["card"], label_text="overall")
        donut.pack()

        # Right of donut: tier + breakdown
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")

        head = ctk.CTkFrame(right, fg_color="transparent")
        head.pack(fill="x", anchor="w")
        tier_label, tier_desc = TIER_LABELS.get(
            result.tier, ("Custom Tier", ""))
        label(head, tier_label, size=22, weight="bold",
              color=tier_color).pack(side="left")
        chip(head, result.tier.upper(),
             color=tier_color, bg=C["card_hi"]).pack(side="left", padx=12, pady=4)

        dim_label(right, tier_desc, size=12, wraplength=560).pack(
            anchor="w", pady=(4, 14))

        # Small inline stats
        stats_row = ctk.CTkFrame(right, fg_color="transparent")
        stats_row.pack(fill="x")
        for k, v in [
            ("Overall", f"{result.overall_score:.1f}"),
            ("Single-Core", f"{result.cpu_single_score:,.0f}"),
            ("Multi-Core", f"{result.cpu_multi_score:,.0f}"),
            ("Memory", f"{result.memory_bandwidth_gbps:.2f} GB/s"),
        ]:
            box = ctk.CTkFrame(stats_row, fg_color="transparent")
            box.pack(side="left", padx=(0, 28))
            sub_label(box, k.upper(), size=10).pack(anchor="w")
            label(box, v, size=15, weight="bold").pack(anchor="w")

        # ── Bar chart ─────────────────────────────────────────────────
        chart_card = card_frame(self._results_frame)
        chart_card.pack(fill="x", pady=(0, 18))
        head2 = ctk.CTkFrame(chart_card, fg_color="transparent")
        head2.pack(fill="x", padx=22, pady=(16, 0))
        label(head2, "Sub-scores", size=14, weight="bold").pack(side="left")
        sub_label(head2, "  / 100 each", size=10).pack(side="left")

        single_pct = min(100, result.cpu_single_score / 1_000)
        multi_pct  = min(100, result.cpu_multi_score  / 2_000)
        mem_score  = min(100, result.details.get("mem_score", 0))
        vram_mb    = result.details.get("vram_mb", 0)
        vram_pct   = min(100, vram_mb / 245.76)

        bar_data = [
            ("Single",  single_pct, C["accent"]),
            ("Multi",   multi_pct,  C["indigo"]),
            ("Memory",  mem_score,  C["purple"]),
            ("VRAM",    vram_pct,   C["yellow"]),
        ]
        BarChart(chart_card, bar_data, width=720, height=190,
                 bg=C["card"]).pack(padx=14, pady=(8, 16))

        # ── Action row ────────────────────────────────────────────────
        actions = ctk.CTkFrame(self._results_frame, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 12))
        accent_button(actions, "→  View Model Recommendations",
                      lambda: self.app.show_page("models"),
                      width=260).pack(side="left")
        ghost_button(actions, "Re-run",
                     lambda: self._start(),
                     width=110, color=C["dim"]).pack(side="left", padx=10)
