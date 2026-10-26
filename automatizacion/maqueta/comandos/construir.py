from __future__ import annotations

from maqueta.comandos.base import Comando


class Construir(Comando):
    nombre = "construir"
    ayuda = "crea proyecto, equipos, configs iniciales y cables (idempotente)"
    orden = 30

    def ejecutar(self, app, args):
        app.constructor().construir()
        app.dibujos().aplicar()
