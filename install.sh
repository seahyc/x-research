#!/usr/bin/env bash
# x-research install script
# Verifies and installs all dependencies needed by the x-research skill,
# then symlinks the skill into ~/.claude/skills/ so Claude Code can find it.

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$REPO_DIR/skills/x-research"
SKILL_LINK="$HOME/.claude/skills/x-research"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

ok()    { echo -e "${GREEN}✓${RESET} $1"; }
warn()  { echo -e "${YELLOW}!${RESET} $1"; }
fail()  { echo -e "${RED}✗${RESET} $1"; }
info()  { echo -e "  $1"; }

echo
echo "x-research installer"
echo "===================="
echo
echo "Tip: if you just want the skill files (no dependency checks), the lightest"
echo "     install is the cross-agent Skills CLI:"
echo "         npx skills add seahyc/x-research"
echo "     This script does that AND verifies all runtime dependencies."
echo

# Detect platform
PLATFORM="$(uname -s)"
case "$PLATFORM" in
  Darwin)  PKGMGR="brew" ;;
  Linux)   PKGMGR="apt" ;;
  *)       PKGMGR="" ;;
esac

# 1. Check ffmpeg
echo "Checking ffmpeg..."
if command -v ffmpeg >/dev/null 2>&1; then
  ok "ffmpeg installed: $(ffmpeg -version 2>&1 | head -1)"
else
  warn "ffmpeg not found"
  if [ "$PKGMGR" = "brew" ]; then
    info "Install with: brew install ffmpeg"
  elif [ "$PKGMGR" = "apt" ]; then
    info "Install with: sudo apt-get install ffmpeg"
  fi
  read -p "Install ffmpeg now? [y/N] " yn
  if [[ "$yn" =~ ^[Yy]$ ]]; then
    if [ "$PKGMGR" = "brew" ]; then
      brew install ffmpeg
    elif [ "$PKGMGR" = "apt" ]; then
      sudo apt-get update && sudo apt-get install -y ffmpeg
    else
      fail "Unknown platform — install ffmpeg manually"
      exit 1
    fi
    ok "ffmpeg installed"
  fi
fi

# 2. Check curl
echo
echo "Checking curl..."
if command -v curl >/dev/null 2>&1; then
  ok "curl installed: $(curl --version | head -1 | awk '{print $1, $2}')"
else
  fail "curl not found — install via your system package manager"
  exit 1
fi

# 3. Check whisper (optional but recommended)
echo
echo "Checking Whisper (audio transcription)..."
WHISPER_BIN=""
for cmd in whisper whisper-cpp /opt/homebrew/Caskroom/miniconda/base/bin/whisper; do
  if command -v "$cmd" >/dev/null 2>&1 || [ -x "$cmd" ]; then
    WHISPER_BIN="$cmd"
    break
  fi
done

if [ -n "$WHISPER_BIN" ]; then
  ok "whisper found at: $WHISPER_BIN"
else
  warn "whisper not found (optional — needed for audio transcription)"
  info "Install options:"
  info "  pip install openai-whisper        # OpenAI Python whisper"
  info "  brew install openai-whisper       # macOS via Homebrew"
  info "  brew install whisper-cpp          # faster C++ port"
  info "  uv tool install openai-whisper    # via uv"
  read -p "Install OpenAI whisper via pip now? [y/N] " yn
  if [[ "$yn" =~ ^[Yy]$ ]]; then
    if command -v uv >/dev/null 2>&1; then
      uv tool install openai-whisper && ok "whisper installed via uv"
    elif command -v pipx >/dev/null 2>&1; then
      pipx install openai-whisper && ok "whisper installed via pipx"
    elif command -v pip >/dev/null 2>&1; then
      pip install --user openai-whisper && ok "whisper installed via pip"
    else
      fail "No Python package manager found — install whisper manually"
    fi
  fi
fi

# 4. Check Chrome / browser
echo
echo "Checking for a Chromium-based browser..."
BROWSER_FOUND=""
for app in "/Applications/Google Chrome.app" "/Applications/Brave Browser.app" "/Applications/Microsoft Edge.app" "/Applications/Arc.app" "/Applications/Dia.app"; do
  if [ -d "$app" ]; then
    BROWSER_FOUND="$(basename "$app" .app)"
    break
  fi
done
if command -v google-chrome >/dev/null 2>&1; then BROWSER_FOUND="google-chrome"; fi
if command -v chromium >/dev/null 2>&1; then BROWSER_FOUND="chromium"; fi

if [ -n "$BROWSER_FOUND" ]; then
  ok "Browser detected: $BROWSER_FOUND"
else
  warn "No Chromium-based browser found"
  info "Install Chrome, Brave, Edge, Arc, or Dia to use the browser automation pipeline"
fi

# 5. Check claude-in-chrome MCP (optional — alternative to chrome-cdp)
echo
echo "Checking for claude-in-chrome MCP server..."
if [ -f "$HOME/.claude/settings.json" ] && grep -q "claude-in-chrome" "$HOME/.claude/settings.json" 2>/dev/null; then
  ok "claude-in-chrome MCP server configured in ~/.claude/settings.json"
else
  warn "claude-in-chrome MCP server not configured (recommended for video URL capture)"
  info "Install from: https://github.com/anthropics/claude-in-chrome"
  info "Alternative: use chrome-cdp (https://github.com/seahyc/chrome-cdp) — see SKILL.md for the mapping"
fi

# 6. Symlink the skill into ~/.claude/skills/
echo
echo "Linking skill into ~/.claude/skills/..."
mkdir -p "$HOME/.claude/skills"
if [ -L "$SKILL_LINK" ]; then
  EXISTING_TARGET="$(readlink "$SKILL_LINK")"
  if [ "$EXISTING_TARGET" = "$SKILL_SRC" ]; then
    ok "Already linked: $SKILL_LINK -> $SKILL_SRC"
  else
    warn "Link exists but points elsewhere: $EXISTING_TARGET"
    read -p "Overwrite to point at $SKILL_SRC? [y/N] " yn
    if [[ "$yn" =~ ^[Yy]$ ]]; then
      rm "$SKILL_LINK" && ln -s "$SKILL_SRC" "$SKILL_LINK"
      ok "Re-linked: $SKILL_LINK -> $SKILL_SRC"
    fi
  fi
elif [ -e "$SKILL_LINK" ]; then
  fail "$SKILL_LINK exists and is not a symlink — manual cleanup required"
  exit 1
else
  ln -s "$SKILL_SRC" "$SKILL_LINK"
  ok "Linked: $SKILL_LINK -> $SKILL_SRC"
fi

# 7. Done
echo
echo "===================="
echo -e "${GREEN}Install complete.${RESET}"
echo
echo "To use:"
echo "  In Claude Code, ask: 'research [topic] on X' or invoke /x-research"
echo
echo "Repo: https://github.com/seahyc/x-research"
echo
