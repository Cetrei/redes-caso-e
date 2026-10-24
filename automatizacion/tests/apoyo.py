"""Dobles de prueba: un GNS3 en memoria, una consola de FortiGate con guion, un reloj que no espera y un
repo de juguete en una carpeta temporal. Son el segundo adaptador de cada seam del motor."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from maqueta.aplicacion import Aplicacion
from maqueta.errores import ErrorConexionConsola
from maqueta.repositorio import Repositorio
from maqueta.tipos import registro_por_defecto


class RelojFalso:
    """Dormir solo adelanta el reloj: una espera de 8 minutos dura microsegundos."""

    def __init__(self) -> None:
        self.t = 0.0

    def ahora(self) -> float:
        return self.t

    def dormir(self, segundos: float) -> None:
        self.t += segundos


class Gns3Falso:
    """Servidor GNS3 en memoria que entiende las llamadas REST que usa el motor."""

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
        self._rutas = [
            ("GET", r"/projects", self._listar_proyectos),
            ("POST", r"/projects", self._crear_proyecto),
            ("POST", r"/projects/(?P<pid>[^/]+)/open", self._abrir),
            ("DELETE", r"/projects/(?P<pid>[^/]+)", self._borrar_proyecto),
            ("GET", r"/templates", lambda **_: list(self._plantillas.values())),
            ("POST", r"/templates", self._crear_plantilla),
            ("GET", r"/projects/(?P<pid>[^/]+)/nodes", lambda pid, **_: list(self.nodos[pid].values())),
            ("POST", r"/projects/(?P<pid>[^/]+)/templates/(?P<tid>[^/]+)", self._crear_nodo),
            ("PUT", r"/projects/(?P<pid>[^/]+)/nodes/(?P<nid>[^/]+)", self._actualizar_nodo),
            ("DELETE", r"/projects/(?P<pid>[^/]+)/nodes/(?P<nid>[^/]+)", lambda pid, nid, **_: self.nodos[pid].pop(nid)),
            ("POST", r"/projects/(?P<pid>[^/]+)/nodes/(?P<accion>start|stop)", self._accion_todos),
            ("POST", r"/projects/(?P<pid>[^/]+)/nodes/(?P<nid>[^/]+)/start", self._iniciar_nodo),
            ("POST", r"/projects/(?P<pid>[^/]+)/nodes/(?P<nid>[^/]+)/files/(?P<ruta>.+)", self._archivo),
            ("GET", r"/projects/(?P<pid>[^/]+)/links", lambda pid, **_: self.enlaces[pid]),
            ("POST", r"/projects/(?P<pid>[^/]+)/links", self._enlace),
        ]

    def solicitar(self, metodo, ruta, *, cuerpo=None, crudo=None):
        self.llamadas.append((metodo, ruta, cuerpo if cuerpo is not None else crudo))
        for m, patron, manejador in self._rutas:
            if m == metodo and (r := re.fullmatch(patron, ruta)):
                return manejador(cuerpo=cuerpo, crudo=crudo, **r.groupdict())
        raise AssertionError(f"el GNS3 falso no conoce {metodo} {ruta}")

    # utilidades para las pruebas

    def pid(self) -> str:
        return next(iter(self.proyectos))

    def nodo(self, nombre: str) -> dict:
        return next(n for n in self.nodos[self.pid()].values() if n["name"] == nombre)

    def nombres(self) -> list[str]:
        return sorted(n["name"] for n in self.nodos[self.pid()].values())

    def archivo(self, nombre: str, ruta: str) -> bytes:
        return self.archivos[(self.pid(), self.nodo(nombre)["node_id"], ruta)]

    # rutas

    def _id(self, prefijo: str) -> str:
        self._n += 1
        return f"{prefijo}{self._n}"

    def _listar_proyectos(self, **_):
        return [{"name": p["name"], "project_id": pid, "status": "opened"} for pid, p in self.proyectos.items()]

    def _crear_proyecto(self, cuerpo, **_):
        pid = self._id("p")
        self.proyectos[pid] = {"name": cuerpo["name"]}
        self.nodos[pid], self.enlaces[pid] = {}, []
        return {"project_id": pid, "name": cuerpo["name"]}

    def _abrir(self, **_):
        return ""

    def _borrar_proyecto(self, pid, **_):
        del self.proyectos[pid], self.nodos[pid], self.enlaces[pid]

    def _crear_plantilla(self, cuerpo, **_):
        self.plantillas_creadas.append(cuerpo)
        tid = self._id("t")
        self._plantillas[tid] = {"template_id": tid, "name": cuerpo["name"], "node_type": "docker"}
        return self._plantillas[tid]

    def _crear_nodo(self, pid, tid, cuerpo, **_):
        plantilla = self._plantillas[tid]
        nid = self._id("n")
        nodo = {"node_id": nid, "name": plantilla["name"], "node_type": plantilla["node_type"], "status": "stopped",
                "x": cuerpo["x"], "y": cuerpo["y"], "console": 5000 + self._n, "console_host": "127.0.0.1",
                "properties": {"dynamips_id": self._n, "adapters": 8}}
        self.nodos[pid][nid] = nodo
        return dict(nodo)

    def _actualizar_nodo(self, pid, nid, cuerpo, **_):
        nodo = self.nodos[pid][nid]
        for clave, valor in cuerpo.items():
            if clave == "properties":
                nodo["properties"].update(valor)
            else:
                nodo[clave] = valor
        return dict(nodo)

    def _accion_todos(self, pid, accion, **_):
        for nodo in self.nodos[pid].values():
            nodo["status"] = "started" if accion == "start" else "stopped"

    def _iniciar_nodo(self, pid, nid, **_):
        self.nodos[pid][nid]["status"] = "started"

    def _archivo(self, pid, nid, ruta, crudo, **_):
        self.archivos[(pid, nid, ruta)] = crudo

    def _enlace(self, pid, cuerpo, **_):
        self.enlaces[pid].append({"link_id": self._id("l"), "nodes": cuerpo["nodes"]})


class EstadoFortigate:
    """Lo que sobrevive entre conexiones a la consola del FortiGate falso (la licencia, el reinicio)."""

    def __init__(self, licencia: str = "Invalid", clave: str = "Fortinet.2026", internet: bool = True):
        self.licencia = licencia
        self.clave = clave
        self.internet = internet
        self.rechazos = 0                  # conexiones que fallan porque el equipo esta reiniciando
        self.recibido: list[str] = []      # toda linea que llego, de cualquier conexion


class ConexionFortigate:
    """Consola telnet de un FortiGate con guion: login, `get system status`, ping y `execute vm-license`."""

    def __init__(self, estado: EstadoFortigate, reloj: RelojFalso):
        self._estado = estado
        self._reloj = reloj
        self._cola: list[bytes] = []
        self._fase = "login"
        self._confirmando = False

    def leer(self, timeout):
        if self._cola:
            return self._cola.pop(0)
        self._reloj.dormir(timeout)
        return None

    def enviar(self, datos: bytes) -> None:
        linea = datos.decode(errors="ignore").strip("\r")
        if datos[:1] == b"\xff":           # respuesta de negociacion telnet: no es un comando
            return
        self._estado.recibido.append(linea)
        self._responder(linea)

    def _decir(self, texto: str) -> None:
        self._cola.append(texto.encode())

    def _responder(self, linea: str) -> None:
        e = self._estado
        if self._fase == "login":
            if linea == "":
                self._decir("FortiGate-VM64 login: ")
            elif linea == "admin":
                self._fase = "clave"
                self._decir("Password: ")
        elif self._fase == "clave":
            if linea == e.clave:
                self._fase = "sesion"
                self._decir("FGVM # ")
            else:
                self._fase = "login"
                self._decir("Login incorrect\r\n")
        elif linea == "get system status":
            self._decir(f"Version: FortiGate-VM64 v8.0\r\nLicense Status: {e.licencia}\r\nFGVM # ")
        elif linea.startswith("execute ping"):
            recibidos = 5 if e.internet else 0
            self._decir(f"5 packets transmitted, {recibidos} packets received, 0% packet loss\r\nFGVM # ")
        elif linea == "execute vm-license":
            self._confirmando = True
            self._decir("This operation will reboot the system ! Do you want to continue? (y/n)")
        elif linea == "y" and self._confirmando:
            self._confirmando = False
            e.licencia, e.rechazos = "Valid", 2
        else:
            self._decir("FGVM # ")


class CanalFalso:
    def __init__(self) -> None:
        self.subidas: list[tuple[Path, str]] = []
        self.comandos: list[str] = []
        self.cerrado = False

    def subir_arbol(self, origen, destino):
        self.subidas.append((origen, destino))

    def ejecutar(self, comando, timeout=900):
        self.comandos.append(comando)
        return "build ok"

    def cerrar(self):
        self.cerrado = True


PLANTILLAS = {"RT": "dynamips", "FG": "qemu", "SWT": "ethernet_switch", "CL": "docker", "NAT": "nat"}

ARCHIVOS = {
    "automatizacion/topologia/proyecto.yml": """\
