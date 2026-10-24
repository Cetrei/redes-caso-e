"""Un modulo por tipo de nodo de GNS3 (dynamips, qemu, docker, switch).

Para soportar un tipo nuevo: crear su modulo aca con una subclase de TipoNodo (ver base.py) y su alias en
proyecto.yml > tipos. No hay nada que registrar: `registro_por_defecto` lo encuentra.
"""
from __future__ import annotations

import sys

from ..registro import descubrir
from .base import ContextoPreparacion, RegistroTipos, TipoNodo

__all__ = ["ContextoPreparacion", "RegistroTipos", "TipoNodo", "registro_por_defecto"]


def registro_por_defecto() -> RegistroTipos:
    return RegistroTipos(clase() for clase in descubrir(TipoNodo, sys.modules[__name__]))
