"""
Node.js installer.
Installs Node.js via nvm (preferred) or system package manager.
"""

import os
import platform
import subprocess
import shutil
import sys
from typing import Callable, Optional


def _run(cmd: list, env: dict = None, timeout: int = 120) -> tuple:
    merged_env = {**os.environ, **(env or {})}
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=merged_env
        )
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return False, str(e)


class NodeInstaller:
    """Installs Node.js 22 LTS cross-platform."""

    NVM_VERSION = "v0.40.1"
    NODE_VERSION = "22"

    def __init__(self, on_log: Callable[[str], None] = None):
        self.log = on_log or print

    def install(self) -> bool:
        """
        Attempt Node.js installation. Returns True on success.
        Tries, in order: nvm, system package manager, manual download hint.
        """
        system = platform.system()
        if system in ("Darwin", "Linux"):
            return self._install_via_nvm()
        if system == "Windows":
            return self._install_windows()
        self.log(f"[warn] Unsupported OS: {system}. Please install Node.js manually.")
        return False

    # ------------------------------------------------------------------
    # nvm (macOS / Linux)
    # ------------------------------------------------------------------

    def _install_via_nvm(self) -> bool:
        nvm_dir = os.path.expanduser("~/.nvm")

        if not os.path.isdir(nvm_dir):
            self.log("Downloading nvm installer...")
            ok, out = _run([
                "bash", "-c",
                f"curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/{self.NVM_VERSION}/install.sh | bash"
            ], timeout=60)
            if not ok:
                self.log(f"[error] nvm install failed: {out}")
                return self._install_via_package_manager()

        self.log(f"Installing Node.js {self.NODE_VERSION} via nvm...")
        nvm_sh = os.path.join(nvm_dir, "nvm.sh")
        ok, out = _run([
            "bash", "-c",
            f'export NVM_DIR="{nvm_dir}" && [ -s "{nvm_sh}" ] && . "{nvm_sh}" && nvm install {self.NODE_VERSION} && nvm alias default {self.NODE_VERSION}'
        ], timeout=180)

        if not ok:
            self.log(f"[error] Node.js install via nvm failed: {out}")
            return False

        self.log(f"Node.js {self.NODE_VERSION} installed via nvm.")
        self._add_nvm_to_shell_profile()
        return True

    def _add_nvm_to_shell_profile(self):
        """Ensure nvm is sourced in shell startup files."""
        nvm_dir = os.path.expanduser("~/.nvm")
        snippet = (
            f'\nexport NVM_DIR="{nvm_dir}"\n'
            f'[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"\n'
            f'[ -s "$NVM_DIR/bash_completion" ] && . "$NVM_DIR/bash_completion"\n'
        )
        shell = os.environ.get("SHELL", "")
        profiles = []
        if "zsh" in shell:
            profiles = ["~/.zshrc", "~/.zprofile"]
        elif "bash" in shell:
            profiles = ["~/.bashrc", "~/.bash_profile"]
        else:
            profiles = ["~/.profile"]

        for p in profiles:
            path = os.path.expanduser(p)
            if os.path.isfile(path):
                with open(path) as f:
                    content = f.read()
                if "NVM_DIR" not in content:
                    with open(path, "a") as f:
                        f.write(snippet)
                    self.log(f"  Added nvm init to {p}")
                break

    # ------------------------------------------------------------------
    # Package manager (macOS / Linux fallback)
    # ------------------------------------------------------------------

    def _install_via_package_manager(self) -> bool:
        system = platform.system()
        if system == "Darwin":
            return self._install_brew()
        if system == "Linux":
            return self._install_apt() or self._install_dnf() or self._install_pacman()
        return False

    def _install_brew(self) -> bool:
        if not shutil.which("brew"):
            self.log("[warn] Homebrew not found. Skipping brew install.")
            return False
        self.log("Installing Node.js via Homebrew...")
        ok, out = _run(["brew", "install", "node"], timeout=300)
        if ok:
            self.log("Node.js installed via Homebrew.")
        else:
            self.log(f"[error] brew install node failed: {out}")
        return ok

    def _install_apt(self) -> bool:
        if not shutil.which("apt-get"):
            return False
        self.log("Setting up NodeSource repo and installing Node.js via apt...")
        # NodeSource setup
        ok, out = _run([
            "bash", "-c",
            f"curl -fsSL https://deb.nodesource.com/setup_{self.NODE_VERSION}.x | sudo -E bash -"
        ], timeout=120)
        if not ok:
            return False
        ok, out = _run(["sudo", "apt-get", "install", "-y", "nodejs"], timeout=180)
        if ok:
            self.log("Node.js installed via apt.")
        return ok

    def _install_dnf(self) -> bool:
        if not shutil.which("dnf"):
            return False
        self.log("Installing Node.js via dnf (Fedora/RHEL)...")
        ok, out = _run(["sudo", "dnf", "install", "-y", "nodejs"], timeout=180)
        if ok:
            self.log("Node.js installed via dnf.")
        return ok

    def _install_pacman(self) -> bool:
        if not shutil.which("pacman"):
            return False
        self.log("Installing Node.js via pacman (Arch)...")
        ok, out = _run(["sudo", "pacman", "-S", "--noconfirm", "nodejs", "npm"], timeout=180)
        if ok:
            self.log("Node.js installed via pacman.")
        return ok

    # ------------------------------------------------------------------
    # Windows
    # ------------------------------------------------------------------

    def _install_windows(self) -> bool:
        # Try winget first
        if shutil.which("winget"):
            self.log("Installing Node.js via winget...")
            ok, out = _run(
                ["winget", "install", "--id", "OpenJS.NodeJS.LTS", "--silent"],
                timeout=300,
            )
            if ok:
                self.log("Node.js installed via winget.")
                return True
        # Try choco
        if shutil.which("choco"):
            self.log("Installing Node.js via Chocolatey...")
            ok, out = _run(["choco", "install", "nodejs-lts", "-y"], timeout=300)
            if ok:
                self.log("Node.js installed via Chocolatey.")
                return True
        self.log(
            "[warn] Could not install Node.js automatically on Windows.\n"
            "  Download from: https://nodejs.org/en/download/\n"
            "  Or use: winget install OpenJS.NodeJS.LTS"
        )
        return False
