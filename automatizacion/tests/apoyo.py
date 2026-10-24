from __future__ import annotations

import os
import tempfile
from pathlib import Path

from maqueta.aplicacion import Adaptadores, Aplicacion
from maqueta.errores import ErrorConexionConsola
from maqueta.repositorio import Repositorio
from maqueta.tipos import registro_por_defecto

from .fortigate_falso import ConexionFortigate, EstadoFortigate
from .gns3_falso import Gns3Falso
from .reloj_falso import RelojFalso


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
    "automatizacion/.env": "FORTICLOUD_CORREO=alumno@ejemplo.com\nFORTICLOUD_CLAVE=ClaveSecreta1\n",
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
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.base = self.raiz / "automatizacion"
        for ruta, texto in ARCHIVOS.items():
            self.escribir(ruta, texto)
        os.chmod(self.base / ".env", 0o600)
        self.salida: list[str] = []
        self.gns3 = Gns3Falso(PLANTILLAS)
        self.reloj = RelojFalso()
        self.canal = CanalFalso()
        self.fortigate = EstadoFortigate()
        self.conexiones: list[ConexionFortigate] = []
        self.app = Aplicacion(Repositorio(self.base), self._adaptadores())

    def _adaptadores(self) -> Adaptadores:
        return Adaptadores(reloj=self.reloj, salida=self.salida.append, fabrica_transporte=lambda servidor: self.gns3,
                           fabrica_conexion=self._conexion, fabrica_canal=lambda config: self.canal,
                           tipos=registro_por_defecto())

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
        for dato in ("proyecto", "gns3", "entorno"):
            self.app.__dict__.pop(dato, None)
        return self.app

    def cerrar(self) -> None:
        self._tmp.cleanup()
