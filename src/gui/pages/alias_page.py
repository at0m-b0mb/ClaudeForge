"""
Alias Manager page — create, view, and delete claude-local aliases.
"""

import threading
import shutil
import customtkinter as ctk
from ..app import BasePage, C, card_frame, label, dim_label, accent_button, badge, status_dot


class AliasRow(ctk.CTkFrame):
    """One row in the alias list."""

    def __init__(self, parent, status, on_delete):
        super().__init__(parent, fg_color=C["card"], corner_radius=10,
                         border_width=1, border_color=C["border"])

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=16, pady=12)

        name_row = ctk.CTkFrame(left, fg_color="transparent")
        name_row.pack(anchor="w")
        label(name_row, status.alias_name, size=14, weight="bold").pack(side="left")
        if status.on_path:
            badge(name_row, "on PATH", C["green"]).pack(side="left", padx=8)
        else:
            badge(name_row, "not on PATH", C["yellow"]).pack(side="left", padx=8)

        dim_label(left, f"Model: {status.model_id}   Port: {status.proxy_port}").pack(anchor="w", pady=(2, 0))
        dim_label(left, status.wrapper_path, size=10).pack(anchor="w")

        ctk.CTkButton(
            self, text="✕ Remove", width=90, height=32,
            fg_color="transparent", hover_color="#2d1515",
            text_color=C["red"], border_width=1, border_color=C["red"],
            corner_radius=8,
            command=on_delete,
        ).pack(side="right", padx=14)


class AliasPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        self._refresh_list()

    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Alias Manager",
            "Create a separate command that routes Claude Code to a local Ollama model.",
        )
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=28)
        outer.columnconfigure(0, weight=3)
        outer.columnconfigure(1, weight=2)

        # ── Left: existing aliases ────────────────────────────────────
        left = ctk.CTkFrame(outer, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))
        label(hdr, "Your Local Aliases", size=15, weight="bold").pack(side="left")
        ctk.CTkButton(
            hdr, text="⟳", width=36, height=30,
            fg_color=C["card"], hover_color=C["border"],
            text_color=C["accent"], corner_radius=8,
            command=self._refresh_list,
        ).pack(side="right")

        self._list_frame = ctk.CTkFrame(left, fg_color="transparent")
        self._list_frame.pack(fill="x")

        # Explanation
        info_card = card_frame(left)
        info_card.pack(fill="x", pady=(16, 0))
        rows = [
            ("claude",       "→  Anthropic cloud API  (unchanged)"),
            ("claude-local", "→  Ollama / local model  (via proxy)"),
        ]
        for cmd, desc in rows:
            r = ctk.CTkFrame(info_card, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=5)
            label(r, cmd, size=13, weight="bold", color=C["accent"]).pack(side="left")
            dim_label(r, f"  {desc}", size=12).pack(side="left")

        # ── Right: create form ────────────────────────────────────────
        form_card = card_frame(outer)
        form_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        label(form_card, "Create New Alias", size=14, weight="bold").pack(anchor="w", padx=16, pady=(14, 10))

        # Alias name
        self._name_entry = self._form_field(form_card, "Alias Name", "claude-local")

        # Model
        local_models = self._get_local_model_ids()
        label(form_card, "Ollama Model", size=12, color=C["dim"]).pack(anchor="w", padx=16, pady=(8, 2))
        self._model_combo = ctk.CTkComboBox(
            form_card,
            values=local_models or ["qwen2.5-coder:7b", "llama3.1:8b", "llama3.2:3b"],
            fg_color=C["bg"], border_color=C["border"],
            button_color=C["accent"], button_hover_color=C["accent_dk"],
            dropdown_fg_color=C["card"], dropdown_hover_color=C["border"],
            text_color=C["text"], font=ctk.CTkFont(size=13),
            width=220, height=36,
        )
        self._model_combo.pack(anchor="w", padx=16)
        dim_label(form_card, "Or type any Ollama model ID above", size=10).pack(anchor="w", padx=16, pady=(2, 0))

        # Port
        self._port_entry = self._form_field(form_card, "Proxy Port", "4001")

        # litellm status
        litellm_ok = shutil.which("litellm") is not None
        self._litellm_status = status_dot(form_card, litellm_ok,
                                           "litellm installed" if litellm_ok else "litellm missing")
        self._litellm_status.pack(anchor="w", padx=16, pady=(10, 4))
        if not litellm_ok:
            install_lit = ctk.CTkButton(
                form_card, text="Install litellm",
                fg_color="transparent", text_color=C["accent"],
                hover_color=C["nav_hover"], font=ctk.CTkFont(size=11),
                corner_radius=4, height=24,
                command=self._install_litellm,
            )
            install_lit.pack(anchor="w", padx=14)

        self._create_status = dim_label(form_card, "")
        self._create_status.pack(anchor="w", padx=16, pady=(6, 4))

        self._create_btn = accent_button(form_card, "＋  Create Alias", self._do_create, width=200)
        self._create_btn.pack(anchor="w", padx=16, pady=(4, 16))

    # ------------------------------------------------------------------

    def _form_field(self, parent, title, placeholder):
        label(parent, title, size=12, color=C["dim"]).pack(anchor="w", padx=16, pady=(8, 2))
        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            fg_color=C["bg"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["dim"],
            font=ctk.CTkFont(size=13),
            width=220, height=36,
            corner_radius=8,
        )
        entry.pack(anchor="w", padx=16)
        return entry

    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        from ...setup.alias_manager import AliasManager
        statuses = AliasManager().list_aliases()
        if not statuses:
            dim_label(self._list_frame,
                      "No local aliases yet. Create one using the form →",
                      size=12, wraplength=400).pack(anchor="w", pady=8)
        else:
            for s in statuses:
                row = AliasRow(self._list_frame, s, on_delete=lambda n=s.alias_name: self._do_remove(n))
                row.pack(fill="x", pady=4)

    def _do_create(self):
        from ...setup.alias_manager import AliasManager
        name  = self._name_entry.get().strip() or "claude-local"
        model = self._model_combo.get().strip() or "qwen2.5-coder:7b"
        try:
            port = int(self._port_entry.get().strip() or "4001")
        except ValueError:
            port = 4001

        self._create_status.configure(text="Creating…", text_color=C["dim"])
        self._create_btn.configure(state="disabled")

        def _run():
            mgr = AliasManager(on_log=lambda m: None)
            info = mgr.create(alias_name=name, model_id=model, proxy_port=port)
            self.app.after(0, lambda: self._on_create_done(info, name))
        threading.Thread(target=_run, daemon=True).start()

    def _on_create_done(self, info, name):
        self._create_btn.configure(state="normal")
        if info:
            self._create_status.configure(
                text=f"'{name}' created!", text_color=C["green"]
            )
        else:
            self._create_status.configure(text="Creation failed.", text_color=C["red"])
        self._refresh_list()

    def _do_remove(self, alias_name: str):
        from ...setup.alias_manager import AliasManager
        AliasManager().remove(alias_name)
        self._refresh_list()

    def _install_litellm(self):
        def _run():
            from ...setup.alias_manager import AliasManager
            mgr = AliasManager()
            ok = mgr.install_litellm()
            self.app.after(0, lambda: self._litellm_status.configure(
                text="  litellm installed" if ok else "  install failed"
            ))
        threading.Thread(target=_run, daemon=True).start()

    def _get_local_model_ids(self):
        """Pull Ollama model list if Ollama is available."""
        if not shutil.which("ollama"):
            return []
        try:
            import subprocess
            r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                lines = r.stdout.strip().splitlines()[1:]  # skip header
                return [l.split()[0] for l in lines if l.strip()]
        except Exception:
            pass
        return []
