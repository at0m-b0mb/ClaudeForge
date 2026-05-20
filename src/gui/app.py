"""
ClaudeForge — Modern GUI
Main application window, sidebar, theme, and shared widgets.
"""

import math
import threading
import tkinter as tk
import customtkinter as ctk

# ── Global theme ──────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_NAME = "ClaudeForge"
VERSION  = "1.1.0"
GITHUB   = "github.com/at0m-b0mb/ClaudeForge"

# ── Colour palette ────────────────────────────────────────────────────────────
# Designed for a deep, modern look with teal-cyan "Claude-ish" accent.
C = {
    "bg":         "#0a0e17",   # app background (deep navy-black)
    "bg_alt":     "#0e131f",   # slightly raised section bg
    "sidebar":    "#080b13",   # sidebar background (darker)
    "card":       "#161b27",   # card surface
    "card_hi":    "#1e2533",   # raised / hover card
    "border":     "#222a3a",   # subtle border
    "border_lt":  "#2e3850",   # lighter border for emphasis
    "accent":     "#5eead4",   # teal-cyan accent
    "accent_dk":  "#14b8a6",   # darker teal for hover
    "accent_lt":  "#99f6e4",   # lighter shade for highlight
    "purple":     "#a78bfa",   # purple accent
    "indigo":     "#818cf8",   # indigo accent
    "pink":       "#f472b6",
    "text":       "#e6ecf5",   # primary text
    "dim":        "#8b95a8",   # secondary text
    "sub":        "#5a6478",   # tertiary text
    "green":      "#34d399",
    "yellow":     "#fbbf24",
    "red":        "#f87171",
    "nav_hover":  "#11161f",
    "nav_active": "#1a2030",
    "ink":        "#06090f",   # text on accent buttons
}

NAV_ITEMS = [
    ("dashboard", "Dashboard",  "🏠"),
    ("hardware",  "Hardware",   "💻"),
    ("benchmark", "Benchmark",  "⚡"),
    ("models",    "Models",     "🤖"),
    ("install",   "Install",    "📦"),
    ("alias",     "Aliases",    "🔗"),
    ("settings",  "Settings",   "⚙"),
]

TIER_COLORS = {
    "ultra": "#a78bfa",
    "high":  "#34d399",
    "mid":   "#fbbf24",
    "low":   "#f87171",
}


# ── Font helpers ──────────────────────────────────────────────────────────────

def _font(size=13, weight="normal"):
    return ctk.CTkFont(size=size, weight=weight)


# ── Helpers ───────────────────────────────────────────────────────────────────

def card_frame(parent, **kw):
    """Styled card frame."""
    defaults = dict(
        fg_color=C["card"],
        corner_radius=14,
        border_width=1,
        border_color=C["border"],
    )
    defaults.update(kw)
    return ctk.CTkFrame(parent, **defaults)


def label(parent, text, size=13, weight="normal", color=None, **kw):
    return ctk.CTkLabel(
        parent, text=text,
        font=_font(size, weight),
        text_color=color or C["text"],
        **kw,
    )


def dim_label(parent, text, size=12, **kw):
    return label(parent, text, size=size, color=C["dim"], **kw)


def sub_label(parent, text, size=11, **kw):
    return label(parent, text, size=size, color=C["sub"], **kw)


def accent_button(parent, text, command, width=140, height=38, **kw):
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=C["accent"], hover_color=C["accent_dk"],
        text_color=C["ink"], font=_font(13, "bold"),
        corner_radius=10, width=width, height=height,
        **kw,
    )


def ghost_button(parent, text, command, width=120, height=36, color=None, **kw):
    color = color or C["accent"]
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color="transparent", hover_color=C["card_hi"],
        text_color=color, border_color=color, border_width=1,
        font=_font(12, "bold"), corner_radius=10,
        width=width, height=height, **kw,
    )


def chip(parent, text, color=None, bg=None):
    """A small pill / chip label."""
    fg = color or C["accent"]
    background = bg or "#0e2522"
    return ctk.CTkLabel(
        parent, text=f"  {text}  ",
        font=_font(10, "bold"),
        text_color=fg,
        fg_color=background,
        corner_radius=10,
    )


def badge(parent, text, color):
    """Solid-coloured rounded badge."""
    f = ctk.CTkFrame(parent, fg_color=color, corner_radius=8)
    ctk.CTkLabel(
        f, text=text, font=_font(11, "bold"),
        text_color=C["ink"],
    ).pack(padx=10, pady=3)
    return f


def status_dot(parent, ok: bool, text: str):
    """Small coloured dot + label."""
    color = C["green"] if ok else C["red"]
    f = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(f, text="●", font=_font(11), text_color=color).pack(side="left")
    ctk.CTkLabel(f, text=f"  {text}", font=_font(12), text_color=C["text"]).pack(side="left")
    return f


