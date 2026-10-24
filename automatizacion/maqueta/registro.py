"""Descubrimiento de plugins: los tipos de nodo y los subcomandos se encuentran solos.

Agregar uno es crear un modulo en el paquete correspondiente con una subclase concreta; no hay lista
que mantener en otro archivo.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import Iterator


def _descendientes(base: type) -> Iterator[type]:
    for sub in base.__subclasses__():
        yield sub
        yield from _descendientes(sub)


def descubrir(base: type, paquete: ModuleType) -> list[type]:
    """Importa todos los modulos de `paquete` y devuelve las subclases concretas de `base` definidas en el."""
    for modulo in pkgutil.iter_modules(paquete.__path__):
        importlib.import_module(f"{paquete.__name__}.{modulo.name}")
    prefijo = paquete.__name__ + "."
    return [c for c in _descendientes(base) if c.__module__.startswith(prefijo) and not inspect.isabstract(c)]
