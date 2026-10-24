from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from maqueta.aplicacion import Aplicacion
from maqueta.comandos import Comando, descubrir
from maqueta.nucleo.errores import ErrorMaqueta, ErrorTopologia

DESCRIPCION = """Arma y opera la maqueta del Caso E en un servidor GNS3 2.2 a partir de los archivos de topologia/.

Es idempotente: se puede repetir cualquier subcomando sin duplicar nada.
"""


def crear_parser(comandos: Sequence[Comando]) -> argparse.ArgumentParser:
    ayuda = "\n".join(f"  {c.nombre:<11} {c.ayuda}" for c in comandos)
    parser = argparse.ArgumentParser(prog="gns3ctl.py", description=DESCRIPCION + "\nSubcomandos:\n" + ayuda,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="subcomando", required=True, metavar="subcomando")
    for c in comandos:
        p = sub.add_parser(c.nombre, help=c.ayuda)
        c.argumentos(p)
        p.set_defaults(comando=c)
    return parser


def main(base: Path, argv: Sequence[str] | None = None, app: Aplicacion | None = None) -> int:
    args = crear_parser(descubrir()).parse_args(argv)
    app = app or Aplicacion.crear(base)
    try:
        args.comando.ejecutar(app, args)
    except ErrorTopologia as e:
        print(f"topologia/ invalida: {e}", file=sys.stderr)
        return 1
    except ErrorMaqueta as e:
        print(e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrumpido", file=sys.stderr)
        return 130
    return 0
