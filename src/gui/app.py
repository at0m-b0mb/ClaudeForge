"""
ClaudeForge — Modern GUI
Main application window, sidebar, theme, and shared widgets.
"""

import math
import platform
import threading
import tkinter as tk
import customtkinter as ctk

# ── Global theme ──────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_NAME = "ClaudeForge"
VERSION  = "1.2.0"
GITHUB   = "github.com/at0m-b0mb/ClaudeForge"

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "bg":         "#0a0e17",
    "bg_alt":     "#0e131f",
    "sidebar":    "#080b13",
    "card":       "#161b27",
    "card_hi":    "#1e2533",
    "border":     "#222a3a",
    "border_lt":  "#2e3850",
    "accent":     "#5eead4",
    "accent_dk":  "#14b8a6",
    "accent_lt":  "#99f6e4",
    "purple":     "#a78bfa",
    "indigo":     "#818cf8",
    "pink":       "#f472b6",
    "text":       "#e6ecf5",
    "dim":        "#8b95a8",
    "sub":        "#5a6478",
    "green":      "#34d399",
    "yellow":     "#fbbf24",
    "red":        "#f87171",
    "nav_hover":  "#11161f",
    "nav_active": "#1a2030",
    "ink":        "#06090f",
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

# Toast kinds → (icon, accent color, bg color)
TOAST_KINDS = {
    "success": ("✓", C["green"],  "#0e2a1c"),
    "error":   ("✕", C["red"],    "#2a1212"),
    "warn":    ("!", C["yellow"], "#2a1f0a"),
    "info":    ("ⓘ", C["accent"], "#0e2522"),
}


# ── Font + colour helpers ─────────────────────────────────────────────────────

def _font(size=13, weight="normal"):
    return ctk.CTkFont(size=size, weight=weight)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{int(max(0, min(255, c))):02x}" for c in rgb)


def _mix(c1, c2, t):
    a = _hex_to_rgb(c1)
    b = _hex_to_rgb(c2)
    return _rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


# ── Widget helpers ────────────────────────────────────────────────────────────

def card_frame(parent, **kw):
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
    fg = color or C["accent"]
    background = bg or "#0e2522"
    return ctk.CTkLabel(
        parent, text=f"  {text}  ",
        font=_font(10, "bold"),
        text_color=fg, fg_color=background,
        corner_radius=10,
    )


def badge(parent, text, color):
    f = ctk.CTkFrame(parent, fg_color=color, corner_radius=8)
    ctk.CTkLabel(
        f, text=text, font=_font(11, "bold"),
        text_color=C["ink"],
    ).pack(padx=10, pady=3)
    return f


def status_dot(parent, ok: bool, text: str):
    color = C["green"] if ok else C["red"]
    f = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(f, text="●", font=_font(11), text_color=color).pack(side="left")
    ctk.CTkLabel(f, text=f"  {text}", font=_font(12),
                 text_color=C["text"]).pack(side="left")
    return f


def hairline(parent, color=None, pad_x=0, pad_y=0):
    f = ctk.CTkFrame(parent, height=1, fg_color=color or C["border"])
    f.pack(fill="x", padx=pad_x, pady=pad_y)
    return f


def attach_hover_lift(widget, base_border=None, hover_border=None,
                      base_fg=None, hover_fg=None):
    """Make a CTkFrame brighten on mouse-enter."""
    base_border  = base_border  or C["border"]
    hover_border = hover_border or C["accent"]
    base_fg      = base_fg      or C["card"]
    hover_fg     = hover_fg     or C["card_hi"]

    def _enter(_e):
        widget.configure(border_color=hover_border, fg_color=hover_fg)
    def _leave(_e):
        widget.configure(border_color=base_border, fg_color=base_fg)

    widget.bind("<Enter>", _enter)
    widget.bind("<Leave>", _leave)
    for child in widget.winfo_children():
        try:
            child.bind("<Enter>", _enter)
            child.bind("<Leave>", _leave)
        except Exception:
            pass


# ── Canvas widgets ────────────────────────────────────────────────────────────

