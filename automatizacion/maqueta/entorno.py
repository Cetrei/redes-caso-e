"""Lo que comparten todos los servicios: los bordes ya conectados y los datos cargados una sola vez.

Un servicio recibe un `Entorno` en vez de una lista de piezas sueltas. Asi su constructor queda en uno o dos
argumentos, y agregar un borde nuevo no obliga a tocar la firma de cada servicio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .fortigate_cli import SesionFortigate
from .gns3 import ClienteGns3
from .modelo import Proyecto
from .reloj import Reloj
from .repositorio import Repositorio
from .tipos import RegistroTipos


@dataclass(frozen=True)
class Entorno:
    gns3: ClienteGns3
    proyecto: Proyecto
    repositorio: Repositorio
    tipos: RegistroTipos
    reloj: Reloj
    salida: Callable[[str], None]
    sesion_fortigate: Callable[[int], SesionFortigate]      # puerto de consola -> sesion ya conectada
