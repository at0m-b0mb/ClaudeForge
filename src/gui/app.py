"""
ClaudeForge — Modern GUI
Main application window + sidebar navigation.
"""

import threading
import customtkinter as ctk

# ── Global theme ──────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_NAME = "ClaudeForge"
VERSION  = "1.0.0"
GITHUB   = "github.com/at0m-b0mb/ClaudeForge"

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "bg":        "#0d1117",   # main background
    "sidebar":   "#161b22",   # sidebar
    "card":      "#21262d",   # card / surface
    "border":    "#30363d",   # subtle border
    "accent":    "#4ac6b7",   # teal accent (Claude-ish)
    "accent_dk": "#2a9d8f",   # darker teal for hover
    "purple":    "#7c3aed",   # purple accent
    "text":      "#e6edf3",   # primary text
    "dim":       "#8b949e",   # secondary text
    "green":     "#3fb950",
    "yellow":    "#d29922",
    "red":       "#f85149",
    "nav_hover": "#1c2128",   # nav button hover
    "nav_active":"#21262d",   # nav button active bg
}

NAV_ITEMS = [
    ("dashboard", "  Dashboard",  "🏠"),
    ("hardware",  "  Hardware",   "💻"),
    ("benchmark", "  Benchmark",  "⚡"),
    ("models",    "  Models",     "🤖"),
    ("install",   "  Install",    "📦"),
    ("alias",     "  Aliases",    "🔗"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def card_frame(parent, **kw):
    """Styled card frame."""
    defaults = dict(
        fg_color=C["card"],
        corner_radius=12,
        border_width=1,
        border_color=C["border"],
    )
    defaults.update(kw)
    return ctk.CTkFrame(parent, **defaults)


def label(parent, text, size=13, weight="normal", color=None, **kw):
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(size=size, weight=weight),
        text_color=color or C["text"],
        **kw,
    )


def dim_label(parent, text, size=12, **kw):
    return label(parent, text, size=size, color=C["dim"], **kw)


def accent_button(parent, text, command, width=140, height=36, **kw):
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=C["accent"], hover_color=C["accent_dk"],
        text_color="#0d1117", font=ctk.CTkFont(size=13, weight="bold"),
        corner_radius=8, width=width, height=height,
        **kw,
    )


def badge(parent, text, color):
    """Coloured rounded badge."""
    f = ctk.CTkFrame(parent, fg_color=color, corner_radius=6, width=1, height=1)
    ctk.CTkLabel(
        f, text=text,
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color="#0d1117",
    ).pack(padx=8, pady=2)
    return f


def status_dot(parent, ok: bool, text: str):
    """Small coloured dot + label."""
    color = C["green"] if ok else C["red"]
    f = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(f, text="●", font=ctk.CTkFont(size=10), text_color=color).pack(side="left")
    ctk.CTkLabel(f, text=f"  {text}", font=ctk.CTkFont(size=12), text_color=C["text"]).pack(side="left")
    return f


# ── Sidebar ───────────────────────────────────────────────────────────────────

class Sidebar(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=C["sidebar"], corner_radius=0, width=220)
        self.app = app
        self._buttons = {}
        self._build()

    def _build(self):
        self.pack_propagate(False)

        # Logo block
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(22, 6))
        ctk.CTkLabel(
            logo_frame, text="⚡ ClaudeForge",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C["accent"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame, text=f"v{VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=C["dim"],
        ).pack(anchor="w")

        ctk.CTkFrame(self, height=1, fg_color=C["border"]).pack(fill="x", padx=12, pady=(8, 14))

        # Nav buttons
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=8)

        for page_key, label_text, icon in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"{icon}  {label_text.strip()}",
                anchor="w",
                fg_color="transparent",
                hover_color=C["nav_hover"],
                text_color=C["dim"],
                font=ctk.CTkFont(size=13),
                corner_radius=8,
                height=40,
                command=lambda k=page_key: self.app.show_page(k),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[page_key] = btn

        # Bottom: GitHub link
        ctk.CTkFrame(self, height=1, fg_color=C["border"]).pack(fill="x", padx=12, pady=(0, 10), side="bottom")
        ctk.CTkLabel(
            self, text=GITHUB,
            font=ctk.CTkFont(size=10),
            text_color=C["dim"],
        ).pack(side="bottom", pady=(0, 6))

    def set_active(self, page_key: str):
        for key, btn in self._buttons.items():
            if key == page_key:
                btn.configure(
                    fg_color=C["nav_active"],
                    text_color=C["text"],
                    font=ctk.CTkFont(size=13, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=C["dim"],
                    font=ctk.CTkFont(size=13, weight="normal"),
                )


# ── Base page ─────────────────────────────────────────────────────────────────

class BasePage(ctk.CTkScrollableFrame):
    """All pages inherit from this. Provides `self.app` and page header helpers."""

    def __init__(self, parent, app, **kw):
        super().__init__(
            parent,
            fg_color=C["bg"],
            scrollbar_button_color=C["card"],
            scrollbar_button_hover_color=C["border"],
            **kw,
        )
        self.app = app

    def on_show(self):
        """Called every time this page becomes visible."""
        pass

    def page_header(self, title: str, subtitle: str = ""):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=28, pady=(24, 4))
        ctk.CTkLabel(
            f, text=title,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=C["text"],
        ).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                f, text=subtitle,
                font=ctk.CTkFont(size=13),
                text_color=C["dim"],
            ).pack(anchor="w", pady=(2, 0))
        ctk.CTkFrame(self, height=1, fg_color=C["border"]).pack(fill="x", padx=28, pady=(8, 16))


# ── App ───────────────────────────────────────────────────────────────────────

class ClaudeForgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ClaudeForge")
        self.geometry("1200x760")
        self.minsize(960, 620)
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
        from .pages.dashboard    import DashboardPage
        from .pages.hardware_page import HardwarePage
        from .pages.benchmark_page import BenchmarkPage
        from .pages.models_page  import ModelsPage
        from .pages.install_page import InstallPage
        from .pages.alias_page   import AliasPage

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
            self.system_info = HardwareDetector().detect()
            self.after(0, self._on_detect_complete)
        threading.Thread(target=_run, daemon=True).start()

    def _on_detect_complete(self):
        for page in self.pages.values():
            if hasattr(page, "on_hardware_ready"):
                page.on_hardware_ready()


def launch():
    """Launch the ClaudeForge GUI. Call from main.py --gui."""
    app = ClaudeForgeApp()
    app.mainloop()
