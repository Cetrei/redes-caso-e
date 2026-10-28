from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from maqueta.datos.anotaciones import leer_notas, leer_zonas
from maqueta.nucleo.errores import ErrorTopologia
from maqueta.nucleo.modelo import ConfigFortigate, ConfigSsh, Enlace, Imagen, Nodo, Proyecto, PuertoSwitch


def _entero(valor: Any) -> int | None:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def _texto(valor: Any) -> str | None:
    return None if valor is None else str(valor)


def _mapa_texto(valor: Any, clave: str) -> dict[str, str]:
    if valor is None:
        return {}
    if not isinstance(valor, dict):
        raise ErrorTopologia(f"proyecto.yml > {clave}: debe ser un mapa")
    return {str(k): str(v) for k, v in valor.items()}


def _seccion(datos: dict, clave: str, campos: tuple[str, ...]) -> dict | None:
    valor = datos.get(clave)
    if valor is None:
        return None
    if not isinstance(valor, dict):
        raise ErrorTopologia(f"proyecto.yml > {clave}: debe ser un mapa")
    for campo in campos:
        if campo not in valor:
            raise ErrorTopologia(f"proyecto.yml > {clave}: falta '{campo}'")
    return valor


class Repositorio:
    def __init__(self, base: Path):
        self.base = base
        self.raiz = base.parent
        self._dir = base / "topologia"

    @property
    def servicios(self) -> Path:
        return self.raiz / "servicios"

    def existe(self, ruta: str) -> bool:
        return (self.raiz / ruta).exists()

    def leer(self, ruta: str) -> str:
        try:
            return (self.raiz / ruta).read_text(encoding="utf-8")
        except OSError as e:
            raise ErrorTopologia(f"no pude leer {ruta}: {e.strerror or e}") from e

    def cargar(self) -> Proyecto:
        datos = self._datos_proyecto()
        return Proyecto(
            nombre=str(datos["proyecto"]),
            servidor=str(datos["servidor"]),
            plan_b=bool(datos.get("plan_b", False)),
            plantillas=_mapa_texto(datos.get("plantillas"), "plantillas"),
            tipos=_mapa_texto(datos.get("tipos"), "tipos"),
            dynamips_slots=_mapa_texto(datos.get("dynamips_slots"), "dynamips_slots"),
            fortigate=self._fortigate(datos),
            imagenes=self._imagenes(datos),
            ssh=self._ssh(datos),
            nodos={n.nombre: n for n in self._nodos()},
            enlaces=tuple(self._enlaces()),
            zonas=leer_zonas(self._opcional("zonas.yml")),
            notas=leer_notas(self._opcional("notas.yml")),
        )

    def actualizar_posicion(self, nombre: str, x: int, y: int) -> None:
        ruta = self._dir / "nodos" / f"{nombre}.yml"
        texto = ruta.read_text(encoding="utf-8")
        texto = re.sub(r"(?m)^x: .*$", f"x: {x}", texto, count=1)
        texto = re.sub(r"(?m)^y: .*$", f"y: {y}", texto, count=1)
        ruta.write_text(texto, encoding="utf-8", newline="\n")

    def _opcional(self, nombre: str) -> Any:
        ruta = self._dir / nombre
        return self._yaml(ruta) if ruta.exists() else None

    def _datos_proyecto(self) -> dict:
        ruta = self._dir / "proyecto.yml"
        if not ruta.exists():
            raise ErrorTopologia(f"Falta {ruta}")
        datos = self._yaml(ruta) or {}
        if not isinstance(datos, dict):
            raise ErrorTopologia("proyecto.yml: debe ser un mapa")
        for clave in ("proyecto", "servidor"):
            if not datos.get(clave):
                raise ErrorTopologia(f"proyecto.yml: falta '{clave}'")
        return datos

    @staticmethod
    def _fortigate(datos: dict) -> ConfigFortigate | None:
        fg = _seccion(datos, "fortigate", ("nodo", "usuario", "clave"))
        if fg is None:
            return None
        return ConfigFortigate(nodo=str(fg["nodo"]), usuario=str(fg["usuario"]), clave=str(fg["clave"]),
                               puerto_internet=str(fg.get("puerto_internet", "port4")))

    @staticmethod
    def _ssh(datos: dict) -> ConfigSsh | None:
        ssh = _seccion(datos, "ssh", ("host", "puerto", "usuario", "clave"))
        if ssh is None:
            return None
        return ConfigSsh(host=str(ssh["host"]), puerto=int(ssh["puerto"]), usuario=str(ssh["usuario"]), clave=str(ssh["clave"]))

    def _imagenes(self, datos: dict) -> tuple[Imagen, ...]:
        imagenes = datos.get("imagenes") or []
        if not isinstance(imagenes, list):
            raise ErrorTopologia("proyecto.yml > imagenes: debe ser una lista")
        return tuple(self._imagen(i) for i in imagenes)

    def _yaml(self, ruta: Path) -> Any:
        try:
            return yaml.safe_load(ruta.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ErrorTopologia(f"{ruta.relative_to(self.raiz)}: YAML invalido: {e}") from e

    @staticmethod
    def _imagen(d: Any) -> Imagen:
        if not isinstance(d, dict) or not {"etiqueta", "ruta", "plantilla"} <= d.keys():
            raise ErrorTopologia(f"proyecto.yml > imagenes: cada una necesita etiqueta, ruta y plantilla, no {d!r}")
        return Imagen(str(d["etiqueta"]), str(d["ruta"]), str(d["plantilla"]), str(d.get("consola", "telnet")))

    def _nodos(self) -> list[Nodo]:
        return [self._nodo(f) for f in sorted((self._dir / "nodos").glob("*.yml"))]

    def _nodo(self, archivo: Path) -> Nodo:
        d = self._yaml(archivo) or {}
        if not isinstance(d, dict):
            raise ErrorTopologia(f"nodos/{archivo.name}: debe ser un mapa con plantilla, x, y...")
        puertos = d.get("puertos") or []
        if not isinstance(puertos, list):
            raise ErrorTopologia(f"nodos/{archivo.name}: 'puertos' debe ser una lista")
        return Nodo(
            nombre=archivo.stem,
            plantilla=_texto(d.get("plantilla")),
            x=_entero(d.get("x")),
            y=_entero(d.get("y")),
            config=_texto(d.get("config")),
            config_plan_b=_texto(d.get("config_plan_b")),
            red=_texto(d.get("red")),
            puertos=tuple(self._puerto_switch(archivo, i, p) for i, p in enumerate(puertos)),
        )

    @staticmethod
    def _puerto_switch(archivo: Path, i: int, p: Any) -> PuertoSwitch:
        if not isinstance(p, dict) or _entero(p.get("n")) is None or _entero(p.get("vlan")) is None or "tipo" not in p:
            raise ErrorTopologia(f"nodos/{archivo.name}: puertos[{i}] debe ser {{n, tipo, vlan}}, no {p!r}")
        return PuertoSwitch(p["n"], str(p["tipo"]), p["vlan"])

    def _enlaces(self) -> list[Enlace]:
        res = []
        for f in sorted((self._dir / "enlaces").glob("*.yml")):
            lista = self._yaml(f) or []
            for cable in lista if isinstance(lista, list) else [lista]:
                if not (isinstance(cable, list) and len(cable) == 4):
                    raise ErrorTopologia(f"enlaces/{f.name}: cada cable es [equipo, puerto, equipo, puerto], no {cable!r}")
                res.append(Enlace(*(str(x) for x in cable)))
        return res