proyecto: casoT
plan_b: false
servidor: http://127.0.0.1:3080
plantillas: {router: RT, fortigate: FG, switch: SWT, cliente: CL}
tipos: {router: dynamips, fortigate: qemu, switch: ethernet_switch, cliente: docker}
dynamips_slots: {slot1: PA-GE, slot2: PA-GE}
fortigate: {nodo: FGT-01, usuario: admin, clave: Fortinet.2026, puerto_internet: port4}
imagenes:
  - {etiqueta: caso/x, ruta: servicios, plantilla: IMG}
ssh: {host: 127.0.0.1, puerto: 2222, usuario: gns3, clave: gns3}
""",
    "automatizacion/topologia/nodos/R1.yml": "plantilla: router\nx: -200\ny: -100\nconfig: configs/R1.txt\n",
    "automatizacion/topologia/nodos/FGT-01.yml": (
        "# el FortiGate\nplantilla: fortigate\nx: 0\ny: -100\nconfig: configs/FGT-01.conf\n"
        "config_plan_b: configs/FGT-01-planB.conf\n"),
    "automatizacion/topologia/nodos/SW.yml": (
        "plantilla: switch\nx: 0\ny: 100\npuertos:\n  - {n: 0, tipo: access, vlan: 1}\n  - {n: 1, tipo: access, vlan: 1}\n"),
    "automatizacion/topologia/nodos/PC.yml": "plantilla: cliente\nx: 200\ny: 100\nred: hosts/hosts.md\n",
    "automatizacion/topologia/enlaces/red.yml": "- [R1, Gi0/1, FGT-01, port1]\n- [FGT-01, port2, SW, p0]\n- [SW, p1, PC, eth0]\n",
    "automatizacion/secretos.yml": "forticloud:\n  correo: alumno@ejemplo.com\n  clave: ClaveSecreta1\n",
    "configs/R1.txt": (
        "!\nhostname R1\ninterface GigabitEthernet0/1\n ip address 10.0.0.1 255.255.255.0\n"
        "crypto key generate rsa modulus 2048\nip access-list extended USUARIOS\n remark 35 permit tcp any any\nend\nquedo fuera\n"),
    "configs/FGT-01.conf": "# comentario\nconfig system interface\nedit port1\nnext\nend\n",
    "configs/FGT-01-planB.conf": "# plan B\nconfig system interface\nedit port1\nset alias planb\nnext\nend\n",
    "hosts/hosts.md": "# Hosts\n\n### PC\n\n```\nauto eth0\niface eth0 inet static\n```\n",
    "servicios/Dockerfile": "FROM alpine\n",
    "servicios/cliente/Dockerfile": "FROM alpine\n",
}


class Escenario:
    """Un repo de juguete valido en una carpeta temporal, con todos los dobles ya conectados a una Aplicacion."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.base = self.raiz / "automatizacion"
        for ruta, texto in ARCHIVOS.items():
            self.escribir(ruta, texto)
        os.chmod(self.base / "secretos.yml", 0o600)
        self.salida: list[str] = []
        self.gns3 = Gns3Falso(PLANTILLAS)
        self.reloj = RelojFalso()
        self.canal = CanalFalso()
        self.fortigate = EstadoFortigate()
        self.conexiones: list[ConexionFortigate] = []
        self.app = Aplicacion(
            repositorio=Repositorio(self.base), reloj=self.reloj, salida=self.salida.append,
            fabrica_transporte=lambda servidor: self.gns3, fabrica_conexion=self._conexion,
            fabrica_canal=lambda config: self.canal, tipos=registro_por_defecto())

    def _conexion(self, puerto: int) -> ConexionFortigate:
        if self.fortigate.rechazos > 0:
            self.fortigate.rechazos -= 1
            raise ErrorConexionConsola("el FortiGate aun reinicia")
        conexion = ConexionFortigate(self.fortigate, self.reloj)
        self.conexiones.append(conexion)
        return conexion

    def escribir(self, ruta: str, texto: str) -> None:
        destino = self.raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")

    def reemplazar(self, ruta: str, viejo: str, nuevo: str) -> None:
        texto = (self.raiz / ruta).read_text(encoding="utf-8")
        assert viejo in texto, f"{viejo!r} no esta en {ruta}"
        self.escribir(ruta, texto.replace(viejo, nuevo))

    def borrar(self, ruta: str) -> None:
        (self.raiz / ruta).unlink()

    def recargar(self):
        """Una Aplicacion nueva sobre los archivos actuales (el proyecto se carga una sola vez por Aplicacion)."""
        self.app.__dict__.pop("proyecto", None)
        self.app.__dict__.pop("gns3", None)
        return self.app

    def cerrar(self) -> None:
        self._tmp.cleanup()
