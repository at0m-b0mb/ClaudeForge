"""
Hardware page — scan and display system hardware.
"""

import threading
import customtkinter as ctk
from ..app import BasePage, C, card_frame, label, dim_label, accent_button, status_dot


def _vram_str(vram_mb: int) -> str:
    if vram_mb == 0:
        return "Shared / unknown"
    if vram_mb >= 1024:
        return f"{vram_mb / 1024:.1f} GB"
    return f"{vram_mb} MB"


class HardwarePage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False
        self._scanning = False

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        if self.app.system_info:
            self._populate()

    def on_hardware_ready(self):
        if self._built:
            self._populate()

    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Hardware Detection",
            "Detailed breakdown of your CPU, memory, GPU, and storage.",
        )
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=28, pady=(0, 18))
        self._scan_btn = accent_button(ctrl, "⟳  Scan Hardware", self._start_scan, width=160)
        self._scan_btn.pack(side="left")
        self._scan_status = dim_label(ctrl, "")
        self._scan_status.pack(side="left", padx=14)

        # Cards grid
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=28)
        grid.columnconfigure((0, 1), weight=1)

        self._os_card   = self._make_card(grid, 0, 0, "🖥  Operating System")
        self._cpu_card  = self._make_card(grid, 0, 1, "⚙  CPU")
        self._ram_card  = self._make_card(grid, 1, 0, "🧠  Memory")
        self._gpu_card  = self._make_card(grid, 1, 1, "🎮  GPU")
        self._disk_card = self._make_card(grid, 2, 0, "💾  Disk",  colspan=2)

        if self.app.system_info:
            self._populate()

    def _make_card(self, grid, row, col, title, colspan=1):
        card = card_frame(grid)
        card.grid(row=row, column=col, columnspan=colspan, padx=6, pady=6, sticky="nsew")
        label(card, title, size=13, weight="bold", color=C["dim"]).pack(anchor="w", padx=16, pady=(14, 8))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=(0, 14))
        return body

    # ------------------------------------------------------------------

    def _start_scan(self):
        if self._scanning:
            return
        self._scanning = True
        self._scan_btn.configure(state="disabled", text="Scanning…")
        self._scan_status.configure(text="")
        def _run():
            from ...hardware.detector import HardwareDetector
            self.app.system_info = HardwareDetector().detect()
            self.app.after(0, self._on_scan_done)
        threading.Thread(target=_run, daemon=True).start()

    def _on_scan_done(self):
        self._scanning = False
        self._scan_btn.configure(state="normal", text="⟳  Scan Hardware")
        self._scan_status.configure(text="Scan complete", text_color=C["green"])
        self._populate()
        for page in self.app.pages.values():
            if hasattr(page, "on_hardware_ready"):
                page.on_hardware_ready()

    def _populate(self):
        info = self.app.system_info
        if not info:
            return
        self._fill(self._os_card,  [
            ("OS",           info.os_name),
            ("Architecture", info.architecture),
            ("Kernel",       info.os_version[:60] + ("…" if len(info.os_version) > 60 else "")),
        ])
        cpu = info.cpu
        self._fill(self._cpu_card, [
            ("Model",    cpu.model),
            ("Cores",    f"{cpu.physical_cores} physical  /  {cpu.logical_cores} logical"),
            ("Frequency", f"{cpu.max_freq_mhz:.0f} MHz" if cpu.max_freq_mhz else "N/A"),
            ("Type",     "Apple Silicon (ARM64)" if cpu.is_apple_silicon else cpu.architecture),
        ])
        self._fill(self._ram_card, [
            ("Total",     f"{info.ram_total_gb:.1f} GB"),
            ("Available", f"{info.ram_available_gb:.1f} GB"),
            ("Used",      f"{info.ram_total_gb - info.ram_available_gb:.1f} GB"),
        ])
        if info.gpus:
            rows = []
            for g in info.gpus:
                accel = []
                if g.cuda_available:  accel.append("CUDA")
                if g.metal_available: accel.append("Metal")
                if g.rocm_available:  accel.append("ROCm")
                rows += [
                    ("Name",    g.name),
                    ("VRAM",    _vram_str(g.vram_mb)),
                    ("Accel.",  ", ".join(accel) if accel else "None detected"),
                ]
        else:
            rows = [("GPU", "No discrete GPU detected")]
        self._fill(self._gpu_card, rows)

        self._fill(self._disk_card, [
            ("Total", f"{info.disk_total_gb:.1f} GB"),
            ("Free",  f"{info.disk_free_gb:.1f} GB"),
            ("Used",  f"{info.disk_total_gb - info.disk_free_gb:.1f} GB"),
        ], horizontal=True)

    def _fill(self, frame, rows, horizontal=False):
        for w in frame.winfo_children():
            w.destroy()
        if horizontal:
            for key, val in rows:
                col = ctk.CTkFrame(frame, fg_color="transparent")
                col.pack(side="left", padx=24, pady=0)
                dim_label(col, key, size=11).pack(anchor="w")
                label(col, val, size=14, weight="bold").pack(anchor="w")
        else:
            for key, val in rows:
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                dim_label(row, f"{key}:", size=12).pack(side="left", anchor="w")
                label(row, val, size=12).pack(side="left", padx=8, anchor="w")
