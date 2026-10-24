#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "paramiko"]
# ///
"""Entrada de la linea de comandos. Toda la logica vive en el paquete maqueta/ (ver automatizacion/README.md)."""
import sys
from pathlib import Path

from maqueta.cli import main

if __name__ == "__main__":
    sys.exit(main(Path(__file__).resolve().parent))
