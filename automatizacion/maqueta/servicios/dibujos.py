from __future__ import annotations

from maqueta.nucleo.dibujo import dibujos_de
from maqueta.servicios.entorno import Entorno


class Dibujos:
    def __init__(self, entorno: Entorno):
        self._gns3 = entorno.gns3
        self._p = entorno.proyecto
        self._salida = entorno.salida

    def aplicar(self) -> None:
        pid = self._gns3.abrir_proyecto()
        actuales = {d.clave: d for d in self._gns3.dibujos(pid) if d.clave}
        deseados = {d.clave: d for d in dibujos_de(self._p)}
        nuevos = [d for c, d in deseados.items() if c not in actuales]
        cambiados = [(actuales[c], d) for c, d in deseados.items() if c in actuales and actuales[c].difiere(d)]
        sobran = [a for c, a in actuales.items() if c not in deseados]
        for d in nuevos:
            self._gns3.crear_dibujo(pid, d)
        for actual, d in cambiados:
            self._gns3.actualizar_dibujo(pid, actual.drawing_id, d)
        for a in sobran:
            self._gns3.borrar_dibujo(pid, a.drawing_id)
        self._resumen(len(nuevos), len(cambiados), len(sobran))

    def _resumen(self, nuevos: int, cambiados: int, sobran: int) -> None:
        if not (nuevos or cambiados or sobran):
            self._salida("dibujos: sin cambios")
            return
        self._salida(f"dibujos: {nuevos} creados, {cambiados} actualizados, {sobran} retirados")
