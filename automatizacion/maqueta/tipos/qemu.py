from __future__ import annotations

import re

from ..modelo import Puerto
from .base import TipoNodo


class Qemu(TipoNodo):
    clave = "qemu"
    ejemplo = "port1"
    descripcion = "el FortiGate"

    def puerto(self, nombre: str) -> Puerto:
        m = re.fullmatch(r"port(\d+)", nombre)
        if not m:
            raise self.puerto_invalido(nombre)
        return Puerto(int(m.group(1)) - 1, 0)
