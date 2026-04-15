"""
Claude Code installer.
Installs @anthropic-ai/claude-code via npm and verifies the installation.
"""

import os
import subprocess
import shutil
import platform
from typing import Callable, Optional, Tuple


def _run(cmd: list, env: dict = None, timeout: int = 120) -> Tuple[bool, str]:
    merged_env = {**os.environ, **(env or {})}
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=merged_env
        )
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return False, str(e)


def _nvm_node_env() -> dict:
    """Build an env dict that includes nvm-managed node/npm on PATH."""
    nvm_dir = os.path.expanduser("~/.nvm")
    nvm_sh = os.path.join(nvm_dir, "nvm.sh")
    if not os.path.isfile(nvm_sh):
        return {}
    # Use subprocess directly so we can read only stdout (nvm may write
    # informational messages to stderr which would corrupt the PATH value).
    try:
        r = subprocess.run(
            ["bash", "-c",
             f'export NVM_DIR="{nvm_dir}" && . "{nvm_sh}" && echo $PATH'],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0 and r.stdout.strip():
            return {"PATH": r.stdout.strip()}
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return {}


class ClaudeCodeInstaller:
    """Installs and verifies Claude Code CLI."""

    PACKAGE = "@anthropic-ai/claude-code"

    def __init__(self, on_log: Callable[[str], None] = None):
        self.log = on_log or print

    def is_installed(self) -> bool:
        """Check whether `claude` binary is on PATH."""
        return shutil.which("claude") is not None

    def installed_version(self) -> Optional[str]:
        ok, out = _run(["claude", "--version"])
        return out.strip() if ok and out else None

    def install(self) -> bool:
        """
        Install Claude Code globally via npm.
        Returns True on success.
        """
        if self.is_installed():
            ver = self.installed_version()
            self.log(f"Claude Code is already installed ({ver}).")
            return True

        npm = shutil.which("npm")
        if not npm:
            # Try nvm-managed npm
            env = _nvm_node_env()
            if env:
                paths = env.get("PATH", "").split(os.pathsep)
                npm = next(
                    (os.path.join(p, "npm") for p in paths if os.path.isfile(os.path.join(p, "npm"))),
                    None
                )
            if not npm:
                self.log("[error] npm not found. Please install Node.js first.")
                return False

        self.log(f"Installing {self.PACKAGE} globally via npm...")
        cmd = [npm, "install", "-g", self.PACKAGE]

        # On macOS/Linux, try with --prefix to avoid sudo
        env = _nvm_node_env()
        ok, out = _run(cmd, env=env if env else None, timeout=180)

        if not ok:
            self.log(f"[warn] npm install failed, retrying with sudo...")
            ok, out = _run(["sudo"] + cmd, timeout=180)

        if ok:
            self.log("Claude Code installed successfully.")
            ver = self.installed_version()
            if ver:
                self.log(f"  Version: {ver}")
            return True

        self.log(f"[error] Failed to install Claude Code:\n{out}")
        return False

    def update(self) -> bool:
        """Update Claude Code to the latest version."""
        npm = shutil.which("npm")
        if not npm:
            self.log("[error] npm not found.")
            return False
        self.log(f"Updating {self.PACKAGE}...")
        ok, out = _run([npm, "update", "-g", self.PACKAGE], timeout=120)
        if ok:
            self.log("Claude Code updated.")
        else:
            self.log(f"[warn] Update may have failed: {out}")
        return ok

    def verify(self) -> bool:
        """Run a quick sanity-check to confirm claude is callable."""
        ok, out = _run(["claude", "--version"])
        if ok:
            self.log(f"Verification passed: {out.splitlines()[0]}")
        else:
            self.log("[error] `claude --version` failed. Installation may be broken.")
        return ok
