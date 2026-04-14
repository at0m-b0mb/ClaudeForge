"""
Benchmark page — run CPU/memory benchmark and display scored results.
"""

import threading
import customtkinter as ctk
from ..app import BasePage, C, card_frame, label, dim_label, accent_button, badge


TIER_COLORS = {
    "ultra": "#a855f7",   # purple
    "high":  "#3fb950",   # green
    "mid":   "#d29922",   # yellow
    "low":   "#f85149",   # red
}


class ScoreBar(ctk.CTkFrame):
    """Animated horizontal score bar."""

    def __init__(self, parent, value: float, max_val: float = 100, color=None):
        super().__init__(parent, fg_color=C["border"], corner_radius=6, height=10)
        self._color = color or C["accent"]
        self._pct = min(1.0, max(0.0, value / max_val)) if max_val else 0
        self._fill = ctk.CTkFrame(self, fg_color=self._color, corner_radius=6, height=10, width=1)
        self._fill.place(relx=0, rely=0, relheight=1, relwidth=0)
        self.after(50, self._animate)

    def _animate(self, current=0.0):
        target = self._pct
        step = (target - current) * 0.12 + 0.002
        current = min(target, current + step)
        self._fill.place(relwidth=current)
        if current < target - 0.002:
            self.after(16, lambda: self._animate(current))


class MetricCard(ctk.CTkFrame):
    def __init__(self, parent, icon, title, value_str, score_pct, color=None):
        super().__init__(parent, fg_color=C["card"], corner_radius=12,
                         border_width=1, border_color=C["border"])
        self.pack_propagate(False)

        ctk.CTkLabel(self, text=icon, font=ctk.CTkFont(size=22)).pack(padx=18, pady=(16, 4), anchor="w")
        dim_label(self, title, size=11).pack(padx=18, anchor="w")
        label(self, value_str, size=16, weight="bold").pack(padx=18, pady=(2, 8), anchor="w")
        bar = ScoreBar(self, score_pct, color=color)
        bar.pack(fill="x", padx=18, pady=(0, 6))
        dim_label(self, f"{score_pct:.0f} / 100").pack(padx=18, pady=(0, 14), anchor="w")


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

    def on_hardware_ready(self):
        pass  # no automatic action needed

    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Performance Benchmark",
            "Measures CPU and memory to score your machine and recommend models.",
        )

        # Control bar
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=28, pady=(0, 20))
        self._run_btn = accent_button(ctrl, "▶  Run Benchmark", self._start, width=170)
        self._run_btn.pack(side="left")
        self._status_label = dim_label(ctrl, "")
        self._status_label.pack(side="left", padx=14)

        # Progress bar (hidden until benchmark runs)
        self._prog = ctk.CTkProgressBar(self, fg_color=C["card"], progress_color=C["accent"],
                                         height=6, corner_radius=3)
        self._prog.set(0)
        self._prog.pack(fill="x", padx=28, pady=(0, 20))
        self._prog.pack_forget()

        # Metrics grid (shown after run)
        self._metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._metrics_frame.pack(fill="x", padx=28)
        self._metrics_frame.columnconfigure((0, 1, 2, 3), weight=1)

        # Overall score (shown after run)
        self._overall_frame = card_frame(self)
        self._overall_frame.pack(fill="x", padx=28, pady=16)
        self._overall_frame.pack_forget()

    # ------------------------------------------------------------------

    def _start(self):
        if self._running:
            return
        if not self.app.system_info:
            self._status_label.configure(text="Run Hardware Scan first.", text_color=C["yellow"])
            return
        self._running = True
        self._run_btn.configure(state="disabled", text="Running…")
        self._status_label.configure(text="", text_color=C["dim"])

        # Show progress bar
        self._prog.pack(fill="x", padx=28, pady=(0, 20))
        self._prog.configure(mode="indeterminate")
        self._prog.start()

        def _run():
            from ...hardware.benchmark import Benchmarker
            steps = []
            def on_step(msg):
                steps.append(msg)
                self.app.after(0, lambda m=msg: self._status_label.configure(
                    text=m, text_color=C["dim"]
                ))
            result = Benchmarker(system_info=self.app.system_info).run(on_progress=on_step)
            self.app.bench_result = result
            self.app.after(0, lambda: self._on_done(result))
        threading.Thread(target=_run, daemon=True).start()

    def _on_done(self, result):
        self._running = False
        self._prog.stop()
        self._prog.pack_forget()
        self._run_btn.configure(state="normal", text="▶  Run Benchmark")
        self._status_label.configure(text="Complete!", text_color=C["green"])
        self._show_results(result)
        # Tell models page to refresh
        if hasattr(self.app.pages.get("models"), "on_benchmark_ready"):
            self.app.pages["models"].on_benchmark_ready()

    def _show_results(self, result):
        for w in self._metrics_frame.winfo_children():
            w.destroy()

        # CPU scores
        single_pct = min(100, result.cpu_single_score / 100_000)
        multi_pct  = min(100, result.cpu_multi_score  / 200_000)

        metrics = [
            ("⚡", "Single-Core CPU",    f"{result.cpu_single_score:,.0f} ops/s", single_pct,        C["accent"]),
            ("🔀", "Multi-Core CPU",     f"{result.cpu_multi_score:,.0f} ops/s",  multi_pct,         C["accent"]),
            ("🧠", "Memory Bandwidth",   f"{result.memory_bandwidth_gbps:.2f} GB/s", min(100, result.details.get("mem_score", 0)), C["purple"]),
            ("🎮", "GPU VRAM",           f"{result.details.get('vram_mb', 0) / 1024:.1f} GB",
             min(100, result.details.get("vram_mb", 0) / 245.76), C["yellow"]),
        ]
        for col, (icon, title, val, pct, color) in enumerate(metrics):
            card = MetricCard(self._metrics_frame, icon, title, val, pct, color)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")

        # Overall score card
        self._overall_frame.pack(fill="x", padx=28, pady=(8, 24))
        for w in self._overall_frame.winfo_children():
            w.destroy()

        tier_color = TIER_COLORS.get(result.tier, C["accent"])

        left = ctk.CTkFrame(self._overall_frame, fg_color="transparent")
        left.pack(side="left", padx=20, pady=16)
        label(left, "Overall Score", size=12, color=C["dim"]).pack(anchor="w")
        score_row = ctk.CTkFrame(left, fg_color="transparent")
        score_row.pack(anchor="w", pady=4)
        label(score_row, f"{result.overall_score:.1f}", size=36, weight="bold", color=tier_color).pack(side="left")
        label(score_row, " / 100", size=18, color=C["dim"]).pack(side="left", pady=12)

        right = ctk.CTkFrame(self._overall_frame, fg_color="transparent")
        right.pack(side="left", padx=16, pady=16)
        badge_widget = ctk.CTkFrame(right, fg_color=tier_color, corner_radius=8)
        badge_widget.pack(anchor="w")
        ctk.CTkLabel(badge_widget, text=f"  {result.tier.upper()} TIER  ",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#0d1117").pack(padx=6, pady=4)

        bar_frame = ctk.CTkFrame(self._overall_frame, fg_color="transparent")
        bar_frame.pack(side="left", fill="x", expand=True, padx=20, pady=16)
        dim_label(bar_frame, "Performance Score").pack(anchor="w")
        ScoreBar(bar_frame, result.overall_score, color=tier_color).pack(
            fill="x", pady=(8, 0), ipady=2
        )
