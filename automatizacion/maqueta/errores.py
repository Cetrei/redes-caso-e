from __future__ import annotations

from typing import Iterable


class ErrorMaqueta(Exception):
    pass


class ErrorTopologia(ErrorMaqueta):
    pass


class ErrorValidacion(ErrorMaqueta):
    def __init__(self, errores: Iterable[str]):
        self.errores = tuple(errores)
        super().__init__("topologia/ tiene errores, corrige antes de construir:\n  " + "\n  ".join(self.errores))


class ErrorGns3(ErrorMaqueta):
    pass


class ErrorEstado(ErrorMaqueta):
    pass


class ErrorConsola(ErrorMaqueta):
    pass


class ErrorConexionConsola(ErrorConsola):
    pass


class ErrorSecretos(ErrorMaqueta):
    pass


class ErrorVm(ErrorMaqueta):
    pass
