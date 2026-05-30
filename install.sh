#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
#  tuiman installer
# ─────────────────────────────────────────────

TOOL_NAME="tuiman"
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=14

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[info]${RESET}  $*"; }
success() { echo -e "${GREEN}[ok]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[warn]${RESET}  $*"; }
error()   { echo -e "${RED}[error]${RESET} $*" >&2; exit 1; }

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${CYAN}  Installing ${TOOL_NAME}${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# ── Step 1: Check Python 3.14 ──────────────────

info "Checking for Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+..."

PYTHON_BIN=""
for cmd in python3.14 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    if [ "$major" -eq "$REQUIRED_PYTHON_MAJOR" ] && [ "$minor" -ge "$REQUIRED_PYTHON_MINOR" ]; then
      PYTHON_BIN="$cmd"
      success "Found Python $version at $(command -v $cmd)"
      break
    else
      warn "Found Python $version at $(command -v $cmd) — too old, need 3.14+"
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  error "Python 3.14+ not found. Install it from https://python.org/downloads and re-run this script."
fi

# ── Step 2: Check / install pipx ──────────────

echo ""
info "Checking for pipx..."

if command -v pipx &>/dev/null; then
  PIPX_VERSION=$(pipx --version 2>/dev/null || echo "unknown")
  success "pipx already installed (version: $PIPX_VERSION)"
else
  warn "pipx not found — installing now..."

  if command -v brew &>/dev/null; then
    info "Using Homebrew to install pipx..."
    brew install pipx
  elif command -v apt-get &>/dev/null; then
    info "Using apt to install pipx..."
    sudo apt-get update -qq && sudo apt-get install -y pipx
  elif command -v dnf &>/dev/null; then
    info "Using dnf to install pipx..."
    sudo dnf install -y pipx
  else
    info "Falling back to pip to install pipx..."
    "$PYTHON_BIN" -m pip install --user pipx
  fi

  # Ensure pipx is on PATH
  "$PYTHON_BIN" -m pipx ensurepath

  # Re-source PATH in case pipx was just added
  export PATH="$HOME/.local/bin:$PATH"

  if command -v pipx &>/dev/null; then
    success "pipx installed successfully"
  else
    error "pipx install seemed to succeed but 'pipx' is still not on PATH. Try restarting your terminal and re-running."
  fi
fi

# ── Step 3: Install tuiman ─────────────────────

echo ""
info "Installing ${TOOL_NAME} via pipx..."

if pipx list 2>/dev/null | grep -q "package ${TOOL_NAME}"; then
  warn "${TOOL_NAME} is already installed — upgrading instead..."
  pipx upgrade "$TOOL_NAME"
  success "${TOOL_NAME} upgraded to the latest version"
else
  pipx install "$TOOL_NAME"
  success "${TOOL_NAME} installed successfully"
fi

# ── Done ───────────────────────────────────────

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}  All done! Run: ${TOOL_NAME}${RESET}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
