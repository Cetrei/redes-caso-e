from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Callable

from .consola import Conexion, ConexionTcp, Consola
from .entorno import Entorno
from .fortigate_cli import SesionFortigate
from .gns3 import ClienteGns3, Transporte, TransporteHttp
from .modelo import ConfigSsh, Proyecto
from .reloj import Reloj, RelojReal
from .repositorio import Repositorio
from .secretos import AlmacenSecretos
from .servicios.ciclo import CicloVida
from .servicios.constructor import Constructor
from .servicios.fortigate import PegadorConfigFortigate
from .servicios.imagenes import ConstructorImagenes
from .servicios.licencia import ActivadorLicencia
from .servicios.posiciones import Posiciones
from .ssh import CanalSsh, CanalVm
from .tipos import RegistroTipos, registro_por_defecto
from .validacion import Validador


@dataclass(frozen=True)
class Adaptadores:
    reloj: Reloj
    salida: Callable[[str], None]
    fabrica_transporte: Callable[[str], Transporte]
    fabrica_conexion: Callable[[int], Conexion]
    fabrica_canal: Callable[[ConfigSsh], CanalVm]
    tipos: RegistroTipos

    @classmethod
    def reales(cls, salida: Callable[[str], None] = print) -> Adaptadores:
        return cls(RelojReal(), salida, TransporteHttp, ConexionTcp, CanalSsh, registro_por_defecto())


@dataclass
class Aplicacion:
    repositorio: Repositorio
    adaptadores: Adaptadores

    @classmethod
    def crear(cls, base: Path, salida: Callable[[str], None] = print) -> Aplicacion:
        return cls(Repositorio(base), Adaptadores.reales(salida))

    @property
    def salida(self) -> Callable[[str], None]:
        return self.adaptadores.salida

    @cached_property
    def proyecto(self) -> Proyecto:
        return self.repositorio.cargar()

    @cached_property
    def gns3(self) -> ClienteGns3:
        return ClienteGns3(self.adaptadores.fabrica_transporte(self.proyecto.servidor), self.proyecto.nombre)

    @cached_property
    def entorno(self) -> Entorno:
        a = self.adaptadores
        return Entorno(self.gns3, self.proyecto, self.repositorio, a.tipos, a.reloj, a.salida, self.abrir_sesion_fortigate)

    def validador(self) -> Validador:
        return Validador(self.proyecto, self.repositorio, self.adaptadores.tipos)

    def constructor(self) -> Constructor:
        return Constructor(self.entorno, self.validador())

    def ciclo(self) -> CicloVida:
        return CicloVida(self.entorno)

    def posiciones(self) -> Posiciones:
        return Posiciones(self.entorno)

    def imagenes(self) -> ConstructorImagenes:
        return ConstructorImagenes(self.entorno, self.adaptadores.fabrica_canal)

    def pegador_fortigate(self) -> PegadorConfigFortigate:
        return PegadorConfigFortigate(self.entorno)

    def activador_licencia(self) -> ActivadorLicencia:
        return ActivadorLicencia(self.entorno, AlmacenSecretos(self.repositorio.base / ".env", self.salida))

    def abrir_sesion_fortigate(self, puerto: int) -> SesionFortigate:
        a = self.adaptadores
        return SesionFortigate(Consola(a.fabrica_conexion(puerto), a.reloj), self.proyecto.fortigate_requerido(), a.reloj)
