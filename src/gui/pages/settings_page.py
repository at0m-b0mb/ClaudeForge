"""
Settings page — API key, default model, Ollama, CLAUDE.md, report export.
"""

import json
import os
import shutil
import threading
import customtkinter as ctk

from ..app import (
    BasePage, C,
    card_frame, label, dim_label, sub_label,
    accent_button, ghost_button, chip, status_dot, hairline,
)


class SettingsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False
        self._db = None
        self._db_loading = False

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        self._refresh_status()

    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Settings",
            "API key, default model, Ollama, CLAUDE.md templates, and report export.",
        )

        # ── Section: API Key ──────────────────────────────────────────
        api_card = self._section_card(
            "🔑", "API Key",
            "Store your Anthropic API key in your shell profile.")

        api_inner = ctk.CTkFrame(api_card, fg_color="transparent")
        api_inner.pack(fill="x", padx=18, pady=(0, 16))

        row = ctk.CTkFrame(api_inner, fg_color="transparent")
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        self._api_entry = ctk.CTkEntry(
            row,
            placeholder_text="sk-ant-api03-...",
            show="•",
            font=ctk.CTkFont(size=13),
            fg_color=C["bg_alt"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["sub"],
            height=40, corner_radius=10,
        )
        self._api_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._api_show_btn = ghost_button(
            row, "Show", self._toggle_api_visibility,
            width=70, color=C["dim"],
        )
        self._api_show_btn.configure(height=40)
        self._api_show_btn.grid(row=0, column=1, padx=(0, 8))

        save_btn = accent_button(row, "Save key", self._save_api_key,
                                 width=110, height=40)
        save_btn.grid(row=0, column=2)

        self._api_status = sub_label(api_inner, "", size=11)
        self._api_status.pack(anchor="w", pady=(8, 0))

        existing_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if existing_key:
            self._api_entry.insert(0, existing_key)

        # ── Section: Default model ────────────────────────────────────
        model_card = self._section_card(
            "🤖", "Default model",
            "Which Claude model is used by default in ~/.claude/settings.json.")

        m_inner = ctk.CTkFrame(model_card, fg_color="transparent")
        m_inner.pack(fill="x", padx=18, pady=(0, 16))

        sel_row = ctk.CTkFrame(m_inner, fg_color="transparent")
        sel_row.pack(fill="x")
        sel_row.columnconfigure(0, weight=1)

        self._model_var = ctk.StringVar(value="claude-sonnet-4-6")
        self._model_combo = ctk.CTkComboBox(
            sel_row, variable=self._model_var,
            values=["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-6"],
            fg_color=C["bg_alt"], border_color=C["border"],
            button_color=C["accent"], button_hover_color=C["accent_dk"],
            dropdown_fg_color=C["card"], font=ctk.CTkFont(size=13),
            height=40, corner_radius=10,
        )
        self._model_combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._refresh_models_btn = ghost_button(
            sel_row, "⟳  Refresh", self._refresh_models,
            width=120, color=C["accent"],
        )
        self._refresh_models_btn.configure(height=40)
        self._refresh_models_btn.grid(row=0, column=1, padx=(0, 8))

        accent_button(sel_row, "Apply", self._write_settings,
                      width=90, height=40).grid(row=0, column=2)

        self._model_status = sub_label(m_inner, "Using cached / static model list.",
                                       size=11)
        self._model_status.pack(anchor="w", pady=(8, 0))

        # ── Section: Ollama ───────────────────────────────────────────
        ollama_card = self._section_card(
            "🦙", "Ollama (Local Models)",
            "Install Ollama and pull models to run AI offline.")

        o_inner = ctk.CTkFrame(ollama_card, fg_color="transparent")
        o_inner.pack(fill="x", padx=18, pady=(0, 16))

        self._ollama_status_row = ctk.CTkFrame(o_inner, fg_color="transparent")
        self._ollama_status_row.pack(anchor="w", pady=(0, 10))

        self._install_ollama_btn = accent_button(
            o_inner, "Install Ollama", self._install_ollama, width=170,
        )
        self._install_ollama_btn.pack(anchor="w", pady=(0, 12))

        hairline(o_inner, pad_y=(0, 10))

        pull_row = ctk.CTkFrame(o_inner, fg_color="transparent")
        pull_row.pack(fill="x")
        pull_row.columnconfigure(0, weight=1)

        self._pull_entry = ctk.CTkEntry(
            pull_row,
            placeholder_text="e.g. qwen2.5-coder:7b",
            font=ctk.CTkFont(size=13),
            fg_color=C["bg_alt"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["sub"],
            height=38, corner_radius=10,
        )
        self._pull_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        accent_button(pull_row, "Pull model", self._pull_model,
                      width=130, height=38).grid(row=0, column=1)

        self._pull_log = ctk.CTkTextbox(
            o_inner, height=110,
            font=ctk.CTkFont(size=11, family="Menlo"),
            fg_color=C["bg"], border_color=C["border"], border_width=1,
            text_color=C["dim"], corner_radius=8, state="disabled",
        )
        self._pull_log.pack(fill="x", pady=(10, 0))

        # ── Section: CLAUDE.md ────────────────────────────────────────
        md_card = self._section_card(
            "📝", "CLAUDE.md Template",
            "Create a project-level CLAUDE.md to guide Claude in any directory.")

        md_inner = ctk.CTkFrame(md_card, fg_color="transparent")
        md_inner.pack(fill="x", padx=18, pady=(0, 16))

        dir_row = ctk.CTkFrame(md_inner, fg_color="transparent")
        dir_row.pack(fill="x")
        dir_row.columnconfigure(0, weight=1)

        self._md_dir_entry = ctk.CTkEntry(
            dir_row,
            placeholder_text=os.getcwd(),
            font=ctk.CTkFont(size=13),
            fg_color=C["bg_alt"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["sub"],
            height=38, corner_radius=10,
        )
        self._md_dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        accent_button(dir_row, "Create CLAUDE.md",
                      self._create_claude_md,
                      width=170, height=38).grid(row=0, column=1)

        self._md_status = sub_label(md_inner,
            "Leave blank to use the current working directory.", size=11)
        self._md_status.pack(anchor="w", pady=(8, 0))

        # ── Section: Export Report ────────────────────────────────────
        export_card = self._section_card(
            "📤", "Export report",
            "Save hardware and benchmark data to a JSON file.")

        e_inner = ctk.CTkFrame(export_card, fg_color="transparent")
        e_inner.pack(fill="x", padx=18, pady=(0, 16))

        exp_row = ctk.CTkFrame(e_inner, fg_color="transparent")
        exp_row.pack(fill="x")
        exp_row.columnconfigure(0, weight=1)

        self._export_entry = ctk.CTkEntry(
            exp_row,
            placeholder_text="~/claudeforge_report.json",
            font=ctk.CTkFont(size=13),
            fg_color=C["bg_alt"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["sub"],
            height=38, corner_radius=10,
        )
        self._export_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        accent_button(exp_row, "Export", self._export_report,
                      width=110, height=38).grid(row=0, column=1)

        self._export_status = sub_label(e_inner,
            "Hardware and benchmark must be run first.", size=11)
        self._export_status.pack(anchor="w", pady=(8, 0))

        ctk.CTkFrame(self, fg_color="transparent", height=32).pack()

    # ------------------------------------------------------------------

    def _section_card(self, icon, title, subtitle=""):
        """Builds a card with header (icon + title + subtitle) and returns it."""
        card = card_frame(self)
        card.pack(fill="x", padx=32, pady=(0, 16))

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 4))
        ctk.CTkLabel(head, text=icon, font=ctk.CTkFont(size=18),
                     text_color=C["accent"]).pack(side="left")
        label(head, "  " + title, size=14, weight="bold").pack(side="left")

        if subtitle:
            sub_label(card, subtitle, size=11).pack(
                anchor="w", padx=18, pady=(0, 12))
        return card

    def _log_pull(self, msg: str):
        self._pull_log.configure(state="normal")
        self._pull_log.insert("end", msg + "\n")
        self._pull_log.see("end")
        self._pull_log.configure(state="disabled")

    # ------------------------------------------------------------------

    def _refresh_status(self):
        is_installed = shutil.which("ollama") is not None
        for w in self._ollama_status_row.winfo_children():
            w.destroy()
        status_dot(
            self._ollama_status_row, is_installed,
            "Ollama is installed" if is_installed else "Ollama not found",
        ).pack(side="left")

        if is_installed:
            self._install_ollama_btn.configure(
                state="disabled", text="Ollama installed ✓",
                fg_color=C["card_hi"], text_color=C["green"],
            )
        else:
            self._install_ollama_btn.configure(
                state="normal", text="Install Ollama",
                fg_color=C["accent"], text_color=C["ink"],
            )

    # ------------------------------------------------------------------
    # Handlers

    def _toggle_api_visibility(self):
        current = self._api_entry.cget("show")
        if current == "•":
            self._api_entry.configure(show="")
            self._api_show_btn.configure(text="Hide")
        else:
            self._api_entry.configure(show="•")
            self._api_show_btn.configure(text="Show")

    def _save_api_key(self):
        from ...setup.configurator import Configurator
        key = self._api_entry.get().strip()
        if not key:
            self._api_status.configure(text="Enter an API key first.",
                                       text_color=C["yellow"])
            return

        logs = []
        cfg = Configurator(on_log=lambda m: logs.append(m))
        ok = cfg.save_api_key(key)
        msg = "  ".join(logs) if logs else ("Saved." if ok else "Failed to save.")
        self._api_status.configure(
            text=msg, text_color=C["green"] if ok else C["red"])

    def _refresh_models(self):
        if self._db_loading:
            return
        self._db_loading = True
        self._refresh_models_btn.configure(state="disabled", text="Fetching…")
        self._model_status.configure(text="Fetching live models…",
                                     text_color=C["yellow"])

        api_key = (self._api_entry.get().strip()
                   or os.environ.get("ANTHROPIC_API_KEY", ""))

        def _run():
            from ...models.database import ModelDatabase
            db = ModelDatabase()
            result = db.refresh(api_key=api_key or None, force=True)
            self._db = db

            def _done():
                self._db_loading = False
                self._refresh_models_btn.configure(state="normal",
                                                   text="⟳  Refresh")
                api_ids = [m.id for m in db.claude_api_models]
                if api_ids:
                    self._model_combo.configure(values=api_ids)
                    if self._model_var.get() not in api_ids:
                        self._model_var.set(api_ids[0])
                errors = result.errors
                if errors:
                    self._model_status.configure(
                        text=f"Partial fetch — {len(api_ids)} Claude models. "
                             f"Errors: {errors[0]}",
                        text_color=C["yellow"])
                else:
                    self._model_status.configure(
                        text=f"Live: {len(api_ids)} Claude models, "
                             f"{len(db.local_models)} local.  "
                             f"Source: {result.source}",
                        text_color=C["green"])

            self.app.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _write_settings(self):
        from ...setup.configurator import Configurator
        model_id = self._model_var.get().strip()
        logs = []
        cfg = Configurator(on_log=lambda m: logs.append(m))
        ok = cfg.write_settings(model_id=model_id)
        msg = "  ".join(logs) if logs else (
            "Settings saved." if ok else "Failed to save settings.")
        self._model_status.configure(
            text=msg, text_color=C["green"] if ok else C["red"])

    def _install_ollama(self):
        self._install_ollama_btn.configure(state="disabled", text="Installing…")
        self._log_pull("Starting Ollama install…")

        def _run():
            from ...setup.configurator import Configurator
            cfg = Configurator(
                on_log=lambda m: self.app.after(
                    0, lambda m=m: self._log_pull(m)))
            ok = cfg.install_ollama()
            self.app.after(0, lambda: self._refresh_status())
            if ok:
                self.app.after(0, lambda: self._log_pull("✓ Ollama installed."))
            else:
                self.app.after(0, lambda: self._log_pull(
                    "Install failed or requires manual steps."))

        threading.Thread(target=_run, daemon=True).start()

    def _pull_model(self):
        model_id = self._pull_entry.get().strip()
        if not model_id:
            self._log_pull("Enter a model ID first (e.g. qwen2.5-coder:7b).")
            return
        self._log_pull(f"Pulling {model_id}…")

        def _run():
            from ...setup.configurator import Configurator
            cfg = Configurator(
                on_log=lambda m: self.app.after(
                    0, lambda m=m: self._log_pull(m)))
            ok = cfg.pull_ollama_model(model_id)
            self.app.after(0, lambda: self._log_pull(
                f"✓ {model_id} ready." if ok else f"✗ Failed to pull {model_id}."))

        threading.Thread(target=_run, daemon=True).start()

    def _create_claude_md(self):
        from ...setup.configurator import Configurator
        raw_dir = self._md_dir_entry.get().strip()
        target = os.path.expanduser(raw_dir) if raw_dir else os.getcwd()
        logs = []
        cfg = Configurator(on_log=lambda m: logs.append(m))
        ok = cfg.create_claude_md(project_dir=target)
        msg = "  ".join(logs) if logs else (
            "Created." if ok else "CLAUDE.md already exists.")
        self._md_status.configure(
            text=msg, text_color=C["green"] if ok else C["yellow"])

    def _export_report(self):
        if not self.app.system_info and not self.app.bench_result:
            self._export_status.configure(
                text="Run hardware detection and/or benchmark first.",
                text_color=C["red"])
            return
        raw_path = self._export_entry.get().strip()
        if not raw_path:
            raw_path = os.path.expanduser("~/claudeforge_report.json")
        else:
            raw_path = os.path.expanduser(raw_path)
        report: dict = {}
        if self.app.system_info:
            report["hardware"] = self.app.system_info.to_dict()
        if self.app.bench_result:
            r = self.app.bench_result
            report["benchmark"] = {
                "cpu_single_score":      r.cpu_single_score,
                "cpu_multi_score":       r.cpu_multi_score,
                "memory_bandwidth_gbps": r.memory_bandwidth_gbps,
                "overall_score":         r.overall_score,
                "tier":                  r.tier,
            }
        try:
            parent = os.path.dirname(raw_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(raw_path, "w") as f:
                json.dump(report, f, indent=2)
            self._export_status.configure(
                text=f"✓ Report saved to {raw_path}", text_color=C["green"])
        except Exception as exc:
            self._export_status.configure(text=f"Error: {exc}",
                                          text_color=C["red"])
