from __future__ import annotations

import re

from maqueta.bordes.fortigate_cli import SesionFortigate
from maqueta.nucleo.errores import ErrorConsola, ErrorEstado, ErrorTopologia
from maqueta.servicios.entorno import Entorno

_VIP_EN_USO = re.compile(r"^set extintf .*Return code -23")
_SIN_CUPO = "maximum number"


class PegadorConfigFortigate:
    def __init__(self, entorno: Entorno):
        self._gns3 = entorno.gns3
        self._p = entorno.proyecto
        self._repo = entorno.repositorio
        self._abrir_sesion = entorno.sesion_fortigate
        self._salida = entorno.salida
        self._destino = ""

    def pegar(self, equipo: str | None = None) -> None:
        nombre = equipo or self._p.fortigate_requerido().nodo
        sesion = self._abrir(nombre)
        definicion = self._p.nodos[nombre]
        archivo = definicion.config_para(self._p.plan_b)
        fallos = self._aplicar(sesion, archivo)
        if self._sin_cupo(fallos) and not self._p.plan_b and definicion.config_plan_b:
            self._salida(f"la licencia no admite todas las politicas de {archivo}; aplico el plan B")
            archivo = definicion.config_plan_b
            fallos = self._aplicar(sesion, archivo)
        for f in fallos:
            self._salida(f"rechazada: {f}")
        if fallos:
            raise ErrorConsola(f"FortiOS rechazo {len(fallos)} linea(s) de {archivo}; el resto se aplico. Corrige y vuelve a pegar.")
        self._salida("hecho. Verifica con: get system status / show system interface")

    def _abrir(self, nombre: str) -> SesionFortigate:
        if nombre not in self._p.nodos:
            raise ErrorTopologia(f"{nombre} no tiene archivo en nodos/")
        nodo = self._gns3.nodos(self._gns3.abrir_proyecto()).get(nombre)
        if nodo is None:
            raise ErrorEstado(f"{nombre} no existe en el proyecto. Corre: gns3ctl.py construir")
        if not nodo.encendido:
            raise ErrorEstado(f"{nombre} no esta encendido. Corre: gns3ctl.py iniciar y espera 2 a 3 minutos.")
        sesion = self._abrir_sesion(nodo.console)
        if not sesion.iniciar():
            raise ErrorConsola(f"No llegue al prompt de {nombre}. Espera a que termine de arrancar y reintenta.")
        self._destino = f"{nombre} (consola {nodo.console})"
        return sesion

    def _aplicar(self, sesion: SesionFortigate, archivo: str) -> list[str]:
        self._salida(f"usando {archivo}")
        lineas = [l.rstrip() for l in self._repo.leer(archivo).splitlines() if l.strip() and not l.lstrip().startswith("#")]
        self._salida(f"pegando {len(lineas)} lineas en {self._destino}")
        return [f for f in sesion.pegar(lineas) if not _VIP_EN_USO.search(f)]

    @staticmethod
    def _sin_cupo(fallos: list[str]) -> bool:
        return any(_SIN_CUPO in f.lower() for f in fallos)
