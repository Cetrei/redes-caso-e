"""posiciones: la posicion de cada equipo en el lienzo de GNS3 es x e y de su archivo en nodos/.

`aplicar` lleva el repo a GNS3; `guardar` copia lo que moviste en la GUI de vuelta a los archivos."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from ..gns3 import ClienteGns3, NodoGns3
from ..modelo import Proyecto
from ..repositorio import Repositorio


@dataclass(frozen=True)
class Movimiento:
    nombre: str
    repo: tuple[int, int]
    gns3: tuple[int, int]


def diferencias(proyecto: Proyecto, en_gns3: Mapping[str, NodoGns3]) -> list[Movimiento]:
    """Equipos cuya posicion en GNS3 difiere de la de su archivo. Los que aun no existen en GNS3 se ignoran."""
    return [Movimiento(nodo.nombre, (nodo.x, nodo.y), (n.x, n.y))
            for nodo in proyecto.nodos.values()
            if (n := en_gns3.get(nodo.nombre)) is not None and (n.x, n.y) != (nodo.x, nodo.y)]


class Posiciones:
    def __init__(self, gns3: ClienteGns3, proyecto: Proyecto, repositorio: Repositorio, salida: Callable[[str], None]):
        self._gns3 = gns3
        self._p = proyecto
        self._repo = repositorio
        self._salida = salida

    def aplicar(self) -> None:
        pid = self._gns3.abrir_proyecto()
        en_gns3 = self._gns3.nodos(pid)
        movimientos = diferencias(self._p, en_gns3)
        for m in movimientos:
            self._gns3.actualizar_nodo(pid, en_gns3[m.nombre].node_id, {"x": m.repo[0], "y": m.repo[1]})
            self._salida(f"{m.nombre}: movido de {m.gns3} a {m.repo}")
        self._resumen(len(movimientos), "movidos en GNS3")

    def guardar(self) -> None:
        movimientos = diferencias(self._p, self._gns3.nodos(self._gns3.abrir_proyecto()))
        for m in movimientos:
            self._repo.actualizar_posicion(m.nombre, *m.gns3)
            self._salida(f"{m.nombre}: archivo actualizado a x={m.gns3[0]} y={m.gns3[1]}")
        self._resumen(len(movimientos), "guardados en nodos/")

    def _resumen(self, cantidad: int, destino: str) -> None:
        self._salida("sin cambios" if not cantidad else f"{cantidad} equipo(s) {destino}")
