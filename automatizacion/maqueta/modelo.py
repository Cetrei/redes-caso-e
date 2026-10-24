"""Modelo de dominio: la topologia de la maqueta como datos inmutables, sin YAML ni GNS3 de por medio.

Los valores que `repositorio` no pudo interpretar (una coordenada que no es entero, por ejemplo) quedan
en None: decidir si eso es un error es trabajo de `validacion`, no del modelo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, NamedTuple

from .errores import ErrorTopologia


class Puerto(NamedTuple):
    """Puerto de un nodo de GNS3: adaptador y numero de puerto dentro del adaptador."""

    adaptador: int
    numero: int


@dataclass(frozen=True)
class PuertoSwitch:
    """Modo y VLAN de un puerto de un switch Ethernet de GNS3."""

    n: int
    tipo: str
    vlan: int


@dataclass(frozen=True)
class Nodo:
    """Un equipo de la maqueta tal como lo describe su archivo de topologia/nodos/."""

    nombre: str
    plantilla: str | None
    x: int | None
    y: int | None
    config: str | None = None
    config_plan_b: str | None = None
    red: str | None = None
    puertos: tuple[PuertoSwitch, ...] = ()

    @property
    def archivo(self) -> str:
        return f"nodos/{self.nombre}.yml"

    @property
    def posicion(self) -> tuple[int | None, int | None]:
        return (self.x, self.y)

    def config_para(self, plan_b: bool) -> str:
        """Ruta de la config a usar: la del plan B si esta activo y el nodo la define, si no la normal."""
        elegida = self.config_plan_b if plan_b and self.config_plan_b else self.config
        if not elegida:
            raise ErrorTopologia(f"{self.archivo}: falta 'config'")
        return elegida


@dataclass(frozen=True)
class Enlace:
    """Un cable entre dos puertos, con los nombres de puerto de la especificacion (Gi0/1, port2, eth0, p1)."""

    a: str
    puerto_a: str
    b: str
    puerto_b: str

    @property
    def extremos(self) -> tuple[tuple[str, str], tuple[str, str]]:
        return ((self.a, self.puerto_a), (self.b, self.puerto_b))

    def __str__(self) -> str:
        return f"{self.a} {self.puerto_a} <-> {self.b} {self.puerto_b}"


@dataclass(frozen=True)
class ConfigFortigate:
    """Acceso al CLI del FortiGate (comandos `fortigate` y `licenciar`)."""

    nodo: str
    usuario: str
    clave: str
    puerto_internet: str = "port4"


@dataclass(frozen=True)
class Imagen:
    """Imagen Docker que `imagen` construye en la VM y la plantilla de GNS3 que crea con ella."""

    etiqueta: str
    ruta: str
    plantilla: str


@dataclass(frozen=True)
class ConfigSsh:
    """SSH a la VM de GNS3 (solo para construir imagenes)."""

    host: str
    puerto: int
    usuario: str
    clave: str


@dataclass(frozen=True, eq=False)
class Proyecto:
    """Todo topologia/ ya cargado: parametros globales, equipos y cables."""

    nombre: str
    servidor: str
    plan_b: bool = False
    plantillas: Mapping[str, str] = field(default_factory=dict)     # alias -> nombre de plantilla en GNS3
    tipos: Mapping[str, str] = field(default_factory=dict)          # alias -> clave de tipo de nodo
    dynamips_slots: Mapping[str, str] = field(default_factory=dict)
    fortigate: ConfigFortigate | None = None
    imagenes: tuple[Imagen, ...] = ()
    ssh: ConfigSsh | None = None
    nodos: Mapping[str, Nodo] = field(default_factory=dict)
    enlaces: tuple[Enlace, ...] = ()

    def __post_init__(self) -> None:
        for campo in ("plantillas", "tipos", "dynamips_slots", "nodos"):
            object.__setattr__(self, campo, MappingProxyType(dict(getattr(self, campo))))

    def tipo_de(self, nodo: Nodo) -> str | None:
        """Clave del tipo de nodo que proyecto.yml declara para la plantilla del equipo, si la declara."""
        return self.tipos.get(nodo.plantilla)

    def plantilla_gns3(self, nodo: Nodo) -> str:
        """Nombre de la plantilla de GNS3 con la que se crea el equipo."""
        return self.plantillas[nodo.plantilla]

    def fortigate_requerido(self) -> ConfigFortigate:
        if self.fortigate is None:
            raise ErrorTopologia("proyecto.yml: falta la seccion 'fortigate'")
        return self.fortigate

    def ssh_requerido(self) -> ConfigSsh:
        if self.ssh is None:
            raise ErrorTopologia("proyecto.yml: falta la seccion 'ssh'")
        return self.ssh
