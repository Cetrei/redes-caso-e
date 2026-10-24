from __future__ import annotations

from .base import Comando


class Imagen(Comando):
    nombre = "imagen"
    ayuda = "construye las imagenes Docker en la VM (SSH) y crea sus plantillas"
    orden = 20

    def ejecutar(self, app, args):
        app.imagenes().construir()
