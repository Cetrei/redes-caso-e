#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "paramiko"]
# ///
import sys
from pathlib import Path

from maqueta.cli import main

if __name__ == "__main__":
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(Path(__file__).resolve().parent))
