"""Raiz de composicion: el unico lugar que decide que adaptadores reales usa cada servicio.

Los comandos piden aca el servicio que necesitan y no saben de HTTP, telnet ni SSH. Las pruebas arman una
Aplicacion con transporte, conexion, canal y reloj falsos y ejercitan los mismos servicios.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Callable

from .consola import Conexion, ConexionTcp, Consola
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


@dataclass
class Aplicacion:
    repositorio: Repositorio
    reloj: Reloj
    salida: Callable[[str], None]
    fabrica_transporte: Callable[[str], Transporte]      # servidor -> transporte hacia la API de GNS3
    fabrica_conexion: Callable[[int], Conexion]          # puerto de consola -> conexion telnet
    fabrica_canal: Callable[[ConfigSsh], CanalVm]        # datos SSH -> canal hacia la VM
    tipos: RegistroTipos

    @classmethod
    def crear(cls, base: Path, salida: Callable[[str], None] = print) -> Aplicacion:
        """La aplicacion de verdad: disco, HTTP, telnet y SSH reales."""
        return cls(repositorio=Repositorio(base), reloj=RelojReal(), salida=salida,
                   fabrica_transporte=TransporteHttp, fabrica_conexion=ConexionTcp, fabrica_canal=CanalSsh,
                   tipos=registro_por_defecto())

    # datos que se cargan una sola vez

    @cached_property
    def proyecto(self) -> Proyecto:
        return self.repositorio.cargar()

    @cached_property
    def gns3(self) -> ClienteGns3:
        return ClienteGns3(self.fabrica_transporte(self.proyecto.servidor), self.proyecto.nombre)

    # servicios

    def validador(self) -> Validador:
        return Validador(self.proyecto, self.repositorio, self.tipos)

    def constructor(self) -> Constructor:
        return Constructor(self.gns3, self.proyecto, self.repositorio, self.tipos, self.validador(), self.salida)

    def ciclo(self) -> CicloVida:
        return CicloVida(self.gns3, self.salida)

    def posiciones(self) -> Posiciones:
        return Posiciones(self.gns3, self.proyecto, self.repositorio, self.salida)

    def imagenes(self) -> ConstructorImagenes:
        return ConstructorImagenes(self.gns3, self.proyecto, self.repositorio, self.fabrica_canal, self.salida)

    def pegador_fortigate(self) -> PegadorConfigFortigate:
        return PegadorConfigFortigate(self.gns3, self.proyecto, self.repositorio, self.abrir_sesion_fortigate, self.salida)

    def activador_licencia(self) -> ActivadorLicencia:
        secretos = AlmacenSecretos(self.repositorio.base / "secretos.yml", self.salida)
        return ActivadorLicencia(self.gns3, self.proyecto, secretos, self.tipos, self.abrir_sesion_fortigate,
                                 self.reloj, self.salida)

    def abrir_sesion_fortigate(self, puerto: int) -> SesionFortigate:
        return SesionFortigate(Consola(self.fabrica_conexion(puerto), self.reloj), self.proyecto.fortigate_requerido(), self.reloj)
