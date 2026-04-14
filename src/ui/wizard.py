"""
Interactive setup wizard.
Guides the user through hardware detection, benchmarking, model recommendation,
and full Claude Code installation.
"""

import os
import sys
import platform
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..hardware.detector import HardwareDetector
from ..hardware.benchmark import Benchmarker
from ..models.recommender import ModelRecommender
from ..setup.prerequisites import PrerequisiteChecker
from ..setup.node_installer import NodeInstaller
from ..setup.claude_installer import ClaudeCodeInstaller
from ..setup.configurator import Configurator
from ..setup.alias_manager import AliasManager, DEFAULT_ALIAS
from .banner import print_banner, print_section, print_success, print_warning, print_error, print_info
from .components import (
    hardware_table, benchmark_table, recommendation_panel,
    prerequisites_table, alias_table, make_progress,
)


class SetupWizard:
    """
    Full interactive setup wizard.
    """

    def __init__(self, console: Console = None, skip_benchmark: bool = False, quiet: bool = False):
        self.console = console or Console()
        self.skip_benchmark = skip_benchmark
        self.quiet = quiet

        self.system_info = None
        self.bench_result = None
        self.recommendation = None
        self._alias_created = None   # (alias_name, model_id) if alias was set up

    # ------------------------------------------------------------------
    # Public entry-points
    # ------------------------------------------------------------------

    def run_full(self):
        """Run the complete wizard: detect → benchmark → recommend → install → alias."""
        print_banner(self.console)
        self.run_hardware_detection()
        if not self.skip_benchmark:
            self.run_benchmark()
        self.run_recommendation()
        self.run_prerequisites_check()
        self.run_installation()
        self.run_configuration()
        self.run_alias_setup()
        self.print_summary()

    def run_hardware_only(self):
        """Just detect hardware and show results."""
        print_banner(self.console)
        self.run_hardware_detection()
        if not self.skip_benchmark:
            self.run_benchmark()
        self.run_recommendation()

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def run_hardware_detection(self):
        print_section(self.console, "Step 1 — Hardware Detection")

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=self.console, transient=True) as prog:
            task = prog.add_task("Scanning hardware...", total=None)
            detector = HardwareDetector()
            self.system_info = detector.detect()

        self.console.print(hardware_table(self.system_info))
        self.console.print()

    def run_benchmark(self):
        print_section(self.console, "Step 2 — Performance Benchmark")
        self.console.print("[dim]Running CPU and memory benchmarks (~8 seconds)...[/dim]")
        self.console.print()

        steps_done = []
        def on_progress(msg):
            steps_done.append(msg)
            if not self.quiet:
                print_info(self.console, msg)

        benchmarker = Benchmarker(system_info=self.system_info)
        self.bench_result = benchmarker.run(on_progress=on_progress)

        self.console.print()
        self.console.print(benchmark_table(self.bench_result))
        self.console.print()

    def run_recommendation(self):
        print_section(self.console, "Step 3 — Model Recommendation")

        tier   = self.bench_result.tier   if self.bench_result else "mid"
        score  = self.bench_result.overall_score if self.bench_result else 50.0
        ram_gb = self.system_info.ram_total_gb if self.system_info else 8.0
        vram_mb= max((g.vram_mb for g in self.system_info.gpus), default=0) if self.system_info else 0
        apple  = self.system_info.cpu.is_apple_silicon if self.system_info else False

        recommender = ModelRecommender()
        self.recommendation = recommender.recommend(
            benchmark_tier=tier,
            overall_score=score,
            ram_gb=ram_gb,
            vram_mb=vram_mb,
            is_apple_silicon=apple,
        )

        self.console.print(recommendation_panel(self.recommendation))
        self.console.print()

    def run_prerequisites_check(self):
        print_section(self.console, "Step 4 — Prerequisites")

        checker = PrerequisiteChecker()
        statuses = checker.check_all()
        self.console.print(prerequisites_table(statuses))
        self.console.print()

        missing = checker.missing_required(statuses)
        if missing:
            print_warning(self.console, f"{len(missing)} required prerequisite(s) missing.")
            for s in missing:
                self.console.print(f"  [bold red]{s.name}[/bold red]: {s.install_hint}")
            self.console.print()

            if Confirm.ask("[bold]Attempt automatic installation of missing prerequisites?[/bold]"):
                for s in missing:
                    if s.name.startswith("Node"):
                        installer = NodeInstaller(on_log=lambda m: print_info(self.console, m))
                        if installer.install():
                            print_success(self.console, "Node.js installed.")
                        else:
                            print_error(self.console, "Node.js installation failed. Please install manually.")
            else:
                self.console.print("[dim]Skipping automatic installation.[/dim]")
        else:
            print_success(self.console, "All required prerequisites are satisfied.")

        self.console.print()

    def run_installation(self):
        print_section(self.console, "Step 5 — Install Claude Code")

        installer = ClaudeCodeInstaller(on_log=lambda m: print_info(self.console, m))
        if installer.is_installed():
            ver = installer.installed_version()
            print_success(self.console, f"Claude Code already installed: {ver}")
            if Confirm.ask("Update to the latest version?", default=False):
                installer.update()
        else:
            if Confirm.ask("[bold]Install Claude Code CLI now?[/bold]", default=True):
                ok = installer.install()
                if ok:
                    installer.verify()
                    print_success(self.console, "Claude Code is ready.")
                else:
                    print_error(self.console, "Installation failed. Check the logs above.")
            else:
                self.console.print("[dim]Skipping Claude Code installation.[/dim]")

        self.console.print()

    def run_configuration(self):
        print_section(self.console, "Step 6 — Configuration")

        configurator = Configurator(on_log=lambda m: print_info(self.console, m))

        # API Key
        existing_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if existing_key:
            print_success(self.console, "ANTHROPIC_API_KEY is already set in the environment.")
        else:
            self.console.print(
                "You need an Anthropic API key to use Claude Code.\n"
                "Get one at: [bold cyan]https://console.anthropic.com/[/bold cyan]"
            )
            api_key = Prompt.ask(
                "Enter your Anthropic API key (or press Enter to skip)",
                password=True,
                default="",
            )
            if api_key:
                configurator.save_api_key(api_key)
                print_success(self.console, "API key saved.")
            else:
                print_warning(self.console, "Skipped. Set ANTHROPIC_API_KEY manually before using Claude Code.")

        self.console.print()

        # Model preference
        if self.recommendation:
            default_model = self.recommendation.primary_api_model.id
            self.console.print(
                f"Recommended model: [bold green]{self.recommendation.primary_api_model.display_name}[/bold green]"
            )
            if Confirm.ask(f"Set {default_model!r} as default model in settings?", default=True):
                configurator.write_settings(model_id=default_model)
                print_success(self.console, f"Default model set to {default_model}.")
        else:
            configurator.write_settings()

        self.console.print()

        # CLAUDE.md
        if Confirm.ask("Create a CLAUDE.md template in the current directory?", default=True):
            configurator.create_claude_md()
            print_success(self.console, "CLAUDE.md created.")

        self.console.print()

        # Ollama
        if self.recommendation and self.recommendation.local_models:
            self.console.print(
                f"[bold]Your hardware can run {len(self.recommendation.local_models)} local model(s) via Ollama.[/bold]"
            )
            if Confirm.ask("Install Ollama for local model support?", default=False):
                if configurator.is_ollama_installed():
                    print_success(self.console, "Ollama is already installed.")
                else:
                    configurator.install_ollama()

                if configurator.is_ollama_installed() and self.recommendation.local_models:
                    top_model = self.recommendation.local_models[0]
                    if Confirm.ask(f"Pull the top recommended model ({top_model.display_name})?", default=False):
                        configurator.pull_ollama_model(top_model.id)

        self.console.print()

    def run_alias_setup(self):
        print_section(self.console, "Step 7 — Local Alias Setup")

        self.console.print(
            "This creates a separate command (e.g. [bold cyan]claude-local[/bold cyan]) "
            "that runs Claude Code pointed at a [bold]local Ollama model[/bold] instead of the cloud.\n"
            "Your existing [bold cyan]claude[/bold cyan] command stays untouched.\n"
        )

        if not Confirm.ask("Set up a local alias?", default=False):
            self.console.print("[dim]Skipping local alias setup.[/dim]")
            self.console.print()
            return

        mgr = AliasManager(on_log=lambda m: print_info(self.console, m))

        # ── Choose alias name ─────────────────────────────────────────
        alias_name = Prompt.ask(
            "Alias name",
            default=DEFAULT_ALIAS,
        ).strip() or DEFAULT_ALIAS

        # ── Choose local model ────────────────────────────────────────
        local_models = []
        if self.recommendation:
            local_models = self.recommendation.local_models

        if local_models:
            self.console.print("\nAvailable local models for your hardware:")
            for i, m in enumerate(local_models, 1):
                vram = f"{m.vram_required_mb // 1024} GB VRAM" if m.vram_required_mb else "CPU"
                self.console.print(
                    f"  [bold cyan]{i}[/bold cyan]. {m.display_name}"
                    f"  [{vram}]  {m.use_case}"
                )
            self.console.print()
            choice = Prompt.ask(
                "Pick a model (number or Ollama model ID)",
                default="1",
            ).strip()
            if choice.isdigit():
                idx = int(choice) - 1
                model_id = local_models[idx].id if 0 <= idx < len(local_models) else local_models[0].id
            else:
                model_id = choice or local_models[0].id
        else:
            model_id = Prompt.ask(
                "Enter the Ollama model ID to use",
                default="qwen2.5-coder:7b",
            ).strip() or "qwen2.5-coder:7b"

        # ── litellm check ─────────────────────────────────────────────
        self.console.print()
        if not mgr.check_litellm():
            print_warning(
                self.console,
                "litellm is required to proxy Claude Code to Ollama.",
            )
            if Confirm.ask("Install litellm[proxy] via pip now?", default=True):
                ok = mgr.install_litellm()
                if not ok:
                    print_error(self.console, "litellm install failed. You can retry later: pip install litellm[proxy]")
                    self.console.print("[dim]Alias will still be created; install litellm before using it.[/dim]")
            else:
                self.console.print("[dim]Skipping. Install litellm later: pip install litellm[proxy][/dim]")
        else:
            print_success(self.console, "litellm is already installed.")

        # ── Create alias ──────────────────────────────────────────────
        self.console.print()
        info = mgr.create(alias_name=alias_name, model_id=model_id)
        if info:
            print_success(self.console, f"Alias '{alias_name}' created successfully.")
            self.console.print(
                f"\n  [dim]Cloud:[/dim]  [bold cyan]claude[/bold cyan]          → Anthropic API\n"
                f"  [dim]Local:[/dim]  [bold cyan]{alias_name}[/bold cyan]  → Ollama / {model_id}"
            )
            self._alias_created = (alias_name, model_id)
        else:
            print_error(self.console, "Failed to create alias.")

        self.console.print()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def print_summary(self):
        print_section(self.console, "Setup Complete!", style="bold green")

        self.console.print("[bold green]You're all set! Here's what to do next:[/bold green]")
        self.console.print()
        self.console.print("  1. [bold]Reload your shell[/bold] (or open a new terminal) to pick up PATH changes.")
        self.console.print("  2. Run [bold cyan]claude[/bold cyan] in any project directory to start coding.")
        self.console.print("  3. Run [bold cyan]claude --help[/bold cyan] to explore available commands.")
        self.console.print()

        if self.recommendation:
            pm = self.recommendation.primary_api_model
            self.console.print(
                f"  Your default model is [bold green]{pm.display_name}[/bold green]. "
                "Change it anytime with [bold cyan]claude config set model <model-id>[/bold cyan]."
            )

        if self._alias_created:
            alias_name, model_id = self._alias_created
            self.console.print(
                f"  Use [bold cyan]{alias_name}[/bold cyan] to run Claude Code locally "
                f"(Ollama / {model_id})."
            )
            self.console.print(
                "  Make sure Ollama is running with:  [bold]ollama serve[/bold]"
            )
            self.console.print()

        self.console.print("[dim]Docs:   https://docs.anthropic.com/en/docs/claude-code[/dim]")
        self.console.print("[dim]Issues: https://github.com/anthropics/claude-code/issues[/dim]")
        self.console.print()
