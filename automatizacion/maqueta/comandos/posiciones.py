"""posiciones: sincroniza x,y de nodos/ con el lienzo de GNS3, en un sentido o en el otro."""
from __future__ import annotations

from .base import Comando


class Posiciones(Comando):
    nombre = "posiciones"
    ayuda = "aplica x,y de nodos/ al lienzo de GNS3 (--guardar hace lo contrario)"
    orden = 40

    def argumentos(self, parser):
        parser.add_argument("--guardar", action="store_true",
                            help="GNS3 -> repo: escribe en nodos/*.yml las posiciones actuales del lienzo")

    def ejecutar(self, app, args):
        servicio = app.posiciones()
        servicio.guardar() if args.guardar else servicio.aplicar()
