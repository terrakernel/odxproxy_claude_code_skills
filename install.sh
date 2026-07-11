#!/usr/bin/env bash
#
# install.sh — link (or copy) every skill in this repo into a Claude Code
# skills directory so they are discovered.
#
# Usage:
#   ./install.sh [TARGET_DIR] [--copy]
#
#   TARGET_DIR   where to install skills (default: ~/.claude/skills).
#                For a project-scoped install, pass e.g. .claude/skills.
#   --copy       copy the skill folders instead of symlinking them.
#                Default is symlink, so `git pull` updates installed skills.
#
# A "skill" is any immediate subfolder of this repo that contains a SKILL.md.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${HOME}/.claude/skills"
MODE="symlink"
for arg in "$@"; do
    case "$arg" in
        --copy) MODE="copy" ;;
        --symlink) MODE="symlink" ;;
        -h|--help)
            sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) TARGET="$arg" ;;
    esac
done

mkdir -p "$TARGET"

installed=0
for skill in "$REPO_DIR"/*/; do
    name="$(basename "$skill")"
    [ -f "${skill}SKILL.md" ] || continue   # only real skill folders

    dest="${TARGET%/}/${name}"
    if [ -e "$dest" ] || [ -L "$dest" ]; then
        echo "• $name: already present at $dest — removing and reinstalling"
        rm -rf "$dest"
    fi

    if [ "$MODE" = "copy" ]; then
        cp -R "${skill%/}" "$dest"
        echo "✓ copied  $name -> $dest"
    else
        ln -s "${skill%/}" "$dest"
        echo "✓ linked  $name -> $dest"
    fi
    installed=$((installed + 1))
done

if [ "$installed" -eq 0 ]; then
    echo "No skills (folders containing SKILL.md) found in $REPO_DIR" >&2
    exit 1
fi

echo
echo "Installed $installed skill(s) into $TARGET"
echo "Start a new Claude Code session to pick them up."
