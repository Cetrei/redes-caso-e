from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, NamedTuple

from maqueta.nucleo.errores import ErrorTopologia


class Puerto(NamedTuple):
    adaptador: int
    numero: int


@dataclass(frozen=True)
class PuertoSwitch:
    n: int
    tipo: str
    vlan: int


@dataclass(frozen=True)
class Nodo:
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
        elegida = self.config_plan_b if plan_b and self.config_plan_b else self.config
        if not elegida:
            raise ErrorTopologia(f"{self.archivo}: falta 'config'")
        return elegida


@dataclass(frozen=True)
class Enlace:
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
class Zona:
    nombre: str
    x: int
    y: int
    ancho: int
    alto: int
    tono: str
    lineas: tuple[str, ...] = ()


@dataclass(frozen=True)
class Nota:
    texto: str
    x: int
    y: int
    tono: str = "neutro"
    ancho: int | None = None
    alto: int | None = None
    tam: int = 10
    negrita: bool = False


@dataclass(frozen=True)
class ConfigFortigate:
    nodo: str
    usuario: str
    clave: str
    puerto_internet: str = "port4"


@dataclass(frozen=True)
class Imagen:
    etiqueta: str
    ruta: str
    plantilla: str
    consola: str = "telnet"


@dataclass(frozen=True)
class ConfigSsh:
    host: str
    puerto: int
    usuario: str
    clave: str


@dataclass(frozen=True, eq=False)
class Proyecto:
    nombre: str
    servidor: str
    plan_b: bool = False
    plantillas: Mapping[str, str] = field(default_factory=dict)
    tipos: Mapping[str, str] = field(default_factory=dict)
    dynamips_slots: Mapping[str, str] = field(default_factory=dict)
    fortigate: ConfigFortigate | None = None
    imagenes: tuple[Imagen, ...] = ()
    ssh: ConfigSsh | None = None
    nodos: Mapping[str, Nodo] = field(default_factory=dict)
    enlaces: tuple[Enlace, ...] = ()
    zonas: tuple[Zona, ...] = ()
    notas: tuple[Nota, ...] = ()

    def __post_init__(self) -> None:
        for campo in ("plantillas", "tipos", "dynamips_slots", "nodos"):
            object.__setattr__(self, campo, MappingProxyType(dict(getattr(self, campo))))

    def tipo_de(self, nodo: Nodo) -> str | None:
        return self.tipos.get(nodo.plantilla)

    def plantilla_gns3(self, nodo: Nodo) -> str:
        return self.plantillas[nodo.plantilla]

    def fortigate_requerido(self) -> ConfigFortigate:
        if self.fortigate is None:
            raise ErrorTopologia("proyecto.yml: falta la seccion 'fortigate'")
        return self.fortigate

    def ssh_requerido(self) -> ConfigSsh:
        if self.ssh is None:
            raise ErrorTopologia("proyecto.yml: falta la seccion 'ssh'")
        return self.ssh
