from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, NamedTuple, Protocol
from xml.sax.saxutils import unescape

from maqueta.nucleo.dibujo import Dibujo
from maqueta.nucleo.errores import ErrorGns3
from maqueta.nucleo.modelo import Puerto

_MARCA = re.compile(r"""data-maqueta=(["'])(.*?)\1""")
_ENTIDADES = {"&quot;": '"', "&apos;": "'"}


class Transporte(Protocol):
    def solicitar(self, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
        ...

    def subir(self, ruta: str, contenido: bytes) -> None:
        ...


class TransporteHttp:
    def __init__(self, servidor: str, timeout: float = 120.0):
        self._api = servidor.rstrip("/") + "/v2"
        self._timeout = timeout

    def solicitar(self, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
        datos = None if cuerpo is None else json.dumps(cuerpo).encode()
        req = urllib.request.Request(self._api + ruta, data=datos, method=metodo)
        if datos is not None:
            req.add_header("Content-Type", "application/json")
        return self._enviar(req)

    def subir(self, ruta: str, contenido: bytes) -> None:
        self._enviar(urllib.request.Request(self._api + ruta, data=contenido, method="POST"))

    def _enviar(self, req: urllib.request.Request) -> Any:
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as r:
                texto = r.read().decode()
                return json.loads(texto) if texto and texto.lstrip()[0] in "[{" else texto
        except urllib.error.HTTPError as e:
            raise ErrorGns3(f"ERROR {e.code} en {req.get_method()} {req.selector}: {e.read().decode()[:1500]}") from e
        except urllib.error.URLError as e:
            raise ErrorGns3(f"No hay conexion con {self._api}: {e.reason}. Enciende la VM de GNS3 y espera a que ese puerto responda") from e


class Extremo(NamedTuple):
    node_id: str
    adaptador: int
    numero: int


@dataclass(frozen=True)
class NuevoNodo:
    plantilla: str
    nombre: str
    x: int
    y: int


@dataclass(frozen=True)
class Archivo:
    ruta: str
    contenido: bytes


@dataclass(frozen=True)
class NodoGns3:
    node_id: str
    nombre: str
    tipo: str
    estado: str
    x: int
    y: int
    console: int | None
    console_host: str
    propiedades: Mapping[str, Any]
    tipo_consola: str = ""

    @classmethod
    def desde_json(cls, d: Mapping[str, Any]) -> NodoGns3:
        return cls(
            node_id=d["node_id"], nombre=d["name"], tipo=d["node_type"], estado=d.get("status", ""),
            x=d.get("x", 0), y=d.get("y", 0), console=d.get("console"), console_host=d.get("console_host") or "",
            propiedades=MappingProxyType(dict(d.get("properties") or {})), tipo_consola=d.get("console_type") or "")

    @property
    def consola_texto(self) -> int | None:
        aux = self.propiedades.get("aux")
        if self.tipo_consola == "vnc" and aux:
            return aux
        return self.console

    @property
    def encendido(self) -> bool:
        return self.estado == "started"


@dataclass(frozen=True)
class DibujoGns3:
    drawing_id: str
    clave: str | None
    svg: str
    x: int
    y: int
    z: int

    @classmethod
    def desde_json(cls, d: Mapping[str, Any]) -> DibujoGns3:
        svg = d.get("svg") or ""
        marca = _MARCA.search(svg)
        clave = unescape(marca.group(2), _ENTIDADES) if marca else None
        return cls(d["drawing_id"], clave, svg, d.get("x", 0), d.get("y", 0), d.get("z", 0))

    def difiere(self, otro: Dibujo) -> bool:
        return (self.svg, self.x, self.y, self.z) != (otro.svg, otro.x, otro.y, otro.z)


def _cuerpo_dibujo(d: Dibujo) -> dict[str, Any]:
    return {"svg": d.svg, "x": d.x, "y": d.y, "z": d.z}


class ClienteGns3:
    def __init__(self, transporte: Transporte, nombre_proyecto: str):
        self._t = transporte
        self._nombre = nombre_proyecto

    def abrir_proyecto(self, crear: bool = False) -> str:
        for p in self._t.solicitar("GET", "/projects"):
            if p["name"] == self._nombre:
                if p["status"] != "opened":
                    self._t.solicitar("POST", f"/projects/{p['project_id']}/open")
                return p["project_id"]
        if not crear:
            raise ErrorGns3(f"El proyecto {self._nombre} no existe. Corre: gns3ctl.py construir")
        return self._t.solicitar("POST", "/projects", cuerpo={"name": self._nombre})["project_id"]

    def borrar_proyecto(self, pid: str) -> None:
        self._t.solicitar("DELETE", f"/projects/{pid}")

    def plantillas(self) -> set[str]:
        return {t["name"] for t in self._t.solicitar("GET", "/templates")}

    def plantilla_id(self, nombre: str) -> str:
        for t in self._t.solicitar("GET", "/templates"):
            if t["name"] == nombre:
                return t["template_id"]
        raise ErrorGns3(f"No existe la plantilla '{nombre}' en el servidor.")

    def crear_plantilla_docker(self, nombre: str, imagen: str, consola: str = "telnet") -> None:
        self._t.solicitar("POST", "/templates", cuerpo={
            "name": nombre, "template_type": "docker", "image": imagen, "adapters": 1, "console_type": consola,
            "start_command": "", "compute_id": "local", "category": "guest", "symbol": ":/symbols/docker_guest.svg"})

    def nodos(self, pid: str) -> dict[str, NodoGns3]:
        return {n["name"]: NodoGns3.desde_json(n) for n in self._t.solicitar("GET", f"/projects/{pid}/nodes")}

    def crear_nodo(self, pid: str, nuevo: NuevoNodo) -> NodoGns3:
        tid = self.plantilla_id(nuevo.plantilla)
        n = self._t.solicitar("POST", f"/projects/{pid}/templates/{tid}", {"x": nuevo.x, "y": nuevo.y, "compute_id": "local"})
        self._t.solicitar("PUT", f"/projects/{pid}/nodes/{n['node_id']}", {"name": nuevo.nombre})
        return NodoGns3.desde_json({**n, "name": nuevo.nombre})

    def actualizar_nodo(self, pid: str, node_id: str, campos: Mapping[str, Any]) -> None:
        self._t.solicitar("PUT", f"/projects/{pid}/nodes/{node_id}", cuerpo=dict(campos))

    def escribir_archivo(self, pid: str, node_id: str, archivo: Archivo) -> None:
        self._t.subir(f"/projects/{pid}/nodes/{node_id}/files/{archivo.ruta}", archivo.contenido)

    def iniciar_nodo(self, pid: str, node_id: str) -> None:
        self._t.solicitar("POST", f"/projects/{pid}/nodes/{node_id}/start", cuerpo={})

    def borrar_nodo(self, pid: str, node_id: str) -> None:
        self._t.solicitar("DELETE", f"/projects/{pid}/nodes/{node_id}")

    def accion_nodos(self, pid: str, accion: str) -> None:
        self._t.solicitar("POST", f"/projects/{pid}/nodes/{accion}", cuerpo={})

    def enlaces(self, pid: str) -> set[frozenset[Extremo]]:
        return {frozenset(Extremo(n["node_id"], n["adapter_number"], n["port_number"]) for n in l["nodes"])
                for l in self._t.solicitar("GET", f"/projects/{pid}/links")}

    def conectar(self, pid: str, a: tuple[str, Puerto], b: tuple[str, Puerto]) -> None:
        self._t.solicitar("POST", f"/projects/{pid}/links", cuerpo={"nodes": [
            {"node_id": nid, "adapter_number": p.adaptador, "port_number": p.numero} for nid, p in (a, b)]})

    def dibujos(self, pid: str) -> list[DibujoGns3]:
        return [DibujoGns3.desde_json(d) for d in self._t.solicitar("GET", f"/projects/{pid}/drawings")]

    def crear_dibujo(self, pid: str, dibujo: Dibujo) -> None:
        self._t.solicitar("POST", f"/projects/{pid}/drawings", cuerpo=_cuerpo_dibujo(dibujo))

    def actualizar_dibujo(self, pid: str, drawing_id: str, dibujo: Dibujo) -> None:
        self._t.solicitar("PUT", f"/projects/{pid}/drawings/{drawing_id}", cuerpo=_cuerpo_dibujo(dibujo))

    def borrar_dibujo(self, pid: str, drawing_id: str) -> None:
        self._t.solicitar("DELETE", f"/projects/{pid}/drawings/{drawing_id}")