def hairline(parent, color=None, pad_x=0, pad_y=0):
    """1-px horizontal divider."""
    f = ctk.CTkFrame(parent, height=1, fg_color=color or C["border"])
    f.pack(fill="x", padx=pad_x, pady=pad_y)
    return f


# ── Canvas widgets ────────────────────────────────────────────────────────────

class DonutGauge(tk.Canvas):
    """Animated circular score gauge drawn on a Tk Canvas."""

    def __init__(self, parent, value=0, max_val=100, color=None,
                 size=180, thickness=14, bg=None, label_text=""):
        bg = bg or C["card"]
        super().__init__(
            parent, width=size, height=size,
            highlightthickness=0, bd=0, bg=bg,
        )
        self._size = size
        self._thickness = thickness
        self._max = max_val
        self._target = max(0.0, min(1.0, value / max_val if max_val else 0))
        self._color = color or C["accent"]
        self._bg = bg
        self._label_text = label_text
        self._current = 0.0
        self.after(40, self._animate)

    def _animate(self):
        step = (self._target - self._current) * 0.14 + 0.005
        self._current = min(self._target, self._current + step)
        self._draw(self._current)
        if self._current < self._target - 0.003:
            self.after(16, self._animate)

    def _draw(self, frac):
        self.delete("all")
        s = self._size
        t = self._thickness
        # Background ring
        self.create_arc(
            t, t, s - t, s - t,
            start=0, extent=359.99,
            style="arc", outline=C["border"], width=t,
        )
        # Foreground arc
        if frac > 0:
            self.create_arc(
                t, t, s - t, s - t,
                start=90, extent=-360 * frac,
                style="arc", outline=self._color, width=t,
            )
        # Center value
        value = int(round(self._target * self._max))
        self.create_text(
            s / 2, s / 2 - 6,
            text=f"{value}",
            fill=C["text"],
            font=("Helvetica", int(s / 4.5), "bold"),
        )
        self.create_text(
            s / 2, s / 2 + int(s / 7),
            text=self._label_text or f"/ {self._max}",
            fill=C["dim"],
            font=("Helvetica", int(s / 14)),
        )


class BarChart(tk.Canvas):
    """Vertical bar chart for benchmark sub-scores."""

    def __init__(self, parent, bars, width=520, height=180, bg=None):
        bg = bg or C["card"]
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bd=0, bg=bg)
        self._bars = bars  # list of (label, value0-100, color)
        self._w = width
        self._h = height
        self._draw()

    def _draw(self):
        n = len(self._bars)
        if n == 0:
            return
        pad_x = 30
        pad_b = 36
        pad_t = 16
        usable_w = self._w - 2 * pad_x
        gap = 24
        bar_w = max(8, (usable_w - gap * (n - 1)) / n)
        usable_h = self._h - pad_t - pad_b

        # Faint baseline
        self.create_line(
            pad_x, self._h - pad_b,
            self._w - pad_x, self._h - pad_b,
            fill=C["border"], width=1,
        )

        for i, (lbl, val, color) in enumerate(self._bars):
            val = max(0, min(100, val))
            h = usable_h * (val / 100)
            x0 = pad_x + i * (bar_w + gap)
            y1 = self._h - pad_b
            y0 = y1 - h
            # Bar background track
            self.create_rectangle(
                x0, pad_t, x0 + bar_w, y1,
                fill=C["border"], outline="",
            )
            # Bar fill
            if h > 1:
                self.create_rectangle(
                    x0, y0, x0 + bar_w, y1,
                    fill=color, outline="",
                )
            # Value label on top
            self.create_text(
                x0 + bar_w / 2, y0 - 10,
                text=f"{int(val)}",
                fill=C["text"],
                font=("Helvetica", 11, "bold"),
            )
            # X-axis label
            self.create_text(
                x0 + bar_w / 2, self._h - pad_b + 16,
                text=lbl,
                fill=C["dim"],
                font=("Helvetica", 10),
            )


