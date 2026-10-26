from __future__ import annotations

import sys

from maqueta.nucleo.registro import descubrir
from maqueta.tipos.base import ContextoPreparacion, RegistroTipos, TipoNodo

__all__ = ["ContextoPreparacion", "RegistroTipos", "TipoNodo", "registro_por_defecto"]


def registro_por_defecto() -> RegistroTipos:
    return RegistroTipos(clase() for clase in descubrir(TipoNodo, sys.modules[__name__]))
