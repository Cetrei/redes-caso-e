"""Cliente de la API REST de GNS3 2.2.

Dos piezas: `Transporte`, que es el seam con la red (el real habla HTTP, las pruebas usan uno en memoria),
y `ClienteGns3`, que traduce el vocabulario de la maqueta (proyecto, nodo, cable) a llamadas REST y las
respuestas JSON a `NodoGns3`. Ningun otro modulo conoce rutas ni JSON de la API.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, NamedTuple, Protocol

from .errores import ErrorGns3
from .modelo import Puerto


class Transporte(Protocol):
    def solicitar(self, metodo: str, ruta: str, *, cuerpo: Any = None, crudo: bytes | None = None) -> Any:
        """Una llamada a la API. `cuerpo` se envia como JSON, `crudo` tal cual. Devuelve el JSON o el texto de la respuesta."""
        ...


class TransporteHttp:
    def __init__(self, servidor: str, timeout: float = 120.0):
        self._api = servidor.rstrip("/") + "/v2"
        self._timeout = timeout

    def solicitar(self, metodo: str, ruta: str, *, cuerpo: Any = None, crudo: bytes | None = None) -> Any:
        datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
        req = urllib.request.Request(self._api + ruta, data=datos, method=metodo)
        if datos is not None and crudo is None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as r:
                texto = r.read().decode()
                return json.loads(texto) if texto and texto.lstrip()[0] in "[{" else texto
        except urllib.error.HTTPError as e:
            raise ErrorGns3(f"ERROR {e.code} en {metodo} {ruta}: {e.read().decode()[:1500]}") from e
        except urllib.error.URLError as e:
            raise ErrorGns3(f"No hay conexion con {self._api}: {e.reason}. Arranca la VM con gns3vm/start-gns3vm.sh") from e


class Extremo(NamedTuple):
    """Un lado de un cable en GNS3."""

    node_id: str
    adaptador: int
    numero: int


@dataclass(frozen=True)
class NodoGns3:
    """Un nodo tal como existe en el proyecto de GNS3."""

    node_id: str
    nombre: str
    tipo: str
    estado: str
    x: int
    y: int
    console: int | None
    console_host: str
    propiedades: Mapping[str, Any]

    @classmethod
    def desde_json(cls, d: Mapping[str, Any]) -> NodoGns3:
        return cls(
            node_id=d["node_id"], nombre=d["name"], tipo=d["node_type"], estado=d.get("status", ""),
            x=d.get("x", 0), y=d.get("y", 0), console=d.get("console"), console_host=d.get("console_host") or "",
            propiedades=MappingProxyType(dict(d.get("properties") or {})))

    @property
    def encendido(self) -> bool:
        return self.estado == "started"


class ClienteGns3:
    """Operaciones sobre un proyecto de GNS3 identificado por su nombre."""

    def __init__(self, transporte: Transporte, nombre_proyecto: str):
        self._t = transporte
        self._nombre = nombre_proyecto

    # proyecto

    def abrir_proyecto(self, crear: bool = False) -> str:
        """Devuelve el id del proyecto, abriendolo si estaba cerrado. Con `crear` lo crea si no existe."""
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

    # plantillas

    def plantillas(self) -> set[str]:
        return {t["name"] for t in self._t.solicitar("GET", "/templates")}

    def plantilla_id(self, nombre: str) -> str:
        for t in self._t.solicitar("GET", "/templates"):
            if t["name"] == nombre:
                return t["template_id"]
        raise ErrorGns3(f"No existe la plantilla '{nombre}' en el servidor.")

    def crear_plantilla_docker(self, nombre: str, imagen: str) -> None:
        self._t.solicitar("POST", "/templates", cuerpo={
            "name": nombre, "template_type": "docker", "image": imagen, "adapters": 1, "console_type": "telnet",
            "start_command": "", "compute_id": "local", "category": "guest", "symbol": ":/symbols/docker_guest.svg"})

    # nodos

    def nodos(self, pid: str) -> dict[str, NodoGns3]:
        return {n["name"]: NodoGns3.desde_json(n) for n in self._t.solicitar("GET", f"/projects/{pid}/nodes")}

    def crear_nodo(self, pid: str, plantilla: str, nombre: str, x: int, y: int) -> NodoGns3:
        """Crea un nodo desde una plantilla (por nombre) y le pone su nombre."""
        tid = self.plantilla_id(plantilla)
        n = self._t.solicitar("POST", f"/projects/{pid}/templates/{tid}", cuerpo={"x": x, "y": y, "compute_id": "local"})
        self._t.solicitar("PUT", f"/projects/{pid}/nodes/{n['node_id']}", cuerpo={"name": nombre})
        return NodoGns3.desde_json({**n, "name": nombre})

    def actualizar_nodo(self, pid: str, node_id: str, campos: Mapping[str, Any]) -> None:
        self._t.solicitar("PUT", f"/projects/{pid}/nodes/{node_id}", cuerpo=dict(campos))

    def escribir_archivo(self, pid: str, node_id: str, ruta: str, contenido: bytes) -> None:
        """Escribe un archivo dentro del nodo (startup-config de un router, interfaces de un contenedor)."""
        self._t.solicitar("POST", f"/projects/{pid}/nodes/{node_id}/files/{ruta}", crudo=contenido)

    def iniciar_nodo(self, pid: str, node_id: str) -> None:
        self._t.solicitar("POST", f"/projects/{pid}/nodes/{node_id}/start", cuerpo={})

    def borrar_nodo(self, pid: str, node_id: str) -> None:
        self._t.solicitar("DELETE", f"/projects/{pid}/nodes/{node_id}")

    def accion_nodos(self, pid: str, accion: str) -> None:
        """`start` o `stop` sobre todos los nodos del proyecto."""
        self._t.solicitar("POST", f"/projects/{pid}/nodes/{accion}", cuerpo={})

    # cables

    def enlaces(self, pid: str) -> set[frozenset[Extremo]]:
        return {frozenset(Extremo(n["node_id"], n["adapter_number"], n["port_number"]) for n in l["nodes"])
                for l in self._t.solicitar("GET", f"/projects/{pid}/links")}

    def conectar(self, pid: str, a: tuple[str, Puerto], b: tuple[str, Puerto]) -> None:
        self._t.solicitar("POST", f"/projects/{pid}/links", cuerpo={"nodes": [
            {"node_id": nid, "adapter_number": p.adaptador, "port_number": p.numero} for nid, p in (a, b)]})
