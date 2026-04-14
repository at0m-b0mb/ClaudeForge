"""
Settings page — API key, default model, Ollama management, CLAUDE.md, report export.
Exposes all features previously only available in the CLI.
"""

import json
import os
import threading

import customtkinter as ctk
from ..app import BasePage, C, card_frame, label, dim_label, accent_button, badge, status_dot


class SettingsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False
        self._db = None         # ModelDatabase, loaded lazily
        self._db_loading = False

    def on_show(self):
        if not self._built:
            self._build()
            self._built = True
        self._refresh_status()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        self.page_header(
            "Settings",
            "API key, default model, Ollama, CLAUDE.md templates, and report export.",
        )

        # ── Section: API Key ──────────────────────────────────────────
        self._section("API Key", "Store your Anthropic API key in your shell profile.")

        api_card = card_frame(self)
        api_card.pack(fill="x", padx=28, pady=(0, 20))

        api_inner = ctk.CTkFrame(api_card, fg_color="transparent")
        api_inner.pack(fill="x", padx=16, pady=14)

        row = ctk.CTkFrame(api_inner, fg_color="transparent")
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        self._api_entry = ctk.CTkEntry(
            row,
            placeholder_text="sk-ant-api03-...",
            show="•",
            font=ctk.CTkFont(size=13),
            fg_color=C["bg"],
            border_color=C["border"],
            height=38,
        )
        self._api_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._api_show_btn = ctk.CTkButton(
            row, text="Show", width=60, height=38,
            fg_color=C["card"], hover_color=C["border"],
            text_color=C["dim"], font=ctk.CTkFont(size=12),
            corner_radius=8,
            command=self._toggle_api_visibility,
        )
        self._api_show_btn.grid(row=0, column=1, padx=(0, 8))

        accent_button(row, "Save Key", self._save_api_key, width=100, height=38).grid(
            row=0, column=2
        )

        self._api_status = dim_label(api_inner, "", size=12)
        self._api_status.pack(anchor="w", pady=(6, 0))

        # Pre-fill from environment if present
        existing_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if existing_key:
            self._api_entry.insert(0, existing_key)

        # ── Section: Default Model ────────────────────────────────────
        self._section("Default Model", "Set which Claude model is used by default in ~/.claude/settings.json.")

        model_card = card_frame(self)
        model_card.pack(fill="x", padx=28, pady=(0, 20))

        model_inner = ctk.CTkFrame(model_card, fg_color="transparent")
        model_inner.pack(fill="x", padx=16, pady=14)

        sel_row = ctk.CTkFrame(model_inner, fg_color="transparent")
        sel_row.pack(fill="x")

        self._model_var = ctk.StringVar(value="claude-sonnet-4-6")
        self._model_combo = ctk.CTkComboBox(
            sel_row,
            variable=self._model_var,
            values=["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-6"],
            width=340,
            font=ctk.CTkFont(size=13),
            fg_color=C["bg"],
            border_color=C["border"],
            button_color=C["accent"],
            dropdown_fg_color=C["card"],
        )
        self._model_combo.pack(side="left", padx=(0, 8))

        self._refresh_models_btn = ctk.CTkButton(
            sel_row, text="⟳  Refresh", width=110, height=36,
            fg_color=C["card"], hover_color=C["border"],
            text_color=C["accent"], font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            command=self._refresh_models,
        )
        self._refresh_models_btn.pack(side="left", padx=(0, 8))

        accent_button(sel_row, "Apply", self._write_settings, width=90, height=36).pack(side="left")

        self._model_status = dim_label(model_inner, "Using cached / static model list.", size=12)
        self._model_status.pack(anchor="w", pady=(6, 0))

        # ── Section: Ollama ───────────────────────────────────────────
        self._section("Ollama (Local Models)", "Install Ollama and pull models to run AI offline.")

        ollama_card = card_frame(self)
        ollama_card.pack(fill="x", padx=28, pady=(0, 20))

        ollama_inner = ctk.CTkFrame(ollama_card, fg_color="transparent")
        ollama_inner.pack(fill="x", padx=16, pady=14)

        self._ollama_status_row = ctk.CTkFrame(ollama_inner, fg_color="transparent")
        self._ollama_status_row.pack(anchor="w", pady=(0, 8))
        self._ollama_dot = status_dot(self._ollama_status_row, False, "Checking…")
        self._ollama_dot.pack(side="left")

        self._install_ollama_btn = accent_button(
            ollama_inner, "Install Ollama", self._install_ollama, width=150
        )
        self._install_ollama_btn.pack(anchor="w", pady=(0, 12))

        ctk.CTkFrame(ollama_inner, height=1, fg_color=C["border"]).pack(fill="x", pady=(0, 12))

        pull_row = ctk.CTkFrame(ollama_inner, fg_color="transparent")
        pull_row.pack(fill="x")
        pull_row.columnconfigure(0, weight=1)

        self._pull_entry = ctk.CTkEntry(
            pull_row,
            placeholder_text="e.g. qwen2.5-coder:7b",
            font=ctk.CTkFont(size=13),
            fg_color=C["bg"],
            border_color=C["border"],
            height=36,
        )
        self._pull_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        accent_button(pull_row, "Pull Model", self._pull_model, width=120, height=36).grid(
            row=0, column=1
        )

        self._pull_log = ctk.CTkTextbox(
            ollama_inner,
            height=80,
            font=ctk.CTkFont(size=11, family="Courier"),
            fg_color=C["bg"],
            border_color=C["border"],
            border_width=1,
            text_color=C["dim"],
            state="disabled",
        )
        self._pull_log.pack(fill="x", pady=(8, 0))

        # ── Section: CLAUDE.md ────────────────────────────────────────
        self._section("CLAUDE.md Template", "Create a project-level CLAUDE.md to guide Claude in any directory.")

        md_card = card_frame(self)
        md_card.pack(fill="x", padx=28, pady=(0, 20))

        md_inner = ctk.CTkFrame(md_card, fg_color="transparent")
        md_inner.pack(fill="x", padx=16, pady=14)

        dir_row = ctk.CTkFrame(md_inner, fg_color="transparent")
        dir_row.pack(fill="x")
        dir_row.columnconfigure(0, weight=1)

        self._md_dir_entry = ctk.CTkEntry(
            dir_row,
            placeholder_text=os.getcwd(),
            font=ctk.CTkFont(size=13),
            fg_color=C["bg"],
            border_color=C["border"],
            height=36,
        )
        self._md_dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        accent_button(dir_row, "Create CLAUDE.md", self._create_claude_md, width=160, height=36).grid(
            row=0, column=1
        )

        self._md_status = dim_label(md_inner, "Leave blank to use current working directory.", size=12)
        self._md_status.pack(anchor="w", pady=(6, 0))

        # ── Section: Export Report ────────────────────────────────────
        self._section("Export Report", "Save hardware and benchmark data to a JSON file.")

        export_card = card_frame(self)
        export_card.pack(fill="x", padx=28, pady=(0, 20))

        export_inner = ctk.CTkFrame(export_card, fg_color="transparent")
        export_inner.pack(fill="x", padx=16, pady=14)

        exp_row = ctk.CTkFrame(export_inner, fg_color="transparent")
        exp_row.pack(fill="x")
        exp_row.columnconfigure(0, weight=1)

        self._export_entry = ctk.CTkEntry(
            exp_row,
            placeholder_text="~/claudeforge_report.json",
            font=ctk.CTkFont(size=13),
            fg_color=C["bg"],
            border_color=C["border"],
            height=36,
        )
        self._export_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        accent_button(exp_row, "Export", self._export_report, width=100, height=36).grid(
            row=0, column=1
        )

        self._export_status = dim_label(export_inner, "Hardware and benchmark must be run first.", size=12)
        self._export_status.pack(anchor="w", pady=(6, 0))

        # bottom padding
        ctk.CTkFrame(self, fg_color="transparent", height=32).pack()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _section(self, title: str, subtitle: str = ""):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=28, pady=(16, 4))
        label(f, title, size=16, weight="bold").pack(anchor="w")
        if subtitle:
            dim_label(f, subtitle, size=12).pack(anchor="w", pady=(2, 0))

    def _log_pull(self, msg: str):
        self._pull_log.configure(state="normal")
        self._pull_log.insert("end", msg + "\n")
        self._pull_log.see("end")
        self._pull_log.configure(state="disabled")

    # ------------------------------------------------------------------
    # Status refresh
    # ------------------------------------------------------------------

    def _refresh_status(self):
        import shutil
        is_installed = shutil.which("ollama") is not None

        for w in self._ollama_status_row.winfo_children():
            w.destroy()
        status_dot(
            self._ollama_status_row,
            is_installed,
            "Ollama is installed" if is_installed else "Ollama not found",
        ).pack(side="left")

        self._install_ollama_btn.configure(
            state="disabled" if is_installed else "normal",
            text="Ollama installed ✓" if is_installed else "Install Ollama",
            fg_color=C["card"] if is_installed else C["accent"],
            text_color=C["dim"] if is_installed else "#0d1117",
        )

    # ------------------------------------------------------------------
    # API Key
    # ------------------------------------------------------------------

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
            self._api_status.configure(text="Enter an API key first.", text_color=C["yellow"])
            return

        logs = []
        cfg = Configurator(on_log=lambda m: logs.append(m))
        ok = cfg.save_api_key(key)
        msg = "  ".join(logs) if logs else ("Saved." if ok else "Failed to save.")
        color = C["green"] if ok else C["red"]
        self._api_status.configure(text=msg, text_color=color)

    # ------------------------------------------------------------------
    # Models refresh
    # ------------------------------------------------------------------

    def _refresh_models(self):
        if self._db_loading:
            return
        self._db_loading = True
        self._refresh_models_btn.configure(state="disabled", text="Fetching…")
        self._model_status.configure(text="Fetching live models…", text_color=C["yellow"])

        api_key = self._api_entry.get().strip() or os.environ.get("ANTHROPIC_API_KEY", "")

        def _run():
            from ...models.database import ModelDatabase
            db = ModelDatabase()
            result = db.refresh(api_key=api_key or None, force=True)
            self._db = db

            def _done():
                self._db_loading = False
                self._refresh_models_btn.configure(state="normal", text="⟳  Refresh")
                api_ids = [m.id for m in db.claude_api_models]
                if api_ids:
                    self._model_combo.configure(values=api_ids)
                    if self._model_var.get() not in api_ids:
                        self._model_var.set(api_ids[0])

                errors = result.errors
                if errors:
                    self._model_status.configure(
                        text=f"Partial fetch — {len(api_ids)} Claude models, {len(db.local_models)} local. Errors: {errors[0]}",
                        text_color=C["yellow"],
                    )
                else:
                    self._model_status.configure(
                        text=f"Live data: {len(api_ids)} Claude models, {len(db.local_models)} local models.  Source: {result.source}",
                        text_color=C["green"],
                    )

            self.app.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # Default model
    # ------------------------------------------------------------------

    def _write_settings(self):
        from ...setup.configurator import Configurator
        model_id = self._model_var.get().strip()
        logs = []
        cfg = Configurator(on_log=lambda m: logs.append(m))
        ok = cfg.write_settings(model_id=model_id)
        msg = "  ".join(logs) if logs else ("Settings saved." if ok else "Failed to save settings.")
        color = C["green"] if ok else C["red"]
        self._model_status.configure(text=msg, text_color=color)

    # ------------------------------------------------------------------
    # Ollama
    # ------------------------------------------------------------------

    def _install_ollama(self):
        self._install_ollama_btn.configure(state="disabled", text="Installing…")
        self._log_pull("Starting Ollama install…")

        def _run():
            from ...setup.configurator import Configurator
            cfg = Configurator(on_log=lambda m: self.app.after(0, lambda m=m: self._log_pull(m)))
            ok = cfg.install_ollama()
            self.app.after(0, lambda: self._refresh_status())
            if ok:
                self.app.after(0, lambda: self._log_pull("Ollama installed successfully."))
            else:
                self.app.after(0, lambda: self._log_pull("Install failed or requires manual steps."))

        threading.Thread(target=_run, daemon=True).start()

    def _pull_model(self):
        model_id = self._pull_entry.get().strip()
        if not model_id:
            self._log_pull("Enter a model ID first (e.g. qwen2.5-coder:7b).")
            return

        self._log_pull(f"Pulling {model_id}…")

        def _run():
            from ...setup.configurator import Configurator
            cfg = Configurator(on_log=lambda m: self.app.after(0, lambda m=m: self._log_pull(m)))
            ok = cfg.pull_ollama_model(model_id)
            self.app.after(
                0,
                lambda: self._log_pull(
                    f"✓ {model_id} ready." if ok else f"✗ Failed to pull {model_id}."
                ),
            )

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # CLAUDE.md
    # ------------------------------------------------------------------

    def _create_claude_md(self):
        from ...setup.configurator import Configurator
        raw_dir = self._md_dir_entry.get().strip()
        target = os.path.expanduser(raw_dir) if raw_dir else os.getcwd()
        logs = []
        cfg = Configurator(on_log=lambda m: logs.append(m))
        ok = cfg.create_claude_md(project_dir=target)
        msg = "  ".join(logs) if logs else ("Created." if ok else "CLAUDE.md already exists.")
        color = C["green"] if ok else C["yellow"]
        self._md_status.configure(text=msg, text_color=color)

    # ------------------------------------------------------------------
    # Report export
    # ------------------------------------------------------------------

    def _export_report(self):
        if not self.app.system_info and not self.app.bench_result:
            self._export_status.configure(
                text="Run Hardware Detection and/or Benchmark first.",
                text_color=C["red"],
            )
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
                "cpu_single_score":       r.cpu_single_score,
                "cpu_multi_score":        r.cpu_multi_score,
                "memory_bandwidth_gbps":  r.memory_bandwidth_gbps,
                "overall_score":          r.overall_score,
                "tier":                   r.tier,
            }

        try:
            os.makedirs(os.path.dirname(raw_path), exist_ok=True)
            with open(raw_path, "w") as f:
                json.dump(report, f, indent=2)
            self._export_status.configure(
                text=f"Report saved to {raw_path}", text_color=C["green"]
            )
        except Exception as exc:
            self._export_status.configure(text=f"Error: {exc}", text_color=C["red"])
