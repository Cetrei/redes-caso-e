"""Errores esperados del motor.

Todo ErrorMaqueta lleva un mensaje listo para quien usa la herramienta: la linea de comandos lo
muestra sin traza y termina con codigo 1. Una excepcion que no herede de ErrorMaqueta es un bug.
"""
from __future__ import annotations

from typing import Iterable


class ErrorMaqueta(Exception):
    """Base de todo error esperado."""


class ErrorTopologia(ErrorMaqueta):
    """Dato mal formado o inconsistente en topologia/."""


class ErrorValidacion(ErrorMaqueta):
    """topologia/ no paso `validar`; conserva la lista de errores."""

    def __init__(self, errores: Iterable[str]):
        self.errores = tuple(errores)
        super().__init__("topologia/ tiene errores, corrige antes de construir:\n  " + "\n  ".join(self.errores))


class ErrorGns3(ErrorMaqueta):
    """El servidor GNS3 respondio con un error o no se pudo alcanzar."""


class ErrorEstado(ErrorMaqueta):
    """La operacion no se puede hacer en el estado actual de la maqueta (nodo apagado, proyecto inexistente...)."""


class ErrorConsola(ErrorMaqueta):
    """No se pudo iniciar sesion o hablar con la consola de un nodo."""


class ErrorConexionConsola(ErrorConsola):
    """No se pudo abrir el socket de la consola (el nodo aun no escucha). Se puede reintentar."""


class ErrorSecretos(ErrorMaqueta):
    """secretos.yml falta o esta incompleto."""


class ErrorVm(ErrorMaqueta):
    """No se pudo trabajar con la VM de GNS3 por SSH."""
