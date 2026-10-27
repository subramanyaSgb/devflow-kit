#!/bin/sh
# Locate a Python 3 and run the guard; fail open if none is found.
DIR="$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then exec python3 "$DIR/devlog_guard.py"; fi
if command -v python  >/dev/null 2>&1; then exec python  "$DIR/devlog_guard.py"; fi
exit 0
