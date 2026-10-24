from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..entorno import Entorno
from ..gns3 import NodoGns3
from ..modelo import Proyecto


@dataclass(frozen=True)
class Movimiento:
    nombre: str
    repo: tuple[int, int]
    gns3: tuple[int, int]


def diferencias(proyecto: Proyecto, en_gns3: Mapping[str, NodoGns3]) -> list[Movimiento]:
    return [Movimiento(nodo.nombre, (nodo.x, nodo.y), (n.x, n.y))
            for nodo in proyecto.nodos.values()
            if (n := en_gns3.get(nodo.nombre)) is not None and (n.x, n.y) != (nodo.x, nodo.y)]


class Posiciones:
    def __init__(self, entorno: Entorno):
        self._gns3 = entorno.gns3
        self._p = entorno.proyecto
        self._repo = entorno.repositorio
        self._salida = entorno.salida

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
