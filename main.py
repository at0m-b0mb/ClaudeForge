#!/usr/bin/env python3
"""
ClaudeForge — Universal Claude Code Installer & Hardware Recommender
====================================================================

Usage:
    python main.py                              Full interactive setup wizard (CLI)
    python main.py --gui                        Launch the modern graphical interface
    python main.py --models                     Browse full model catalog (CLI table view)
    python main.py --detect                     Detect hardware only
    python main.py --benchmark                  Detect + benchmark, show recommendations
    python main.py --install                    Install Claude Code (skip hardware steps)
    python main.py --check                      Check prerequisites only
    python main.py --no-benchmark               Skip the benchmark during full setup
    python main.py --report FILE                Save hardware/benchmark data to JSON

    # Local alias — keep your existing `claude` pointing at the cloud,
    # and get a new command that routes Claude Code to a local Ollama model:
    python main.py --alias                      Create alias (interactive, default: claude-local)
    python main.py --alias --alias-name NAME    Use a custom alias name
    python main.py --alias --alias-model ID     Use a specific Ollama model ID
    python main.py --alias-list                 List all local aliases
    python main.py --alias-remove NAME          Delete a local alias

Run `python main.py --help` for the complete option list.
"""

import argparse
import json
import os
import sys

# Ensure the project root is on the path regardless of CWD
sys.path.insert(0, os.path.dirname(__file__))

# Guard: require Python 3.8+
if sys.version_info < (3, 8):
    print("ERROR: Python 3.8 or newer is required.")
    sys.exit(1)

