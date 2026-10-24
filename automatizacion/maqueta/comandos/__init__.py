"""Un modulo por subcomando de gns3ctl.py (o por familia: ciclo.py trae iniciar, detener, estado y destruir).

Para un subcomando nuevo: crear su modulo aca con una subclase de Comando (ver base.py). No hay lista que
mantener: `descubrir` lo encuentra.
"""
from __future__ import annotations

import sys

from ..registro import descubrir as _descubrir
from .base import Comando

__all__ = ["Comando", "descubrir"]


def descubrir() -> list[Comando]:
    """Todos los subcomandos, ordenados por `orden` y luego por nombre."""
    return sorted((clase() for clase in _descubrir(Comando, sys.modules[__name__])), key=lambda c: (c.orden, c.nombre))
