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
    for modulo in pkgutil.iter_modules(paquete.__path__):
        importlib.import_module(f"{paquete.__name__}.{modulo.name}")
    prefijo = paquete.__name__ + "."
    return [c for c in _descendientes(base) if c.__module__.startswith(prefijo) and not inspect.isabstract(c)]
