"""fortigate: pega la configuracion del FortiGate por su consola telnet."""
from __future__ import annotations

from typing import Callable

from ..errores import ErrorConsola, ErrorEstado, ErrorTopologia
from ..fortigate_cli import SesionFortigate
from ..gns3 import ClienteGns3
from ..modelo import Proyecto
from ..repositorio import Repositorio


class PegadorConfigFortigate:
    def __init__(self, gns3: ClienteGns3, proyecto: Proyecto, repositorio: Repositorio,
                 abrir_sesion: Callable[[int], SesionFortigate], salida: Callable[[str], None]):
        self._gns3 = gns3
        self._p = proyecto
        self._repo = repositorio
        self._abrir_sesion = abrir_sesion
        self._salida = salida

    def pegar(self, equipo: str | None = None) -> None:
        nombre = equipo or self._p.fortigate_requerido().nodo
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
        archivo = self._p.nodos[nombre].config_para(self._p.plan_b)
        self._salida(f"usando {archivo}")
        lineas = [l.rstrip() for l in self._repo.leer(archivo).splitlines() if l.strip() and not l.lstrip().startswith("#")]
        self._salida(f"pegando {len(lineas)} lineas en {nombre} (consola {nodo.console})")
        sesion.pegar(lineas)
        self._salida("hecho. Verifica con: get system status / show system interface")
