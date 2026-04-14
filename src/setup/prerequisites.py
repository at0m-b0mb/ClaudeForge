"""
Prerequisites checker.
Verifies and reports on required tools: Python, Node.js, npm, git, curl.
"""

import shutil
import subprocess
import platform
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class PrerequisiteStatus:
    name: str
    found: bool
    version: Optional[str]
    path: Optional[str]
    required: bool
    install_hint: str


def _run(cmd: list) -> Tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False, ""


def _version_of(binary: str, flag: str = "--version") -> Optional[str]:
    ok, out = _run([binary, flag])
    if ok and out:
        # Return the first meaningful line
        return out.splitlines()[0].strip()
    return None


class PrerequisiteChecker:
    """Checks all tools needed for Claude Code to be installed and used."""

    def check_all(self) -> List[PrerequisiteStatus]:
        checks = [
            self._check_python(),
            self._check_node(),
            self._check_npm(),
            self._check_git(),
            self._check_curl(),
        ]
        return checks

    def all_required_met(self, statuses: List[PrerequisiteStatus]) -> bool:
        return all(s.found for s in statuses if s.required)

    def missing_required(self, statuses: List[PrerequisiteStatus]) -> List[PrerequisiteStatus]:
        return [s for s in statuses if s.required and not s.found]

    # ------------------------------------------------------------------

    def _check_python(self) -> PrerequisiteStatus:
        binary = "python3" if shutil.which("python3") else "python"
        version = _version_of(binary)
        return PrerequisiteStatus(
            name="Python 3",
            found=version is not None,
            version=version,
            path=shutil.which(binary),
            required=True,
            install_hint="Visit https://www.python.org/downloads/ or use your system package manager.",
        )

    def _check_node(self) -> PrerequisiteStatus:
        version = _version_of("node")
        # Claude Code requires Node.js >= 18
        meets_min = False
        if version:
            try:
                major = int(version.lstrip("v").split(".")[0])
                meets_min = major >= 18
            except (ValueError, IndexError):
                meets_min = False
        return PrerequisiteStatus(
            name="Node.js (>=18)",
            found=meets_min,
            version=version,
            path=shutil.which("node"),
            required=True,
            install_hint=self._node_install_hint(),
        )

    def _check_npm(self) -> PrerequisiteStatus:
        version = _version_of("npm")
        return PrerequisiteStatus(
            name="npm",
            found=version is not None,
            version=version,
            path=shutil.which("npm"),
            required=True,
            install_hint="npm is bundled with Node.js. Re-installing Node should fix this.",
        )

    def _check_git(self) -> PrerequisiteStatus:
        version = _version_of("git")
        return PrerequisiteStatus(
            name="git",
            found=version is not None,
            version=version,
            path=shutil.which("git"),
            required=False,
            install_hint="https://git-scm.com/downloads",
        )

    def _check_curl(self) -> PrerequisiteStatus:
        version = _version_of("curl")
        return PrerequisiteStatus(
            name="curl",
            found=version is not None,
            version=version,
            path=shutil.which("curl"),
            required=False,
            install_hint="Install via your system package manager (e.g., `sudo apt install curl`).",
        )

    @staticmethod
    def _node_install_hint() -> str:
        system = platform.system()
        if system == "Darwin":
            return (
                "Install via nvm: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash && nvm install 22`\n"
                "  Or via Homebrew: `brew install node`"
            )
        if system == "Linux":
            return (
                "Install via nvm: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash && nvm install 22`\n"
                "  Or via NodeSource: https://github.com/nodesource/distributions"
            )
        if system == "Windows":
            return "Download from https://nodejs.org or use winget: `winget install OpenJS.NodeJS.LTS`"
        return "Visit https://nodejs.org/en/download/"
