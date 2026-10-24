from __future__ import annotations

import sys

from maqueta.comandos.base import Comando
from maqueta.nucleo.registro import descubrir as _descubrir

__all__ = ["Comando", "descubrir"]


def descubrir() -> list[Comando]:
    return sorted((clase() for clase in _descubrir(Comando, sys.modules[__name__])), key=lambda c: (c.orden, c.nombre))
