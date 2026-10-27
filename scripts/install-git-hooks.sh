#!/bin/sh
# Point git at the versioned hooks in .githooks/ (run once per clone).
set -e
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
echo "Git hooks installed from .githooks/ (secret scan runs on every commit)."
command -v gitleaks >/dev/null 2>&1 || echo "WARNING: gitleaks not found. Install it: brew install gitleaks"
