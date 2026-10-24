from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Llamada:
    ruta: dict[str, str]
    cuerpo: Any = None
    crudo: bytes | None = None


class Gns3Falso:
    def __init__(self, plantillas: dict[str, str]):
        self._plantillas = {f"t{i}": {"template_id": f"t{i}", "name": n, "node_type": tipo}
                            for i, (n, tipo) in enumerate(plantillas.items())}
        self.proyectos: dict[str, dict] = {}
        self.nodos: dict[str, dict[str, dict]] = {}
        self.enlaces: dict[str, list[dict]] = {}
        self.archivos: dict[tuple[str, str, str], bytes] = {}
        self.plantillas_creadas: list[dict] = []
        self.llamadas: list[tuple[str, str, object]] = []
        self._n = 0
        self._rutas = self._tabla_de_rutas()

    def _tabla_de_rutas(self) -> list[tuple[str, str, Any]]:
        p = r"/projects/(?P<pid>[^/]+)"
        return [
            ("GET", r"/projects", self._listar_proyectos),
            ("POST", r"/projects", self._crear_proyecto),
            ("POST", p + r"/open", lambda c: ""),
            ("DELETE", p, self._borrar_proyecto),
            ("GET", r"/templates", lambda c: list(self._plantillas.values())),
            ("POST", r"/templates", self._crear_plantilla),
            ("GET", p + r"/nodes", lambda c: list(self.nodos[c.ruta["pid"]].values())),
            ("POST", p + r"/templates/(?P<tid>[^/]+)", self._crear_nodo),
            ("PUT", p + r"/nodes/(?P<nid>[^/]+)", self._actualizar_nodo),
            ("DELETE", p + r"/nodes/(?P<nid>[^/]+)", lambda c: self.nodos[c.ruta["pid"]].pop(c.ruta["nid"])),
            ("POST", p + r"/nodes/(?P<accion>start|stop)", self._accion_todos),
            ("POST", p + r"/nodes/(?P<nid>[^/]+)/start", self._iniciar_nodo),
            ("POST", p + r"/nodes/(?P<nid>[^/]+)/files/(?P<archivo>.+)", self._archivo),
            ("GET", p + r"/links", lambda c: self.enlaces[c.ruta["pid"]]),
            ("POST", p + r"/links", self._enlace),
        ]

    def solicitar(self, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
        return self._despachar(metodo, ruta, Llamada({}, cuerpo=cuerpo))

    def subir(self, ruta: str, contenido: bytes) -> None:
        self._despachar("POST", ruta, Llamada({}, crudo=contenido))

    def _despachar(self, metodo: str, ruta: str, llamada: Llamada) -> Any:
        self.llamadas.append((metodo, ruta, llamada.cuerpo if llamada.cuerpo is not None else llamada.crudo))
        for m, patron, manejador in self._rutas:
            if m == metodo and (r := re.fullmatch(patron, ruta)):
                llamada.ruta = r.groupdict()
                return manejador(llamada)
        raise AssertionError(f"el GNS3 falso no conoce {metodo} {ruta}")

    def pid(self) -> str:
        return next(iter(self.proyectos))

    def nodo(self, nombre: str) -> dict:
        return next(n for n in self.nodos[self.pid()].values() if n["name"] == nombre)

    def nombres(self) -> list[str]:
        return sorted(n["name"] for n in self.nodos[self.pid()].values())

    def archivo(self, nombre: str, ruta: str) -> bytes:
        return self.archivos[(self.pid(), self.nodo(nombre)["node_id"], ruta)]

    def _id(self, prefijo: str) -> str:
        self._n += 1
        return f"{prefijo}{self._n}"

    def _listar_proyectos(self, c: Llamada) -> list[dict]:
        return [{"name": p["name"], "project_id": pid, "status": "opened"} for pid, p in self.proyectos.items()]

    def _crear_proyecto(self, c: Llamada) -> dict:
        pid = self._id("p")
        self.proyectos[pid] = {"name": c.cuerpo["name"]}
        self.nodos[pid], self.enlaces[pid] = {}, []
        return {"project_id": pid, "name": c.cuerpo["name"]}

    def _borrar_proyecto(self, c: Llamada) -> None:
        pid = c.ruta["pid"]
        del self.proyectos[pid], self.nodos[pid], self.enlaces[pid]

    def _crear_plantilla(self, c: Llamada) -> dict:
        self.plantillas_creadas.append(c.cuerpo)
        tid = self._id("t")
        self._plantillas[tid] = {"template_id": tid, "name": c.cuerpo["name"], "node_type": "docker"}
        return self._plantillas[tid]

    def _crear_nodo(self, c: Llamada) -> dict:
        plantilla = self._plantillas[c.ruta["tid"]]
        nid = self._id("n")
        nodo = {"node_id": nid, "name": plantilla["name"], "node_type": plantilla["node_type"], "status": "stopped",
                "x": c.cuerpo["x"], "y": c.cuerpo["y"], "console": 5000 + self._n, "console_host": "127.0.0.1",
                "properties": {"dynamips_id": self._n, "adapters": 8}}
        self.nodos[c.ruta["pid"]][nid] = nodo
        return dict(nodo)

    def _actualizar_nodo(self, c: Llamada) -> dict:
        nodo = self.nodos[c.ruta["pid"]][c.ruta["nid"]]
        for clave, valor in c.cuerpo.items():
            if clave == "properties":
                nodo["properties"].update(valor)
            else:
                nodo[clave] = valor
        return dict(nodo)

    def _accion_todos(self, c: Llamada) -> None:
        for nodo in self.nodos[c.ruta["pid"]].values():
            nodo["status"] = "started" if c.ruta["accion"] == "start" else "stopped"

    def _iniciar_nodo(self, c: Llamada) -> None:
        self.nodos[c.ruta["pid"]][c.ruta["nid"]]["status"] = "started"

    def _archivo(self, c: Llamada) -> None:
        self.archivos[(c.ruta["pid"], c.ruta["nid"], c.ruta["archivo"])] = c.crudo

    def _enlace(self, c: Llamada) -> None:
        self.enlaces[c.ruta["pid"]].append({"link_id": self._id("l"), "nodes": c.cuerpo["nodes"]})
