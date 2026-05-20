"""
Alias Manager page — create / view / delete claude-local aliases.
Routes Claude Code directly through Ollama's Anthropic-compatible API.
"""

import threading
import shutil
import subprocess
import webbrowser
import customtkinter as ctk

from ..app import (
    BasePage, C,
    card_frame, label, dim_label, sub_label,
    accent_button, ghost_button, chip, badge, status_dot, hairline,
)


class AliasRow(ctk.CTkFrame):
    """One row in the alias list with model + path + delete."""

    def __init__(self, parent, status, on_delete):
        super().__init__(
            parent, fg_color=C["card"], corner_radius=12,
            border_width=1, border_color=C["border"],
        )

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=18, pady=14)

        name_row = ctk.CTkFrame(left, fg_color="transparent")
        name_row.pack(anchor="w")
        label(name_row, status.alias_name, size=14, weight="bold").pack(side="left")
        if status.on_path:
            chip(name_row, "on PATH", color=C["green"],
                 bg="#0e2a1c").pack(side="left", padx=8)
        else:
            chip(name_row, "not on PATH", color=C["yellow"],
                 bg="#2a1f0a").pack(side="left", padx=8)

        meta = ctk.CTkFrame(left, fg_color="transparent")
        meta.pack(anchor="w", pady=(6, 2))
        chip(meta, status.model_id, color=C["accent_lt"],
             bg="#0e2522").pack(side="left", padx=(0, 6))
        chip(meta, status.ollama_url, color=C["dim"],
             bg=C["bg_alt"]).pack(side="left")

        sub_label(left, status.wrapper_path, size=10).pack(
            anchor="w", pady=(6, 0))

        ghost_button(self, "✕  Remove",
                     on_delete, width=110, color=C["red"]).pack(
            side="right", padx=18, pady=14)


class AliasPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        self._refresh_list()
        self._refresh_status()

    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Aliases",
            "Create a separate command that routes Claude Code to a local Ollama model — no proxy needed.",
        )

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=32, pady=(0, 24))
        outer.columnconfigure(0, weight=3)
        outer.columnconfigure(1, weight=2)

        # ── Left column: list + how-it-works ──────────────────────────
        left = ctk.CTkFrame(outer, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))
        label(hdr, "Your local aliases", size=15, weight="bold").pack(side="left")
        ghost_button(hdr, "⟳", self._refresh_list, width=40,
                     color=C["accent"]).pack(side="right")

        self._list_frame = ctk.CTkFrame(left, fg_color="transparent")
        self._list_frame.pack(fill="x")

        # How-it-works
        info_card = card_frame(left)
        info_card.pack(fill="x", pady=(18, 0))
        head = ctk.CTkFrame(info_card, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(head, text="⚡", font=ctk.CTkFont(size=18),
                     text_color=C["accent"]).pack(side="left")
        label(head, "  How it works", size=13, weight="bold").pack(side="left")

        rows = [
            ("claude",       "→  Anthropic cloud API  (your ANTHROPIC_API_KEY)",
             C["indigo"]),
            ("claude-local", "→  Ollama direct  (no proxy, no extra packages)",
             C["accent"]),
        ]
        for cmd, desc, col in rows:
            r = ctk.CTkFrame(info_card, fg_color="transparent")
            r.pack(fill="x", padx=18, pady=4)
            label(r, cmd, size=13, weight="bold", color=col).pack(side="left")
            dim_label(r, "  " + desc, size=12).pack(side="left")
        sub_label(
            info_card,
            "Ollama exposes a native Anthropic-compatible /v1/messages endpoint, "
            "so Claude Code talks to it directly.",
            size=11, wraplength=440,
        ).pack(anchor="w", padx=18, pady=(6, 14))

        # ── Right column: create form ─────────────────────────────────
        form_card = card_frame(outer)
        form_card.grid(row=0, column=1, sticky="nsew", padx=(14, 0))

        head2 = ctk.CTkFrame(form_card, fg_color="transparent")
        head2.pack(fill="x", padx=18, pady=(18, 4))
        label(head2, "Create new alias", size=15, weight="bold").pack(side="left")
        chip(head2, "claude-local style", color=C["accent"],
             bg="#0e2522").pack(side="left", padx=10)

        # Alias name
        self._name_entry = self._form_field(form_card, "Alias name",
                                            "claude-local")
        # Model dropdown
        local_models = self._get_local_model_ids()
        label(form_card, "Ollama model", size=12,
              color=C["dim"]).pack(anchor="w", padx=18, pady=(12, 4))
        self._model_combo = ctk.CTkComboBox(
            form_card,
            values=local_models or [
                "qwen2.5-coder:7b", "llama3.1:8b",
                "deepseek-r1:7b", "gemma3:4b",
            ],
            fg_color=C["bg_alt"], border_color=C["border"],
            button_color=C["accent"], button_hover_color=C["accent_dk"],
            dropdown_fg_color=C["card"], dropdown_hover_color=C["border"],
            text_color=C["text"], font=ctk.CTkFont(size=13),
            width=300, height=38, corner_radius=10,
        )
        self._model_combo.pack(anchor="w", padx=18, fill="x")
        sub_label(form_card,
                  "You can type any Ollama model ID above.",
                  size=10).pack(anchor="w", padx=18, pady=(4, 0))

        # Ollama URL
        self._url_entry = self._form_field(form_card, "Ollama URL",
                                           "http://localhost:11434")

        # Dependency status panel
        status_card = ctk.CTkFrame(form_card, fg_color=C["bg_alt"],
                                   corner_radius=10)
        status_card.pack(fill="x", padx=18, pady=(14, 4))
        self._dep_frame = ctk.CTkFrame(status_card, fg_color="transparent")
        self._dep_frame.pack(fill="x", padx=12, pady=10)

        self._ollama_link = ctk.CTkButton(
            form_card, text="Get Ollama →",
            fg_color="transparent", text_color=C["accent"],
            hover_color=C["card_hi"], font=ctk.CTkFont(size=11),
            corner_radius=4, height=22,
            command=lambda: webbrowser.open("https://ollama.ai"),
        )

        self._create_status = dim_label(form_card, "", size=12)
        self._create_status.pack(anchor="w", padx=18, pady=(8, 4))

        self._create_btn = accent_button(form_card, "＋  Create alias",
                                         self._do_create, width=220)
        self._create_btn.pack(anchor="w", padx=18, pady=(4, 18))

    # ------------------------------------------------------------------

    def _form_field(self, parent, title, placeholder):
        label(parent, title, size=12, color=C["dim"]).pack(
            anchor="w", padx=18, pady=(12, 4))
        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            fg_color=C["bg_alt"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["sub"],
            font=ctk.CTkFont(size=13),
            height=38, corner_radius=10,
        )
        entry.pack(anchor="w", padx=18, fill="x")
        return entry

    def _refresh_status(self):
        for w in self._dep_frame.winfo_children():
            w.destroy()
        ollama_ok = shutil.which("ollama") is not None
        node_ok   = shutil.which("node") is not None

        status_dot(self._dep_frame, ollama_ok,
                   "Ollama installed" if ollama_ok
                   else "Ollama not found — needed to run local models").pack(
            anchor="w", pady=3)
        status_dot(self._dep_frame, node_ok,
                   "Node.js installed" if node_ok
                   else "Node.js not found — needed for Claude Code").pack(
            anchor="w", pady=3)

        if not ollama_ok:
            self._ollama_link.pack(anchor="w", padx=14)
        else:
            self._ollama_link.pack_forget()

    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        from ...setup.alias_manager import AliasManager
        statuses = AliasManager().list_aliases()

        if not statuses:
            empty = card_frame(self._list_frame)
            empty.pack(fill="x", pady=8)
            ctk.CTkFrame(empty, fg_color="transparent", height=12).pack()
            ctk.CTkLabel(empty, text="🔗", font=ctk.CTkFont(size=32),
                         text_color=C["accent"]).pack()
            label(empty, "No local aliases yet",
                  size=14, weight="bold").pack(pady=(6, 2))
            dim_label(
                empty,
                "Create one with the form on the right to route Claude Code "
                "to a local Ollama model.",
                size=12, wraplength=420,
            ).pack(pady=(0, 16), padx=14)
        else:
            for s in statuses:
                row = AliasRow(
                    self._list_frame, s,
                    on_delete=lambda n=s.alias_name: self._do_remove(n),
                )
                row.pack(fill="x", pady=4)

    def _do_create(self):
        from ...setup.alias_manager import AliasManager
        name  = self._name_entry.get().strip() or "claude-local"
        model = self._model_combo.get().strip() or "qwen2.5-coder:7b"
        url   = self._url_entry.get().strip() or "http://localhost:11434"

        self._create_status.configure(text="Creating…", text_color=C["dim"])
        self._create_btn.configure(state="disabled")

        def _run():
            mgr  = AliasManager(on_log=lambda m: None)
            info = mgr.create(alias_name=name, model_id=model, ollama_url=url)
            self.app.after(0, lambda: self._on_create_done(info, name))

        threading.Thread(target=_run, daemon=True).start()

    def _on_create_done(self, info, name):
        self._create_btn.configure(state="normal")
        if info:
            self._create_status.configure(
                text=f"✓ '{name}' created — reload your shell to use it.",
                text_color=C["green"],
            )
        else:
            self._create_status.configure(text="Creation failed.",
                                          text_color=C["red"])
        self._refresh_list()

    def _do_remove(self, alias_name: str):
        from ...setup.alias_manager import AliasManager
        AliasManager().remove(alias_name)
        self._refresh_list()

    def _get_local_model_ids(self):
        if not shutil.which("ollama"):
            return []
        try:
            r = subprocess.run(["ollama", "list"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                lines = r.stdout.strip().splitlines()[1:]
                return [line.split()[0] for line in lines if line.strip()]
        except Exception:
            pass
        return []
