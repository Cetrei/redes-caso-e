from __future__ import annotations

import sys

from ..registro import descubrir as _descubrir
from .base import Comando

__all__ = ["Comando", "descubrir"]


def descubrir() -> list[Comando]:
    return sorted((clase() for clase in _descubrir(Comando, sys.modules[__name__])), key=lambda c: (c.orden, c.nombre))
