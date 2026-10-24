from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, ClassVar, Iterable

from .. import hosts_md
from ..errores import ErrorTopologia
from ..gns3 import Archivo, ClienteGns3, NodoGns3
from ..modelo import Nodo, Proyecto, Puerto
from ..repositorio import Repositorio

if TYPE_CHECKING:
    from ..entorno import Entorno


@dataclass
class ContextoPreparacion:
    pid: str
    entorno: Entorno
    avisos: list[str] = field(default_factory=list)
    _redes: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def gns3(self) -> ClienteGns3:
        return self.entorno.gns3

    @property
    def proyecto(self) -> Proyecto:
        return self.entorno.proyecto

    @property
    def repositorio(self) -> Repositorio:
        return self.entorno.repositorio

    @property
    def salida(self) -> Callable[[str], None]:
        return self.entorno.salida

    def escribir(self, creado: NodoGns3, ruta: str, contenido: bytes) -> None:
        self.gns3.escribir_archivo(self.pid, creado.node_id, Archivo(ruta, contenido))

    def bloque_red(self, ruta: str, equipo: str) -> str | None:
        if ruta not in self._redes:
            self._redes[ruta] = hosts_md.bloques(self.repositorio.leer(ruta))
        return self._redes[ruta].get(equipo)


class TipoNodo(ABC):
    clave: ClassVar[str]
    ejemplo: ClassVar[str]
    descripcion: ClassVar[str]

    @abstractmethod
    def puerto(self, nombre: str) -> Puerto:
        pass

    def preparar(self, ctx: ContextoPreparacion, nodo: Nodo, creado: NodoGns3) -> None:
        pass

    def puerto_invalido(self, nombre: str) -> ErrorTopologia:
        return ErrorTopologia(f"puerto '{nombre}' invalido para {self.descripcion} (se espera como {self.ejemplo})")


class RegistroTipos:
    def __init__(self, tipos: Iterable[TipoNodo]):
        self._por_clave = {t.clave: t for t in sorted(tipos, key=lambda t: t.clave)}

    def __contains__(self, clave: object) -> bool:
        return clave in self._por_clave

    def claves(self) -> list[str]:
        return list(self._por_clave)

    def obtener(self, clave: str) -> TipoNodo:
        if clave not in self._por_clave:
            raise ErrorTopologia(f"Tipo de nodo no soportado: {clave}. Hay modulos para: {', '.join(self._por_clave)}")
        return self._por_clave[clave]

    def puerto(self, clave: str, nombre: str) -> Puerto:
        return self.obtener(clave).puerto(nombre)
