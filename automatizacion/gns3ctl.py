#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "paramiko"]
# ///
"""Arma y opera la maqueta del Caso E en un servidor GNS3 2.2 a partir de los archivos de topologia/.

Es idempotente: se puede repetir cualquier subcomando sin duplicar nada.
Estructura y como agregar, quitar o mover equipos: automatizacion/README.md
"""
import argparse, sys

try:
    from maqueta.comandos import todos
except Exception as e:                      # topologia/ mal formada: mensaje corto en vez de traza
    if type(e).__name__ == "ErrorTopologia":
        sys.exit(f"topologia/ invalida: {e}")
    raise
from maqueta.config import ErrorTopologia


def main():
    comandos = todos()
    ayuda = "\n".join(f"  {nombre:<11} {desc}" for nombre, (_, desc, _) in comandos.items())
    ap = argparse.ArgumentParser(description=__doc__ + "\nSubcomandos:\n" + ayuda, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="subcomando")
    for nombre, (fn, desc, extra) in comandos.items():
        p = sub.add_parser(nombre, help=desc)
        if extra:
            extra(p)
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    try:
        a.fn(a)
    except ErrorTopologia as e:
        sys.exit(f"topologia/ invalida: {e}")


if __name__ == "__main__":
    main()
