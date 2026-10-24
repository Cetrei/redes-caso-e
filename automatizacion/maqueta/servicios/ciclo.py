from __future__ import annotations

from maqueta.servicios.entorno import Entorno


class CicloVida:
    def __init__(self, entorno: Entorno):
        self._gns3 = entorno.gns3
        self._salida = entorno.salida

    def cambiar(self, accion: str) -> None:
        self._gns3.accion_nodos(self._gns3.abrir_proyecto(), accion)
        self._salida(f"nodos: {accion} enviado")

    def estado(self) -> None:
        pid = self._gns3.abrir_proyecto()
        for n in sorted(self._gns3.nodos(pid).values(), key=lambda n: n.nombre):
            self._salida(f"{n.nombre:<12}{n.tipo:<16}{n.estado:<9}consola {n.console_host}:{n.console if n.console else '-'}")

    def destruir(self) -> None:
        self._gns3.borrar_proyecto(self._gns3.abrir_proyecto())
        self._salida("proyecto borrado")
