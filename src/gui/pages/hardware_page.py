"""
Hardware page — scan and display system hardware with modern cards + usage bars.
"""

import threading
import customtkinter as ctk

from ..app import (
    BasePage, C,
    card_frame, label, dim_label, sub_label,
    accent_button, ghost_button, chip, hairline, UsageBar,
)


def _vram_str(vram_mb: int) -> str:
    if vram_mb == 0:
        return "Shared / unknown"
    if vram_mb >= 1024:
        return f"{vram_mb / 1024:.1f} GB"
    return f"{vram_mb} MB"


class InfoCard(ctk.CTkFrame):
    """Section card with title + icon + content body."""

    def __init__(self, parent, icon, title, accent=None):
        super().__init__(
            parent, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["border"],
        )
        accent = accent or C["accent"]
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(head, text=icon, font=ctk.CTkFont(size=20),
                     text_color=accent).pack(side="left")
        ctk.CTkLabel(head, text="  " + title,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["text"]).pack(side="left")
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=18, pady=(0, 16))

    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()


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
            "Hardware",
            "Detailed breakdown of your CPU, memory, GPU, and storage.",
            right_widget_factory=self._build_scan_button,
        )

        self._status_row = ctk.CTkFrame(self, fg_color="transparent")
        self._status_row.pack(fill="x", padx=32, pady=(0, 12))
        self._scan_status = dim_label(self._status_row, "", size=12)
        self._scan_status.pack(side="left")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=32, pady=(0, 24))
        grid.columnconfigure((0, 1), weight=1)

        self._os_card   = InfoCard(grid, "🖥",  "Operating System", C["indigo"])
        self._cpu_card  = InfoCard(grid, "⚙",  "CPU",              C["accent"])
        self._ram_card  = InfoCard(grid, "🧠", "Memory",            C["purple"])
        self._gpu_card  = InfoCard(grid, "🎮", "GPU",               C["pink"])
        self._disk_card = InfoCard(grid, "💾", "Storage",           C["yellow"])

        self._os_card.grid(  row=0, column=0, padx=6, pady=6, sticky="nsew")
        self._cpu_card.grid( row=0, column=1, padx=6, pady=6, sticky="nsew")
        self._ram_card.grid( row=1, column=0, padx=6, pady=6, sticky="nsew")
        self._gpu_card.grid( row=1, column=1, padx=6, pady=6, sticky="nsew")
        self._disk_card.grid(row=2, column=0, padx=6, pady=6, sticky="nsew",
                             columnspan=2)

        if self.app.system_info:
            self._populate()
        else:
            self._fill_pending()

    def _build_scan_button(self, parent):
        self._scan_btn = accent_button(parent, "⟳  Scan Hardware",
                                       self._start_scan, width=170)
        self._scan_btn.pack(anchor="e")

    # ------------------------------------------------------------------

    def _start_scan(self):
        if self._scanning:
            return
        self._scanning = True
        self._scan_btn.configure(state="disabled", text="Scanning…")
        self._scan_status.configure(text="Scanning hardware…",
                                    text_color=C["dim"])

        def _run():
            from ...hardware.detector import HardwareDetector
            self.app.system_info = HardwareDetector().detect()
            self.app.after(0, self._on_scan_done)

        threading.Thread(target=_run, daemon=True).start()

    def _on_scan_done(self):
        self._scanning = False
        self._scan_btn.configure(state="normal", text="⟳  Scan Hardware")
        self._scan_status.configure(text="✓ Scan complete",
                                    text_color=C["green"])
        self._populate()
        for page in self.app.pages.values():
            if hasattr(page, "on_hardware_ready"):
                try:
                    page.on_hardware_ready()
                except Exception:
                    pass

    # ------------------------------------------------------------------

    def _fill_pending(self):
        for card in (self._os_card, self._cpu_card, self._ram_card,
                     self._gpu_card, self._disk_card):
            card.clear()
            dim_label(card.body, "—", size=12).pack(anchor="w")

    def _populate(self):
        info = self.app.system_info
        if not info:
            return

        # OS
        self._os_card.clear()
        self._kv_rows(self._os_card.body, [
            ("OS",          info.os_name),
            ("Architecture", info.architecture),
            ("Kernel",      info.os_version[:60] + (
                "…" if len(info.os_version) > 60 else "")),
        ])

        # CPU
        self._cpu_card.clear()
        cpu = info.cpu
        self._kv_rows(self._cpu_card.body, [
            ("Model",     cpu.model),
            ("Cores",     f"{cpu.physical_cores} physical  ·  {cpu.logical_cores} logical"),
            ("Frequency", f"{cpu.max_freq_mhz:.0f} MHz" if cpu.max_freq_mhz else "N/A"),
            ("Type",      "Apple Silicon (ARM64)" if cpu.is_apple_silicon
                          else cpu.architecture),
        ])

        # RAM with progress bar
        self._ram_card.clear()
        ram_used = info.ram_total_gb - info.ram_available_gb
        UsageBar(
            self._ram_card.body, "RAM usage",
            ram_used, info.ram_total_gb, "GB",
            color=C["purple"],
        ).pack(fill="x", pady=(4, 12))
        self._kv_rows(self._ram_card.body, [
            ("Total",     f"{info.ram_total_gb:.1f} GB"),
            ("Available", f"{info.ram_available_gb:.1f} GB"),
            ("Used",      f"{ram_used:.1f} GB"),
        ])

        # GPU
        self._gpu_card.clear()
        if info.gpus:
            for idx, g in enumerate(info.gpus):
                if idx:
                    hairline(self._gpu_card.body, pad_y=(8, 8))
                accel = []
                if g.cuda_available:  accel.append("CUDA")
                if g.metal_available: accel.append("Metal")
                if g.rocm_available:  accel.append("ROCm")

                head = ctk.CTkFrame(self._gpu_card.body, fg_color="transparent")
                head.pack(fill="x", pady=(2, 2))
                label(head, g.name, size=13, weight="bold").pack(side="left")
                if accel:
                    for a in accel:
                        chip(head, a, color=C["pink"],
                             bg="#251525").pack(side="left", padx=4)
                self._kv_rows(self._gpu_card.body, [
                    ("VRAM", _vram_str(g.vram_mb)),
                    ("Type", g.gpu_type.title()),
                ])
        else:
            dim_label(self._gpu_card.body,
                      "No discrete GPU detected — CPU-only inference.",
                      size=12, wraplength=380).pack(anchor="w")

        # Disk with progress bar (used)
        self._disk_card.clear()
        disk_used = info.disk_total_gb - info.disk_free_gb
        UsageBar(
            self._disk_card.body, "Disk usage",
            disk_used, info.disk_total_gb, "GB",
            color=C["yellow"],
        ).pack(fill="x", pady=(4, 12))
        kv = ctk.CTkFrame(self._disk_card.body, fg_color="transparent")
        kv.pack(fill="x")
        for k, v in [("Total", f"{info.disk_total_gb:.1f} GB"),
                     ("Free",  f"{info.disk_free_gb:.1f} GB"),
                     ("Used",  f"{disk_used:.1f} GB")]:
            col = ctk.CTkFrame(kv, fg_color="transparent")
            col.pack(side="left", padx=(0, 28))
            sub_label(col, k.upper(), size=10).pack(anchor="w")
            label(col, v, size=14, weight="bold").pack(anchor="w")

    def _kv_rows(self, parent, rows):
        for k, v in rows:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=3)
            dim_label(row, k, size=12).pack(side="left", anchor="w")
            label(row, v, size=12).pack(side="right", anchor="e")
