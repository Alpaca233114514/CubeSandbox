#!/usr/bin/env bash
# Source this file in Git Bash before running `make` on Windows.
#
#   source dev-env/windows-env.sh
#   make all
#
# It adds the GnuWin32 make directory (installed by winget) to PATH and sets
# the environment variables needed for Docker-based builds to work from MSYS2.

set -euo pipefail

MAKE_DIR="/c/Program Files (x86)/GnuWin32/bin"

if [[ -f "$MAKE_DIR/make.exe" ]]; then
    if [[ ":$PATH:" != *":$MAKE_DIR:"* ]]; then
        export PATH="$MAKE_DIR:$PATH"
        echo "Added $MAKE_DIR to PATH"
    fi
else
    echo "WARNING: make.exe not found at $MAKE_DIR/make.exe" >&2
    echo "Install it with: winget install --id GnuWin32.Make --exact" >&2
fi

# Git Bash path conversion breaks Docker volume mounts and workdir paths.
export MSYS_NO_PATHCONV=1

# Use the bare command name when make invokes itself inside Docker.
export MAKE=make

echo "Windows dev environment ready. Run: make all"
