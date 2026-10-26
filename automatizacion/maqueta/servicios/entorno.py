from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from maqueta.bordes.fortigate_cli import SesionFortigate
from maqueta.bordes.gns3 import ClienteGns3
from maqueta.bordes.reloj import Reloj
from maqueta.datos.repositorio import Repositorio
from maqueta.nucleo.modelo import Proyecto
from maqueta.tipos import RegistroTipos


@dataclass(frozen=True)
class Entorno:
    gns3: ClienteGns3
    proyecto: Proyecto
    repositorio: Repositorio
    tipos: RegistroTipos
    reloj: Reloj
    salida: Callable[[str], None]
    sesion_fortigate: Callable[[int], SesionFortigate]