class DonutGauge(tk.Canvas):
    """Animated circular score gauge with multi-stop gradient ring."""

    def __init__(self, parent, value=0, max_val=100, color=None,
                 gradient=None, size=180, thickness=14, bg=None,
                 label_text=""):
        bg = bg or C["card"]
        super().__init__(
            parent, width=size, height=size,
            highlightthickness=0, bd=0, bg=bg,
        )
        self._size = size
        self._thickness = thickness
        self._max = max_val
        self._target = max(0.0, min(1.0, value / max_val if max_val else 0))
        # Build gradient stops
        if gradient is None:
            base = color or C["accent"]
            gradient = [base, base]
        elif isinstance(gradient, str):
            gradient = [gradient, gradient]
        self._gradient = gradient
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

    def _gradient_color(self, t):
        """Return interpolated color along the gradient stops at t in [0,1]."""
        stops = self._gradient
        if len(stops) < 2:
            return stops[0]
        # Find segment
        n = len(stops) - 1
        seg = min(n - 1, int(t * n))
        local_t = (t * n) - seg
        return _mix(stops[seg], stops[seg + 1], local_t)

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
        # Foreground ring drawn as small segments to fake a gradient
        if frac > 0:
            total = 360 * frac
            steps = max(1, int(total / 4))  # 4° per segment
            for i in range(steps):
                p = i / max(1, steps - 1)
                col = self._gradient_color(p)
                self.create_arc(
                    t, t, s - t, s - t,
                    start=90 - (total * i / steps),
                    extent=-(total / steps) - 0.5,
                    style="arc", outline=col, width=t,
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
        self._bars = bars
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
            self.create_rectangle(
                x0, pad_t, x0 + bar_w, y1,
                fill=C["border"], outline="",
            )
            if h > 1:
                self.create_rectangle(
                    x0, y0, x0 + bar_w, y1,
                    fill=color, outline="",
                )
            self.create_text(
                x0 + bar_w / 2, y0 - 10,
                text=f"{int(val)}",
                fill=C["text"],
                font=("Helvetica", 11, "bold"),
            )
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
        fill.place(relx=0, rely=0, relheight=1,
                   relwidth=max(0.02, min(1, pct)))


class Skeleton(ctk.CTkFrame):
    """Shimmering placeholder used while data loads."""

    def __init__(self, parent, height=12, width=None, corner_radius=6):
        super().__init__(parent, fg_color=C["card_hi"], height=height,
                         corner_radius=corner_radius)
        if width:
            self.configure(width=width)
        self.pack_propagate(False)
        # Shimmering highlight (a small bar that moves across)
        self._shimmer = ctk.CTkFrame(
            self, fg_color=C["border_lt"], corner_radius=corner_radius,
        )
        self._shimmer.place(relx=-0.3, rely=0, relwidth=0.3, relheight=1)
        self._x = -0.3
        self._animating = True
        self.after(60, self._tick)

    def _tick(self):
        if not self._animating:
            return
        self._x += 0.03
        if self._x > 1.1:
            self._x = -0.3
        try:
            self._shimmer.place(relx=self._x, rely=0,
                                relwidth=0.3, relheight=1)
            self.after(60, self._tick)
        except Exception:
            self._animating = False

    def stop(self):
        self._animating = False


# ── Toast notifications ───────────────────────────────────────────────────────

class Toast(ctk.CTkFrame):
    """Slide-in notification banner shown at top of the main area."""

    def __init__(self, parent, message, kind="info", duration_ms=3200,
                 on_close=None):
        icon, accent, bg = TOAST_KINDS.get(kind, TOAST_KINDS["info"])
        super().__init__(
            parent,
            fg_color=bg,
            corner_radius=12,
            border_width=1,
            border_color=accent,
        )
        self._on_close = on_close

        ctk.CTkLabel(
            self, text=icon, font=_font(16, "bold"),
            text_color=accent,
        ).pack(side="left", padx=(14, 6), pady=10)
        ctk.CTkLabel(
            self, text=message, font=_font(12, "bold"),
            text_color=C["text"],
        ).pack(side="left", padx=(2, 10), pady=10)
        ctk.CTkButton(
            self, text="✕", width=24, height=24,
            fg_color="transparent", hover_color=bg,
            text_color=C["sub"], font=_font(11),
            corner_radius=8,
            command=self._dismiss,
        ).pack(side="right", padx=(2, 8), pady=6)

        self.after(duration_ms, self._dismiss)

    def _dismiss(self):
        try:
            self.destroy()
        finally:
            if self._on_close:
                self._on_close(self)


class ToastStack(ctk.CTkFrame):
    """Stacks active toasts in the top-right of the main content area."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        # placed by App
        self._toasts = []

    def show(self, message, kind="info", duration_ms=3200):
        t = Toast(self, message, kind=kind, duration_ms=duration_ms,
                  on_close=self._remove)
        t.pack(anchor="ne", pady=(0, 8))
        self._toasts.append(t)
        # Keep only the last 4
        while len(self._toasts) > 4:
            old = self._toasts.pop(0)
            try:
                old.destroy()
            except Exception:
                pass

    def _remove(self, toast):
        if toast in self._toasts:
            self._toasts.remove(toast)


# ── Sidebar ───────────────────────────────────────────────────────────────────

class Sidebar(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=C["sidebar"], corner_radius=0, width=238)
        self.app = app
        self._buttons = {}
        self._build()

    def _build(self):
        self.pack_propagate(False)

        # Logo
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
            fill="x", padx=14, pady=(12, 12)
        )

        # Nav buttons
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=10)

        mod_key = "⌘" if platform.system() == "Darwin" else "Ctrl"
        for i, (page_key, label_text, icon) in enumerate(NAV_ITEMS, start=1):
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

        # Spacer pushes status panel to the bottom
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        # ── Bottom status panel ────────────────────────────────────────
        status_card = ctk.CTkFrame(
            self, fg_color=C["bg_alt"], corner_radius=12,
            border_width=1, border_color=C["border"],
        )
        status_card.pack(fill="x", padx=10, pady=(0, 10), side="bottom")

        # Machine
        head = ctk.CTkFrame(status_card, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(12, 2))
        ctk.CTkLabel(head, text="●", font=_font(10),
                     text_color=C["dim"]).pack(side="left")
        self._machine_lbl = ctk.CTkLabel(
            head, text="  Detecting…",
            font=_font(11, "bold"), text_color=C["text"],
        )
        self._machine_lbl.pack(side="left")
        self._machine_dot = head.winfo_children()[0]

        self._machine_sub = ctk.CTkLabel(
            status_card, text="",
            font=_font(10), text_color=C["sub"],
            anchor="w",
        )
        self._machine_sub.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkFrame(status_card, height=1, fg_color=C["border"]).pack(
            fill="x", padx=10
        )

        # Tier pill
        self._tier_pill_holder = ctk.CTkFrame(status_card, fg_color="transparent")
        self._tier_pill_holder.pack(fill="x", padx=12, pady=(8, 4))

        # Claude + Ollama status rows
        self._claude_row = ctk.CTkFrame(status_card, fg_color="transparent")
        self._claude_row.pack(fill="x", padx=12, pady=(4, 2))
        self._ollama_row = ctk.CTkFrame(status_card, fg_color="transparent")
        self._ollama_row.pack(fill="x", padx=12, pady=(2, 10))

        # Footer
        ctk.CTkLabel(
            self, text=f"{GITHUB}   ·   {mod_key}+1…{len(NAV_ITEMS)} nav",
            font=_font(9), text_color=C["sub"],
        ).pack(side="bottom", pady=(0, 8))

        self.refresh_status()

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

    def refresh_status(self):
        """Update the bottom status panel from app state."""
        import shutil
        info  = self.app.system_info
        bench = self.app.bench_result

        # Machine line
        if info:
            self._machine_dot.configure(text_color=C["green"])
            short = info.os_name
            if len(short) > 22:
                short = short[:21] + "…"
            self._machine_lbl.configure(text="  " + short)
            sub = f"{info.cpu.physical_cores}C  ·  {info.ram_total_gb:.0f} GB RAM"
            self._machine_sub.configure(text=sub)
        else:
            self._machine_dot.configure(text_color=C["yellow"])
            self._machine_lbl.configure(text="  Detecting…")
            self._machine_sub.configure(text="Scanning hardware in background")

        # Tier pill
        for w in self._tier_pill_holder.winfo_children():
            w.destroy()
        if bench:
            col = TIER_COLORS.get(bench.tier, C["accent"])
            pill = ctk.CTkFrame(
                self._tier_pill_holder, fg_color=C["card_hi"],
                corner_radius=14, border_width=1, border_color=col,
            )
            pill.pack(fill="x")
            ctk.CTkLabel(
                pill, text=f"  {bench.tier.upper()} TIER",
                font=_font(10, "bold"), text_color=col,
            ).pack(side="left", padx=(4, 0), pady=4)
            ctk.CTkLabel(
                pill, text=f"  {bench.overall_score:.0f}/100  ",
                font=_font(11, "bold"), text_color=C["text"],
            ).pack(side="right", padx=(0, 4), pady=4)
        elif info:
            ctk.CTkButton(
                self._tier_pill_holder, text="▶  Run benchmark",
                fg_color=C["accent"], hover_color=C["accent_dk"],
                text_color=C["ink"], font=_font(11, "bold"),
                corner_radius=10, height=28,
                command=lambda: self.app.show_page("benchmark"),
            ).pack(fill="x", pady=2)
        else:
            ctk.CTkLabel(
                self._tier_pill_holder, text="No benchmark yet",
                font=_font(10), text_color=C["sub"],
            ).pack(anchor="w", pady=2)

        # Claude / Ollama statuses
        for w in self._claude_row.winfo_children():
            w.destroy()
        for w in self._ollama_row.winfo_children():
            w.destroy()

        claude_ok = shutil.which("claude") is not None
        ollama_ok = shutil.which("ollama") is not None
        ctk.CTkLabel(self._claude_row,
                     text="●", font=_font(9),
                     text_color=C["green"] if claude_ok else C["sub"]
                     ).pack(side="left")
        ctk.CTkLabel(self._claude_row,
                     text="  Claude Code",
                     font=_font(10), text_color=C["dim"]
                     ).pack(side="left")
        ctk.CTkLabel(self._claude_row,
                     text="installed" if claude_ok else "missing",
                     font=_font(10, "bold"),
                     text_color=C["green"] if claude_ok else C["yellow"]
                     ).pack(side="right")

        ctk.CTkLabel(self._ollama_row,
                     text="●", font=_font(9),
                     text_color=C["green"] if ollama_ok else C["sub"]
                     ).pack(side="left")
        ctk.CTkLabel(self._ollama_row,
                     text="  Ollama",
                     font=_font(10), text_color=C["dim"]
                     ).pack(side="left")
        ctk.CTkLabel(self._ollama_row,
                     text="installed" if ollama_ok else "missing",
                     font=_font(10, "bold"),
                     text_color=C["green"] if ollama_ok else C["yellow"]
                     ).pack(side="right")


# ── Base page ─────────────────────────────────────────────────────────────────

class BasePage(ctk.CTkScrollableFrame):
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
        pass

    def page_header(self, title: str, subtitle: str = "",
                    right_widget_factory=None):
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

        self.system_info    = None
        self.bench_result   = None
        self.recommendation = None

        self._build_layout()
        self._bind_shortcuts()
        self.show_page("dashboard")

        self.after(200, self._background_detect)

    # ── Layout ────────────────────────────────────────────────────────

    def _build_layout(self):
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
        self._container = container

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

        # Toast stack — overlay in the top-right corner of the container
        self.toasts = ToastStack(container)
        self.toasts.place(relx=1.0, rely=0, x=-20, y=20, anchor="ne")
        self.toasts.lift()

    # ── Navigation + transitions ──────────────────────────────────────

    def _bind_shortcuts(self):
        keys = [k for k, _, _ in NAV_ITEMS]
        mod = "Command" if platform.system() == "Darwin" else "Control"
        for i, page_key in enumerate(keys, start=1):
            seq = f"<{mod}-Key-{i}>"
            self.bind_all(seq, lambda _e, k=page_key: self.show_page(k))
        # Reload current page (debug)
        self.bind_all(f"<{mod}-r>", lambda _e: self._fade_in(self.current_page))

    def show_page(self, name: str):
        self.current_page = name
        for key, page in self.pages.items():
            if key == name:
                page.lift()
                try:
                    page.on_show()
                except Exception:
                    pass
        self.sidebar.set_active(name)
        # Keep toasts on top
        try:
            self.toasts.lift()
        except Exception:
            pass
        self._fade_in(name)

    def _fade_in(self, name):
        """Subtle fade-in by sliding page down slightly."""
        page = self.pages.get(name)
        if page is None:
            return
        try:
            page.place(relx=0, rely=0.012, relwidth=1, relheight=1)
            steps = 6
            def step(i):
                if i >= steps:
                    page.place(relx=0, rely=0, relwidth=1, relheight=1)
                    try:
                        self.toasts.lift()
                    except Exception:
                        pass
                    return
                page.place(relx=0, rely=0.012 * (1 - i / steps),
                           relwidth=1, relheight=1)
                self.after(16, lambda: step(i + 1))
            step(0)
        except Exception:
            pass

    # ── Toasts ─────────────────────────────────────────────────────────

    def show_toast(self, message, kind="info", duration_ms=3200):
        """Public API: surface a slide-in notification."""
        try:
            self.toasts.show(message, kind=kind, duration_ms=duration_ms)
            self.toasts.lift()
        except Exception:
            pass

    # ── Hardware detection ────────────────────────────────────────────

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
        try:
            self.sidebar.refresh_status()
        except Exception:
            pass


def launch():
    app = ClaudeForgeApp()
    app.mainloop()
