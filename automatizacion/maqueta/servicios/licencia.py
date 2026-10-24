"""licenciar: activa la licencia de evaluacion permanente del FortiGate con la cuenta FortiCloud de secretos.yml.

Sin esa licencia el FortiGate dice 'License Status: Invalid' y, segun la documentacion de Fortinet, no
aplica politicas. El flujo: darle salida a internet con un NAT temporal de GNS3, pedir la licencia, esperar
el reinicio, verificar `Valid` y retirar el NAT.
"""
from __future__ import annotations

from typing import Callable

from ..errores import ErrorConexionConsola, ErrorConsola, ErrorEstado
from ..fortigate_cli import SesionFortigate
from ..gns3 import ClienteGns3, NodoGns3
from ..modelo import Proyecto, Puerto
from ..reloj import Reloj
from ..secretos import AlmacenSecretos
from ..tipos import RegistroTipos

NAT = "NAT-licencia"
_ESPERA_REINICIO = 480


class ActivadorLicencia:
    def __init__(self, gns3: ClienteGns3, proyecto: Proyecto, secretos: AlmacenSecretos, tipos: RegistroTipos,
                 abrir_sesion: Callable[[int], SesionFortigate], reloj: Reloj, salida: Callable[[str], None]):
        self._gns3 = gns3
        self._p = proyecto
        self._secretos = secretos
        self._tipos = tipos
        self._abrir_sesion = abrir_sesion
        self._reloj = reloj
        self._salida = salida

    def activar(self, equipo: str | None = None) -> None:
        cuenta = self._secretos.forticloud()
        cfg = self._p.fortigate_requerido()
        nombre = equipo or cfg.nodo
        puerto = cfg.puerto_internet
        adaptador = self._tipos.puerto("qemu", puerto).adaptador
        pid = self._gns3.abrir_proyecto()
        en_gns3 = self._gns3.nodos(pid)
        fgt = en_gns3.get(nombre)
        if fgt is None or not fgt.encendido:
            raise ErrorEstado(f"{nombre} no esta encendido. Corre: gns3ctl.py iniciar y espera 2 a 3 minutos.")
        if fgt.propiedades.get("adapters", 0) <= adaptador:
            raise ErrorEstado(f"{nombre} no tiene el adaptador de {puerto}.")
        sesion = self._abrir_sesion(fgt.console)
        if not sesion.iniciar():
            raise ErrorConsola(f"No pude iniciar sesion en {nombre}.")
        sesion.salida_estandar()
        estado = sesion.estado_licencia()
        self._salida(f"licencia actual: {estado}")
        if estado == "Valid":
            return

        nat = self._nat_temporal(pid, en_gns3, fgt, adaptador)
        self._gns3.iniciar_nodo(pid, nat.node_id)
        sesion.enviar_lineas(["config system interface", f"edit {puerto}", "set mode dhcp", "set allowaccess ping",
                              "set defaultgw enable", "set status up", "next", "end"])
        self._salida(f"{puerto} en DHCP contra el NAT de GNS3; espero la direccion y pruebo salida a internet")
        self._reloj.dormir(20)
        if sesion.paquetes_recibidos("8.8.8.8") == 0:
            raise ErrorEstado(f"{nombre} no tiene salida a internet por {puerto} (ping a 8.8.8.8 sin respuesta). Revisa el nodo {NAT}.")
        self._salida("salida a internet: ok")

        self._pedir_licencia(sesion, cuenta.correo, cuenta.clave)
        nuevo, sesion = self._esperar_reinicio(fgt, sesion)
        self._salida(f"licencia despues del reinicio: {nuevo}")
        if nuevo != "Valid":
            raise ErrorEstado("La licencia no quedo Valid. Revisa en el FortiGate: get system status y diagnose debug vm-print-license")

        # el puerto vuelve a quedar sin uso y se quita el NAT temporal
        sesion.enviar_lineas(["config system interface", f"edit {puerto}", "set mode static", "set ip 0.0.0.0 0.0.0.0",
                              "unset allowaccess", "set status down", "next", "end"])
        self._gns3.borrar_nodo(pid, nat.node_id)
        self._salida("listo: licencia de evaluacion activa y NAT temporal retirado")

    def _nat_temporal(self, pid: str, en_gns3: dict[str, NodoGns3], fgt: NodoGns3, adaptador: int) -> NodoGns3:
        """El nodo NAT de GNS3 enlazado al puerto libre del FortiGate; lo reutiliza si ya existe."""
        if NAT in en_gns3:
            return en_gns3[NAT]
        nat = self._gns3.crear_nodo(pid, "NAT", NAT, fgt.x, fgt.y - 150)
        self._gns3.conectar(pid, (nat.node_id, Puerto(0, 0)), (fgt.node_id, Puerto(adaptador, 0)))
        return nat

    def _pedir_licencia(self, sesion: SesionFortigate, correo: str, clave: str) -> None:
        sesion.enviar_lineas([f"execute vm-license-options account-id {correo}",
                              f"execute vm-license-options account-password {clave}"], pausa=1)
        sesion.limpiar()
        sesion.enviar("execute vm-license")
        r = sesion.esperar([r"\(y/n\)", r"[Ff]ail", r"[Ee]rror"], 90)
        if r != r"\(y/n\)":
            detalle = "\n  ".join(sesion.ultimas_lineas(8))
            raise ErrorEstado("FortiCloud no entrego la licencia:\n  " + detalle)
        sesion.enviar("y")
        self._salida("licencia aceptada; el FortiGate se reinicia, espero hasta 8 minutos")

    def _esperar_reinicio(self, fgt: NodoGns3, sesion: SesionFortigate) -> tuple[str | None, SesionFortigate]:
        """Reintenta entrar cada 25 s hasta que la licencia figure Valid o se agote el plazo."""
        estado, fin = None, self._reloj.ahora() + _ESPERA_REINICIO
        while self._reloj.ahora() < fin and estado != "Valid":
            self._reloj.dormir(25)
            try:
                otra = self._abrir_sesion(fgt.console)
                if otra.iniciar(40, estricto=False):
                    otra.salida_estandar()
                    estado, sesion = otra.estado_licencia(), otra
            except (OSError, ErrorConexionConsola):
                pass                      # el FortiGate aun reinicia: se reintenta
        return estado, sesion