class UsageBar(ctk.CTkFrame):
    """Inline usage progress bar with label, used %, color."""

    def __init__(self, parent, label_text, used, total, unit="GB",
                 color=None, height=8):
        super().__init__(parent, fg_color="transparent")
        used = max(0, used)
        total = max(used, total) if total else max(used, 0.0001)
        pct = used / total if total else 0
        col = color or C["accent"]

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        label(row, label_text, size=12, color=C["dim"]).pack(side="left")
        label(row, f"{used:.1f} / {total:.1f} {unit}",
              size=12, color=C["text"]).pack(side="right")

        track = ctk.CTkFrame(self, fg_color=C["border"], height=height,
                             corner_radius=height // 2)
        track.pack(fill="x", pady=(6, 0))
        track.pack_propagate(False)
        fill = ctk.CTkFrame(track, fg_color=col, corner_radius=height // 2)
        fill.place(relx=0, rely=0, relheight=1, relwidth=max(0.02, min(1, pct)))


# ── Sidebar ───────────────────────────────────────────────────────────────────

class Sidebar(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=C["sidebar"], corner_radius=0, width=232)
        self.app = app
        self._buttons = {}
        self._build()

    def _build(self):
        self.pack_propagate(False)

        # Logo block
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", padx=18, pady=(24, 6))
        ctk.CTkLabel(
            logo_frame, text="⚡  ClaudeForge",
            font=_font(20, "bold"),
            text_color=C["accent"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame, text=f"v{VERSION}",
            font=_font(10), text_color=C["sub"],
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(self, height=1, fg_color=C["border"]).pack(
            fill="x", padx=14, pady=(12, 14)
        )

        # Nav buttons
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=10)

        for page_key, label_text, icon in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}    {label_text}",
                anchor="w",
                fg_color="transparent",
                hover_color=C["nav_hover"],
                text_color=C["dim"],
                font=_font(13),
                corner_radius=10,
                height=40,
                command=lambda k=page_key: self.app.show_page(k),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[page_key] = btn

        # Bottom: footer
        ctk.CTkFrame(self, height=1, fg_color=C["border"]).pack(
            fill="x", padx=14, pady=(0, 10), side="bottom"
        )
        ctk.CTkLabel(
            self, text=GITHUB,
            font=_font(10), text_color=C["sub"],
        ).pack(side="bottom", pady=(0, 10))

    def set_active(self, page_key: str):
        for key, btn in self._buttons.items():
            if key == page_key:
                btn.configure(
                    fg_color=C["nav_active"],
                    text_color=C["accent"],
                    font=_font(13, "bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=C["dim"],
                    font=_font(13),
                )


# ── Base page ─────────────────────────────────────────────────────────────────

class BasePage(ctk.CTkScrollableFrame):
    """All pages inherit from this. Provides `self.app` and page header helpers."""

    def __init__(self, parent, app, **kw):
        super().__init__(
            parent,
            fg_color=C["bg"],
            scrollbar_button_color=C["card_hi"],
            scrollbar_button_hover_color=C["border_lt"],
            **kw,
        )
        self.app = app

    def on_show(self):
        """Called every time this page becomes visible."""
        pass

    def page_header(self, title: str, subtitle: str = "", right_widget_factory=None):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=32, pady=(26, 4))

        left = ctk.CTkFrame(f, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            left, text=title,
            font=_font(28, "bold"),
            text_color=C["text"],
        ).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                left, text=subtitle,
                font=_font(13),
                text_color=C["dim"],
            ).pack(anchor="w", pady=(2, 0))

        if right_widget_factory is not None:
            right = ctk.CTkFrame(f, fg_color="transparent")
            right.pack(side="right")
            right_widget_factory(right)

        ctk.CTkFrame(self, height=1, fg_color=C["border"]).pack(
            fill="x", padx=32, pady=(14, 18)
        )


# ── App ───────────────────────────────────────────────────────────────────────

class ClaudeForgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ClaudeForge")
        self.geometry("1280x800")
        self.minsize(1024, 660)
        self.configure(fg_color=C["bg"])

        # Shared detection/benchmark state
        self.system_info    = None
        self.bench_result   = None
        self.recommendation = None

        self._build_layout()
        self.show_page("dashboard")

        # Kick off hardware detection immediately in background
        self.after(200, self._background_detect)

    def _build_layout(self):
        # Lazy import pages here to avoid circular issues at module level
        from .pages.dashboard     import DashboardPage
        from .pages.hardware_page import HardwarePage
        from .pages.benchmark_page import BenchmarkPage
        from .pages.models_page   import ModelsPage
        from .pages.install_page  import InstallPage
        from .pages.alias_page    import AliasPage
        from .pages.settings_page import SettingsPage

        self.sidebar = Sidebar(self)
        self.sidebar.pack(side="left", fill="y")

        container = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        container.pack(side="left", fill="both", expand=True)

        self.pages = {
            "dashboard": DashboardPage(container, self),
            "hardware":  HardwarePage(container, self),
            "benchmark": BenchmarkPage(container, self),
            "models":    ModelsPage(container, self),
            "install":   InstallPage(container, self),
            "alias":     AliasPage(container, self),
            "settings":  SettingsPage(container, self),
        }
        for page in self.pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

    def show_page(self, name: str):
        self.current_page = name
        for key, page in self.pages.items():
            if key == name:
                page.lift()
                page.on_show()
        self.sidebar.set_active(name)

    def _background_detect(self):
        from ..hardware.detector import HardwareDetector
        def _run():
            try:
                self.system_info = HardwareDetector().detect()
                self.after(0, self._on_detect_complete)
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    def _on_detect_complete(self):
        for page in self.pages.values():
            if hasattr(page, "on_hardware_ready"):
                try:
                    page.on_hardware_ready()
                except Exception:
                    pass


def launch():
    """Launch the ClaudeForge GUI. Call from main.py --gui."""
    app = ClaudeForgeApp()
    app.mainloop()
