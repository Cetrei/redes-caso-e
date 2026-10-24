"""iniciar, detener, estado y destruir: el ciclo de vida de los nodos del proyecto."""
from __future__ import annotations

from typing import Callable

from ..gns3 import ClienteGns3


class CicloVida:
    def __init__(self, gns3: ClienteGns3, salida: Callable[[str], None]):
        self._gns3 = gns3
        self._salida = salida

    def cambiar(self, accion: str) -> None:
        """`start` o `stop` sobre todos los nodos."""
        self._gns3.accion_nodos(self._gns3.abrir_proyecto(), accion)
        self._salida(f"nodos: {accion} enviado")

    def estado(self) -> None:
        pid = self._gns3.abrir_proyecto()
        for n in sorted(self._gns3.nodos(pid).values(), key=lambda n: n.nombre):
            self._salida(f"{n.nombre:<12}{n.tipo:<16}{n.estado:<9}consola {n.console_host}:{n.console if n.console else '-'}")

    def destruir(self) -> None:
        self._gns3.borrar_proyecto(self._gns3.abrir_proyecto())
        self._salida("proyecto borrado")
