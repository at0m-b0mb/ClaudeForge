"""
Reusable Rich UI components.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn,
    TextColumn, TimeElapsedColumn, TaskProgressColumn,
)
from rich.text import Text
from rich.columns import Columns
from rich import box
from typing import List, Any


# ------------------------------------------------------------------
# Hardware info table
# ------------------------------------------------------------------

def hardware_table(system_info) -> Table:
    t = Table(title="System Hardware", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    t.add_column("Component", style="bold white", min_width=18)
    t.add_column("Details", style="dim white")
    t.add_column("Status", justify="center", min_width=8)

    def status(ok: bool) -> Text:
        return Text("GOOD", style="bold green") if ok else Text("LIMITED", style="bold yellow")

    # OS
    t.add_row("Operating System", system_info.os_name, status(True))

    # CPU
    cpu = system_info.cpu
    cpu_detail = (
        f"{cpu.model}\n"
        f"{cpu.physical_cores}P / {cpu.logical_cores}L cores  "
        f"@ {cpu.max_freq_mhz:.0f} MHz"
        + ("  [Apple Silicon]" if cpu.is_apple_silicon else "")
    )
    t.add_row("CPU", cpu_detail, status(cpu.physical_cores >= 4))

    # RAM
    ram_ok = system_info.ram_total_gb >= 8
    t.add_row(
        "RAM",
        f"{system_info.ram_total_gb:.1f} GB total  /  {system_info.ram_available_gb:.1f} GB free",
        status(ram_ok),
    )

    # GPU(s)
    if system_info.gpus:
        for i, gpu in enumerate(system_info.gpus):
            vram_str = f"  {gpu.vram_mb / 1024:.1f} GB VRAM" if gpu.vram_mb else "  (shared / unknown)"
            accel = []
            if gpu.cuda_available:
                accel.append("CUDA")
            if gpu.metal_available:
                accel.append("Metal")
            if gpu.rocm_available:
                accel.append("ROCm")
            accel_str = f"  [{', '.join(accel)}]" if accel else ""
            gpu_ok = gpu.vram_mb >= 6000 or gpu.metal_available
            t.add_row(
                f"GPU {i + 1}" if len(system_info.gpus) > 1 else "GPU",
                f"{gpu.name}{vram_str}{accel_str}",
                status(gpu_ok),
            )
    else:
        t.add_row("GPU", "No discrete GPU detected", Text("CPU-ONLY", style="bold yellow"))

    # Disk
    disk_ok = system_info.disk_free_gb >= 10
    t.add_row(
        "Disk",
        f"{system_info.disk_total_gb:.1f} GB total  /  {system_info.disk_free_gb:.1f} GB free",
        status(disk_ok),
    )

    return t


# ------------------------------------------------------------------
# Benchmark results table
# ------------------------------------------------------------------

def benchmark_table(result) -> Table:
    tier_colors = {
        "ultra": "bold magenta",
        "high":  "bold green",
        "mid":   "bold yellow",
        "low":   "bold red",
    }
    tier_color = tier_colors.get(result.tier, "white")

    t = Table(title="Benchmark Results", box=box.ROUNDED, header_style="bold cyan")
    t.add_column("Metric", style="bold white", min_width=22)
    t.add_column("Score", justify="right")
    t.add_column("", justify="left")

    t.add_row(
        "CPU Single-Core",
        f"{result.cpu_single_score:,.0f} ops/s",
        _score_bar(result.details.get("cpu_score", 0) / 2),
    )
    t.add_row(
        "CPU Multi-Core",
        f"{result.cpu_multi_score:,.0f} ops/s",
        _score_bar(result.details.get("cpu_score", 0) / 2),
    )
    t.add_row(
        "Memory Bandwidth",
        f"{result.memory_bandwidth_gbps:.2f} GB/s",
        _score_bar(result.details.get("mem_score", 0)),
    )
    t.add_row(
        "GPU VRAM",
        f"{result.details.get('vram_mb', 0) / 1024:.1f} GB",
        _score_bar(min(100, result.details.get("vram_mb", 0) / 245.76)),
    )
    t.add_section()
    t.add_row(
        "Overall Score",
        f"[{tier_color}]{result.overall_score:.1f} / 100[/{tier_color}]",
        Text(f"  Tier: {result.tier.upper()}", style=tier_color),
    )
    return t


def _score_bar(pct: float, width: int = 20) -> str:
    """Return an ASCII bar representing pct (0–100)."""
    filled = int(min(100, max(0, pct)) * width / 100)
    bar = "█" * filled + "░" * (width - filled)
    if pct >= 75:
        color = "bright_green"
    elif pct >= 40:
        color = "yellow"
    else:
        color = "red"
    return f"[{color}]{bar}[/{color}] {pct:.0f}%"


# ------------------------------------------------------------------
# Recommendation panel
# ------------------------------------------------------------------

def recommendation_panel(rec) -> Panel:
    lines = []

    lines.append(f"[bold cyan]Strategy:[/bold cyan] {rec.strategy.replace('_', ' ').title()}")
    lines.append("")
    lines.append(f"[bold white]Reasoning:[/bold white]")
    lines.append(f"  {rec.reasoning}")
    lines.append("")

    lines.append("[bold white]Recommended Claude API Model:[/bold white]")
    pm = rec.primary_api_model
    lines.append(f"  [bold green]{pm.display_name}[/bold green]  -  {pm.description}")
    if rec.alternative_api_model:
        am = rec.alternative_api_model
        lines.append(f"  [dim]Alternative: {am.display_name}  -  {am.description}[/dim]")
    lines.append("")

    if rec.local_models:
        lines.append("[bold white]Runnable Local Models (via Ollama):[/bold white]")
        for lm in rec.local_models:
            vram_str = f"{lm.vram_required_mb / 1024:.0f} GB VRAM" if lm.vram_required_mb else "CPU"
            lines.append(
                f"  [bold yellow]{lm.display_name}[/bold yellow]"
                f"  [{vram_str}]  {lm.use_case}"
            )
        lines.append("")

    if rec.tips:
        lines.append("[bold white]Tips:[/bold white]")
        for tip in rec.tips:
            lines.append(f"  [dim]•[/dim] {tip}")

    body = "\n".join(lines)
    return Panel(body, title="Model Recommendations", border_style="cyan", padding=(1, 2))


# ------------------------------------------------------------------
# Prerequisites table
# ------------------------------------------------------------------

def prerequisites_table(statuses: list) -> Table:
    t = Table(title="Prerequisites", box=box.ROUNDED, header_style="bold cyan")
    t.add_column("Tool", style="bold white", min_width=16)
    t.add_column("Status", justify="center", min_width=8)
    t.add_column("Version / Info", style="dim white")

    for s in statuses:
        if s.found:
            status_text = Text("FOUND", style="bold green")
            info = s.version or ""
        else:
            req_label = "REQUIRED" if s.required else "OPTIONAL"
            status_text = Text(f"MISSING ({req_label})", style="bold red" if s.required else "bold yellow")
            info = s.install_hint
        t.add_row(s.name, status_text, info)

    return t


# ------------------------------------------------------------------
# Alias table
# ------------------------------------------------------------------

def alias_table(statuses: list) -> Table:
    """Render a table of existing claude-local aliases."""
    t = Table(title="Local Aliases", box=box.ROUNDED, header_style="bold cyan")
    t.add_column("Alias", style="bold white", min_width=16)
    t.add_column("Model", style="yellow", min_width=22)
    t.add_column("Port", justify="right", min_width=6)
    t.add_column("On PATH", justify="center", min_width=8)
    t.add_column("Wrapper")

    for s in statuses:
        on_path_text = Text("YES", style="bold green") if s.on_path else Text("NO", style="bold red")
        t.add_row(
            s.alias_name,
            s.model_id,
            str(s.proxy_port),
            on_path_text,
            s.wrapper_path,
        )

    if not statuses:
        t.add_row("[dim]none[/dim]", "", "", "", "")

    return t


# ------------------------------------------------------------------
# Progress spinner factory
# ------------------------------------------------------------------

def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=True,
    )
