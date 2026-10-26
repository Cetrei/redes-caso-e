from __future__ import annotations

from maqueta.comandos.base import Comando
from maqueta.nucleo.errores import ErrorMaqueta


class Validar(Comando):
    nombre = "validar"
    ayuda = "revisa topologia/ sin tocar GNS3 (corrilo antes de cada PR)"
    orden = 10

    def ejecutar(self, app, args):
        informe = app.validador().validar()
        for e in informe.errores:
            app.salida(f"ERROR: {e}")
        for a in informe.avisos:
            app.salida(f"aviso: {a}")
        if not informe.ok:
            raise ErrorMaqueta(f"\n{len(informe.errores)} error(es) en topologia/")
        app.salida(f"topologia ok: {len(app.proyecto.nodos)} equipos, {len(app.proyecto.enlaces)} cables, {len(informe.avisos)} aviso(s)")
