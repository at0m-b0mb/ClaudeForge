#!/usr/bin/env bash
# =============================================================================
# Claude Code Universal Setup — Unix Bootstrap Script
# =============================================================================
# One-liner install (run this directly):
#   curl -fsSL https://raw.githubusercontent.com/at0m-b0mb/claude-code-setup/main/install.sh | bash
#
# Or clone and run locally:
#   git clone https://github.com/at0m-b0mb/claude-code-setup.git
#   cd claude-code-setup && bash install.sh
# =============================================================================

set -euo pipefail

REPO_URL="https://github.com/at0m-b0mb/claude-code-setup"
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=8

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}  ▶${RESET} $*"; }
success() { echo -e "${GREEN}  ✔${RESET} $*"; }
warn()    { echo -e "${YELLOW}  ⚠${RESET} $*"; }
error()   { echo -e "${RED}  ✖${RESET} $*" >&2; }
header()  { echo -e "\n${BOLD}${CYAN}$*${RESET}\n"; }

# ── Banner ────────────────────────────────────────────────────────────────────
print_banner() {
  echo ""
  echo -e "${CYAN}${BOLD}"
  echo "   ____  _                    _         ____          _"
  echo "  / ___|| |__   ___  _ __ ___| |_ ___  / ___|___   __| | ___"
  echo " | |    | '_ \ / _ \| '__/ __| __/ _ \| |   / _ \ / _\` |/ _ \\"
  echo " | |___ | | | | (_) | |  \__ \ ||  __/| |__| (_) | (_| |  __/"
  echo "  \____||_| |_|\___/|_|  |___/\__\___| \____\___/ \__,_|\___|"
  echo ""
  echo "       Universal Installer & Hardware Recommender"
  echo -e "${RESET}"
}

# ── Checks ────────────────────────────────────────────────────────────────────
check_python() {
  header "Checking Python..."

  for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
      version=$("$cmd" --version 2>&1 | awk '{print $2}')
      major=$(echo "$version" | cut -d. -f1)
      minor=$(echo "$version" | cut -d. -f2)

      if [[ "$major" -ge "$REQUIRED_PYTHON_MAJOR" ]] && \
         [[ "$minor" -ge "$REQUIRED_PYTHON_MINOR" ]]; then
        PYTHON="$cmd"
        success "Found $cmd $version"
        return 0
      else
        warn "$cmd $version is too old (need >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR})"
      fi
    fi
  done

  error "Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+ not found."
  echo ""
  echo "Install it:"
  case "$(uname)" in
    Darwin)  echo "  brew install python3  OR  https://www.python.org/downloads/" ;;
    Linux)   echo "  sudo apt install python3  OR  sudo dnf install python3" ;;
    *)       echo "  https://www.python.org/downloads/" ;;
  esac
  exit 1
}

check_pip() {
  header "Checking pip..."
  if "$PYTHON" -m pip --version &>/dev/null; then
    success "pip is available"
  else
    error "pip not found. Install pip: https://pip.pypa.io/en/stable/installation/"
    exit 1
  fi
}

# ── Repo ──────────────────────────────────────────────────────────────────────
ensure_repo() {
  header "Getting the setup scripts..."

  if [[ -f "$(dirname "$0")/main.py" ]]; then
    REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
    info "Running from local clone: $REPO_DIR"
    return
  fi

  if command -v git &>/dev/null; then
    info "Cloning repository..."
    git clone --depth=1 "$REPO_URL" /tmp/claude-code-setup 2>/dev/null || {
      error "Failed to clone repo. Check your internet connection or clone manually:"
      echo "  git clone $REPO_URL"
      exit 1
    }
    REPO_DIR="/tmp/claude-code-setup"
    success "Cloned to $REPO_DIR"
  else
    error "git not found and not running from a local clone."
    echo "Install git or download the repo manually from: $REPO_URL"
    exit 1
  fi
}

# ── Dependencies ──────────────────────────────────────────────────────────────
install_python_deps() {
  header "Installing Python dependencies..."
  "$PYTHON" -m pip install --quiet --upgrade pip
  "$PYTHON" -m pip install --quiet -r "$REPO_DIR/requirements.txt"
  success "Python dependencies installed"
}

# ── Run ───────────────────────────────────────────────────────────────────────
run_setup() {
  header "Launching Claude Code Setup..."
  cd "$REPO_DIR"
  "$PYTHON" main.py "$@"
}

# ── Main ──────────────────────────────────────────────────────────────────────
print_banner

check_python
check_pip
ensure_repo
install_python_deps
run_setup "$@"
