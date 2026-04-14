"""
Claude Code configurator.
Handles API key storage, shell profile patching, settings.json, and CLAUDE.md templates.
"""

import os
import json
import platform
import subprocess
import shutil
from typing import Callable, Optional


CLAUDE_SETTINGS_TEMPLATE = {
    "model": "claude-sonnet-4-6",
    "theme": "dark",
    "autoUpdaterStatus": "enabled",
    "preferredNotifChannel": "terminal",
}

CLAUDE_MD_TEMPLATE = """\
# Project Guidelines

## Overview
<!-- Describe your project here -->

## Code Style
- Follow existing patterns in the codebase
- Prefer clarity over brevity
- Write self-documenting code

## Testing
- Run tests before committing
- New features should include tests

## Important Files
<!-- List key files and their purposes -->

## Notes for Claude
<!-- Add any project-specific instructions for Claude here -->
"""


def _write_if_absent(path: str, content: str):
    """Write a file only if it does not already exist."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return True
    return False


class Configurator:
    """Configures Claude Code after installation."""

    def __init__(self, on_log: Callable[[str], None] = None):
        self.log = on_log or print

    # ------------------------------------------------------------------
    # API Key
    # ------------------------------------------------------------------

    def save_api_key(self, api_key: str) -> bool:
        """
        Persist the Anthropic API key in the shell profile and the current env.
        Returns True if written to at least one profile.
        """
        if not api_key or not api_key.startswith("sk-ant-"):
            self.log("[warn] API key does not look valid (expected to start with sk-ant-). Skipping.")
            return False

        os.environ["ANTHROPIC_API_KEY"] = api_key
        profile_path = self._detect_shell_profile()

        if profile_path:
            return self._inject_env_var(profile_path, "ANTHROPIC_API_KEY", api_key)
        else:
            self.log("[warn] Could not detect shell profile. Set ANTHROPIC_API_KEY manually.")
            return False

    def _detect_shell_profile(self) -> Optional[str]:
        system = platform.system()
        if system == "Windows":
            return None  # Windows uses System Properties or PowerShell profiles

        shell = os.environ.get("SHELL", "")
        home = os.path.expanduser("~")

        if "zsh" in shell:
            for p in ("~/.zshrc", "~/.zprofile"):
                path = os.path.expanduser(p)
                if os.path.isfile(path):
                    return path
            return os.path.join(home, ".zshrc")

        if "fish" in shell:
            config_dir = os.path.expanduser("~/.config/fish")
            os.makedirs(config_dir, exist_ok=True)
            return os.path.join(config_dir, "config.fish")

        # bash / default
        for p in ("~/.bashrc", "~/.bash_profile", "~/.profile"):
            path = os.path.expanduser(p)
            if os.path.isfile(path):
                return path
        return os.path.expanduser("~/.bashrc")

    def _inject_env_var(self, profile_path: str, key: str, value: str) -> bool:
        try:
            with open(profile_path) as f:
                content = f.read()
        except FileNotFoundError:
            content = ""

        if key in content:
            # Replace existing line
            lines = content.splitlines()
            new_lines = []
            for line in lines:
                if line.strip().startswith(f"export {key}=") or line.strip().startswith(f"{key}="):
                    new_lines.append(f'export {key}="{value}"')
                else:
                    new_lines.append(line)
            new_content = "\n".join(new_lines)
            if not new_content.endswith("\n"):
                new_content += "\n"
        else:
            new_content = content + f'\nexport {key}="{value}"\n'

        with open(profile_path, "w") as f:
            f.write(new_content)

        self.log(f"  API key written to {profile_path}")
        return True

    # ------------------------------------------------------------------
    # settings.json
    # ------------------------------------------------------------------

    def write_settings(self, model_id: Optional[str] = None) -> bool:
        """Write (or patch) ~/.claude/settings.json with sensible defaults."""
        settings_path = os.path.expanduser("~/.claude/settings.json")
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)

        settings = dict(CLAUDE_SETTINGS_TEMPLATE)
        if model_id:
            settings["model"] = model_id

        # Merge with existing settings (never overwrite user's custom keys)
        if os.path.isfile(settings_path):
            try:
                with open(settings_path) as f:
                    existing = json.load(f)
                for k, v in settings.items():
                    existing.setdefault(k, v)
                settings = existing
            except (json.JSONDecodeError, IOError):
                pass

        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")

        self.log(f"  Settings written to {settings_path}")
        return True

    # ------------------------------------------------------------------
    # CLAUDE.md template
    # ------------------------------------------------------------------

    def create_claude_md(self, project_dir: Optional[str] = None) -> bool:
        """
        Create a CLAUDE.md template in the given directory (or cwd).
        Skips if one already exists.
        """
        target_dir = project_dir or os.getcwd()
        target_path = os.path.join(target_dir, "CLAUDE.md")

        if os.path.isfile(target_path):
            self.log(f"  CLAUDE.md already exists at {target_path}. Skipping.")
            return False

        with open(target_path, "w") as f:
            f.write(CLAUDE_MD_TEMPLATE)

        self.log(f"  CLAUDE.md template created at {target_path}")
        return True

    # ------------------------------------------------------------------
    # Ollama (optional local model backend)
    # ------------------------------------------------------------------

    def is_ollama_installed(self) -> bool:
        return shutil.which("ollama") is not None

    def install_ollama(self) -> bool:
        """Attempt to install Ollama (macOS/Linux only)."""
        system = platform.system()
        if system == "Windows":
            self.log("  Download Ollama for Windows from: https://ollama.ai/download")
            return False

        self.log("Installing Ollama...")
        try:
            result = subprocess.run(
                ["bash", "-c", "curl -fsSL https://ollama.ai/install.sh | sh"],
                timeout=120,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self.log("  Ollama installed successfully.")
                return True
            self.log(f"  [warn] Ollama install script exited with {result.returncode}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.log("  [warn] Failed to download Ollama installer.")
        return False

    def pull_ollama_model(self, model_id: str) -> bool:
        """Pull a model via `ollama pull`."""
        if not self.is_ollama_installed():
            self.log("  [error] Ollama is not installed.")
            return False
        self.log(f"  Pulling {model_id} (this may take a while)...")
        try:
            result = subprocess.run(
                ["ollama", "pull", model_id],
                timeout=600,
                capture_output=False,  # Stream output to terminal
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
