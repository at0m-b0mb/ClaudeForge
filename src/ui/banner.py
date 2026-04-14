"""
Terminal banner and branding.
"""

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

BANNER_TEXT = r"""
   ________                __     ______
  / ____/ /___ ___  ______/ /__  / ____/___  _________ ____
 / /   / / __ `/ / / / __  / _ \/ /_  / __ \/ ___/ __ `/ _ \
/ /___/ / /_/ / /_/ / /_/ /  __/ __/ / /_/ / /  / /_/ /  __/
\____/_/\__,_/\__,_/\__,_/\___/_/    \____/_/   \__, /\___/
                                                /____/
"""

TAGLINE = "Universal Claude Code Installer & Hardware Recommender"
APP_NAME = "ClaudeForge"
VERSION  = "1.0.0"


def print_banner(console: Console):
    banner = Text(BANNER_TEXT, style="bold cyan", justify="center")
    tagline = Text(TAGLINE, style="dim white", justify="center")
    version_text = Text(f"v{VERSION}", style="bold green", justify="center")

    console.print()
    console.print(banner)
    console.print(tagline)
    console.print(version_text)
    console.print()


def print_section(console: Console, title: str, style: str = "bold blue"):
    console.rule(f"[{style}]{title}[/{style}]")
    console.print()


def print_success(console: Console, message: str):
    console.print(f"[bold green]  [/bold green] {message}")


def print_warning(console: Console, message: str):
    console.print(f"[bold yellow]  [/bold yellow] {message}")


def print_error(console: Console, message: str):
    console.print(f"[bold red]  [/bold red] {message}")


def print_info(console: Console, message: str):
    console.print(f"[bold cyan]  [/bold cyan] {message}")
