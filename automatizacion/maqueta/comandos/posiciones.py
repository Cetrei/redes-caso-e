from __future__ import annotations

from maqueta.comandos.base import Comando


class Posiciones(Comando):
    nombre = "posiciones"
    ayuda = "aplica x,y de nodos/ y dibuja zonas y notas en el lienzo de GNS3 (--guardar: GNS3 a nodos/)"
    orden = 40

    def argumentos(self, parser):
        parser.add_argument("--guardar", action="store_true",
                            help="GNS3 -> repo: escribe en nodos/*.yml las posiciones actuales del lienzo")

    def ejecutar(self, app, args):
        servicio = app.posiciones()
        if args.guardar:
            servicio.guardar()
            return
        servicio.aplicar()
        app.dibujos().aplicar()
