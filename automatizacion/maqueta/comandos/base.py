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
        pass

    @abstractmethod
    def ejecutar(self, app: Aplicacion, args: argparse.Namespace) -> None:
        pass