# Guard: check for required third-party libraries
def _check_deps():
    missing = []
    for pkg in ("rich", "psutil"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print("Install them with:  pip install " + " ".join(missing))
        print("Or run:            pip install -r requirements.txt")
        sys.exit(1)

_check_deps()

from rich.console import Console
from src.ui.wizard import SetupWizard
from src.ui.banner import print_banner, print_section, print_success, print_warning, print_error, print_info
from src.hardware.detector import HardwareDetector
from src.hardware.benchmark import Benchmarker
from src.models.recommender import ModelRecommender
from src.setup.prerequisites import PrerequisiteChecker
from src.setup.alias_manager import AliasManager, DEFAULT_ALIAS
from src.ui.components import (
    hardware_table, benchmark_table, recommendation_panel, prerequisites_table, alias_table
)


def cmd_full(args):
    wizard = SetupWizard(skip_benchmark=args.no_benchmark, quiet=args.quiet)
    wizard.run_full()


def cmd_detect(args):
    console = Console()
    print_banner(console)
    print_section(console, "Hardware Detection")
    info = HardwareDetector().detect()
    console.print(hardware_table(info))
    if args.report:
        _save_report(info.to_dict(), args.report)
        console.print(f"\n[green]Report saved to {args.report}[/green]")


def cmd_benchmark(args):
    console = Console()
    print_banner(console)
    print_section(console, "Hardware Detection")
    info = HardwareDetector().detect()
    console.print(hardware_table(info))

    print_section(console, "Benchmark")
    console.print("[dim]Running benchmarks (~8 seconds)...[/dim]\n")

    def on_progress(msg):
        console.print(f"  [cyan]>[/cyan] {msg}")

    result = Benchmarker(system_info=info).run(on_progress=on_progress)
    console.print()
    console.print(benchmark_table(result))

    vram_mb = max((g.vram_mb for g in info.gpus), default=0)
    rec = ModelRecommender().recommend(
        benchmark_tier=result.tier,
        overall_score=result.overall_score,
        ram_gb=info.ram_total_gb,
        vram_mb=vram_mb,
        is_apple_silicon=info.cpu.is_apple_silicon,
    )
    console.print()
    print_section(console, "Recommendations")
    console.print(recommendation_panel(rec))

    if args.report:
        report = {"hardware": info.to_dict(), "benchmark": {
            "cpu_single_score": result.cpu_single_score,
            "cpu_multi_score":  result.cpu_multi_score,
            "memory_bandwidth_gbps": result.memory_bandwidth_gbps,
            "overall_score": result.overall_score,
            "tier": result.tier,
        }}
        _save_report(report, args.report)
        console.print(f"\n[green]Report saved to {args.report}[/green]")


def cmd_install(args):
    from src.setup.claude_installer import ClaudeCodeInstaller
    console = Console()
    print_banner(console)
    print_section(console, "Install Claude Code")
    installer = ClaudeCodeInstaller(on_log=lambda m: console.print(f"  {m}"))
    ok = installer.install()
    if ok:
        installer.verify()
    else:
        sys.exit(1)


def cmd_check(args):
    console = Console()
    print_banner(console)
    print_section(console, "Prerequisites Check")
    checker = PrerequisiteChecker()
    statuses = checker.check_all()
    console.print(prerequisites_table(statuses))
    missing = checker.missing_required(statuses)
    if missing:
        console.print(f"\n[red]  {len(missing)} required prerequisite(s) missing.[/red]")
        sys.exit(1)
    else:
        console.print("\n[green]  All required prerequisites are satisfied.[/green]")


def cmd_models(args):
    """Print all models in the database as rich tables."""
    from src.models.database import ModelDatabase
    from src.ui.components import all_models_tables
    console = Console()
    print_banner(console)
    print_section(console, "Model Catalog")
    db = ModelDatabase()
    for _section_name, table in all_models_tables(db):
        console.print(table)
        console.print()


def cmd_gui(args):
    """Launch the ClaudeForge graphical interface."""
    try:
        import customtkinter  # noqa: F401
    except ImportError:
        print("customtkinter is not installed.")
        print("Install it with:  pip install customtkinter")
        print("Or run:           pip install -r requirements.txt")
        sys.exit(1)
    from src.gui.app import launch
    launch()


def cmd_alias(args):
    """Create, list, or remove a local alias."""
    console = Console()
    print_banner(console)
    mgr = AliasManager(on_log=lambda m: print_info(console, m))

    # ── List ──────────────────────────────────────────────────────────
    if args.list:
        print_section(console, "Local Aliases")
        statuses = mgr.list_aliases()
        console.print(alias_table(statuses))
        return

    # ── Remove ────────────────────────────────────────────────────────
    if args.remove:
        print_section(console, f"Remove Alias: {args.remove}")
        mgr.remove(args.remove)
        return

    # ── Create ────────────────────────────────────────────────────────
    alias_name = args.name or DEFAULT_ALIAS
    model_id   = args.model or "qwen2.5-coder:7b"
    proxy_port = args.port or 4001

    print_section(console, f"Create Alias: {alias_name}")
    console.print(
        f"  Cloud command : [bold cyan]claude[/bold cyan]  → Anthropic API\n"
        f"  Local command : [bold cyan]{alias_name}[/bold cyan]  → Ollama / {model_id}\n"
    )

    # litellm check
    if not mgr.check_litellm():
        print_warning(console, "litellm is not installed (required for the proxy).")
        console.print("  Install it with:  [bold]pip install litellm[proxy][/bold]")
        console.print()

    info = mgr.create(alias_name=alias_name, model_id=model_id, proxy_port=proxy_port)
    if info:
        print_success(console, f"Alias '{alias_name}' installed at {info.wrapper_path}")
        console.print()
        console.print("  [bold]Usage:[/bold]")
        console.print(f"    [bold cyan]claude[/bold cyan]         — uses Anthropic cloud (unchanged)")
        console.print(f"    [bold cyan]{alias_name}[/bold cyan]  — uses Ollama / {model_id} locally")
        console.print()
        console.print("  [dim]Reload your shell (or open a new terminal) to activate the alias.[/dim]")
    else:
        print_error(console, "Failed to create alias.")
        sys.exit(1)


def _save_report(data: dict, path: str):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claude-setup",
        description=(
            "Claude Code Universal Setup\n\n"
            "Detects your hardware, benchmarks performance, recommends the best "
            "Claude model for your machine, and installs Claude Code CLI."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--detect", action="store_true",
        help="Detect and display hardware information only.",
    )
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Run hardware detection + benchmark + model recommendation.",
    )
    parser.add_argument(
        "--install", action="store_true",
        help="Install Claude Code CLI without running hardware checks.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Check prerequisites only.",
    )
    parser.add_argument(
        "--no-benchmark", action="store_true",
        help="Skip the benchmark step during full setup.",
    )
    parser.add_argument(
        "--report", metavar="FILE", default=None,
        help="Save hardware/benchmark data to a JSON file.",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Reduce output verbosity.",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Launch the modern graphical interface (requires customtkinter).",
    )
    parser.add_argument(
        "--models", action="store_true",
        help="Browse the full model catalog (Claude API + Ollama local models).",
    )

    # ── Alias sub-options ──────────────────────────────────────────────────────
    alias_group = parser.add_argument_group(
        "local alias",
        "Create a separate command that routes Claude Code to a local Ollama model.\n"
        "Your existing `claude` command is never modified."
    )
    alias_group.add_argument(
        "--alias", action="store_true",
        help="Create a local alias (default name: claude-local).",
    )
    alias_group.add_argument(
        "--alias-name", dest="name", metavar="NAME", default=None,
        help=f"Name for the local alias (default: {DEFAULT_ALIAS}).",
    )
    alias_group.add_argument(
        "--alias-model", dest="model", metavar="MODEL", default=None,
        help="Ollama model ID to use (default: qwen2.5-coder:7b).",
    )
    alias_group.add_argument(
        "--alias-port", dest="port", metavar="PORT", type=int, default=None,
        help="Proxy port for litellm (default: 4001).",
    )
    alias_group.add_argument(
        "--alias-list", dest="list", action="store_true",
        help="List all local aliases created by this tool.",
    )
    alias_group.add_argument(
        "--alias-remove", dest="remove", metavar="NAME", default=None,
        help="Remove a local alias by name.",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.gui:
        cmd_gui(args)
    elif args.models:
        cmd_models(args)
    elif args.detect:
        cmd_detect(args)
    elif args.benchmark:
        cmd_benchmark(args)
    elif args.install:
        cmd_install(args)
    elif args.check:
        cmd_check(args)
    elif args.alias or args.list or args.remove:
        cmd_alias(args)
    else:
        cmd_full(args)


if __name__ == "__main__":
    main()
