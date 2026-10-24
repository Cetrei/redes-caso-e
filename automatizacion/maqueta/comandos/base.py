"""Contrato de los subcomandos de gns3ctl.py.

Para un subcomando nuevo: crear un modulo en este paquete con una subclase de Comando. `descubrir` la
encuentra sola; `orden` fija su lugar en la ayuda.
"""
from __future__ import annotations

import argparse
from abc import ABC, abstractmethod
from typing import ClassVar

from ..aplicacion import Aplicacion


class Comando(ABC):
    nombre: ClassVar[str]
    ayuda: ClassVar[str]
    orden: ClassVar[int] = 100

    def argumentos(self, parser: argparse.ArgumentParser) -> None:
        """Opciones propias del subcomando. Por defecto no tiene."""

    @abstractmethod
    def ejecutar(self, app: Aplicacion, args: argparse.Namespace) -> None:
        """Hace el trabajo a traves de los servicios de `app`. Los errores esperados son ErrorMaqueta."""
