#!/usr/bin/env bash
set -euo pipefail

TOOL_NAME="tuiman"
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=14

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()    { echo -e "${CYAN}==>${RESET} $*"; }
success() { echo -e "${GREEN} ok${RESET} $*"; }
warn()    { echo -e "${YELLOW} !!${RESET} $*"; }
error()   { echo -e "${RED}err${RESET} $*" >&2; exit 1; }

echo ""
echo -e "${CYAN}${TOOL_NAME} installer${RESET}"
echo ""

# Check Python 3.14

info "Python ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+"

PYTHON_BIN=""
for cmd in python3.14 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    if [ "$major" -eq "$REQUIRED_PYTHON_MAJOR" ] && [ "$minor" -ge "$REQUIRED_PYTHON_MINOR" ]; then
      PYTHON_BIN="$cmd"
      success "found Python $version at $(command -v "$cmd")"
      break
    else
      warn "Python $version at $(command -v "$cmd") is too old"
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  error "Python 3.14+ not found. Install it from https://python.org/downloads, then rerun."
fi

# Check / install pipx

echo ""
info "pipx"

if command -v pipx &>/dev/null; then
  PIPX_VERSION=$(pipx --version 2>/dev/null || echo "unknown")
  success "found pipx $PIPX_VERSION"
else
  warn "pipx not found; installing"

  if command -v brew &>/dev/null; then
    info "installing with Homebrew"
    brew install pipx
  elif command -v apt-get &>/dev/null; then
    info "installing with apt"
    sudo apt-get update -qq && sudo apt-get install -y pipx
  elif command -v dnf &>/dev/null; then
    info "installing with dnf"
    sudo dnf install -y pipx
  else
    info "installing with pip"
    "$PYTHON_BIN" -m pip install --user pipx
  fi

  # Ensure pipx is on PATH
  "$PYTHON_BIN" -m pipx ensurepath

  # Re-source PATH in case pipx was just added
  export PATH="$HOME/.local/bin:$PATH"

  if command -v pipx &>/dev/null; then
    success "pipx ready"
  else
    error "pipx is not on PATH. Restart your terminal, then rerun."
  fi
fi

# Install tuiman

echo ""
info "installing ${TOOL_NAME}"

if pipx list 2>/dev/null | grep -q "package ${TOOL_NAME}"; then
  warn "${TOOL_NAME} already installed; upgrading"
  pipx upgrade "$TOOL_NAME"
  success "${TOOL_NAME} upgraded"
else
  pipx install "$TOOL_NAME"
  success "${TOOL_NAME} installed"
fi

echo ""
echo -e "${GREEN}done${RESET} run: ${TOOL_NAME}"
echo ""
