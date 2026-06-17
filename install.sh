#!/usr/bin/env bash
# Install the 60db skills into your agent's skills directory.
# Default: symlink (so `git pull` keeps the installed skills current).
# Use --copy to copy the files instead of symlinking.
#
#   ./install.sh                 # symlink into ~/.claude/skills
#   ./install.sh --copy          # copy instead
#   CLAUDE_SKILLS_DIR=~/.codex/skills ./install.sh   # install elsewhere
set -euo pipefail

MODE="symlink"
[ "${1:-}" = "--copy" ] && MODE="copy"

SRC="$(cd "$(dirname "$0")/skills" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"

for d in "$SRC"/*/; do
  name="$(basename "$d")"
  target="$DEST/$name"
  rm -rf "$target"
  if [ "$MODE" = "copy" ]; then
    cp -R "$d" "$target"
  else
    ln -s "${d%/}" "$target"
  fi
  echo "installed $name -> $target ($MODE)"
done

echo
echo "Done. Restart your agent session so the skills load, then run /setup-60db."
