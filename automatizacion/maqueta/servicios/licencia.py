"""licenciar: activa la licencia de evaluacion permanente del FortiGate con la cuenta FortiCloud de secretos.yml.

Sin esa licencia el FortiGate dice 'License Status: Invalid' y, segun la documentacion de Fortinet, no
aplica politicas. El flujo: darle salida a internet con un NAT temporal de GNS3, pedir la licencia, esperar
el reinicio, verificar `Valid` y retirar el NAT.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..entorno import Entorno
from ..errores import ErrorConexionConsola, ErrorConsola, ErrorEstado
from ..fortigate_cli import SesionFortigate
from ..gns3 import NodoGns3, NuevoNodo
from ..modelo import Puerto
from ..secretos import AlmacenSecretos, CredencialesForticloud

NAT = "NAT-licencia"
_ESPERA_REINICIO = 480


@dataclass
class _Corrida:
    """Lo que `activar` va descubriendo del FortiGate: su nodo, el puerto con salida y la sesion abierta."""

    nombre: str
    puerto: str
    adaptador: int
    pid: str
    nodos: dict[str, NodoGns3]
    sesion: SesionFortigate

    @property
    def fgt(self) -> NodoGns3:
        return self.nodos[self.nombre]


class ActivadorLicencia:
    def __init__(self, entorno: Entorno, secretos: AlmacenSecretos):
        self._e = entorno
        self._secretos = secretos

    def activar(self, equipo: str | None = None) -> None:
        cuenta = self._secretos.forticloud()
        c = self._conectar(equipo)
        estado = c.sesion.estado_licencia()
        self._e.salida(f"licencia actual: {estado}")
        if estado == "Valid":
            return
        nat = self._dar_internet(c)
        self._pedir_licencia(c.sesion, cuenta)
        self._verificar(c)
        self._retirar_nat(c, nat)
        self._e.salida("listo: licencia de evaluacion activa y NAT temporal retirado")

    def _conectar(self, equipo: str | None) -> _Corrida:
        cfg = self._e.proyecto.fortigate_requerido()
        nombre, puerto = equipo or cfg.nodo, cfg.puerto_internet
        adaptador = self._e.tipos.puerto("qemu", puerto).adaptador
        pid = self._e.gns3.abrir_proyecto()
        nodos = self._e.gns3.nodos(pid)
        fgt = nodos.get(nombre)
        if fgt is None or not fgt.encendido:
            raise ErrorEstado(f"{nombre} no esta encendido. Corre: gns3ctl.py iniciar y espera 2 a 3 minutos.")
        if fgt.propiedades.get("adapters", 0) <= adaptador:
            raise ErrorEstado(f"{nombre} no tiene el adaptador de {puerto}.")
        sesion = self._e.sesion_fortigate(fgt.console)
        if not sesion.iniciar():
            raise ErrorConsola(f"No pude iniciar sesion en {nombre}.")
        sesion.salida_estandar()
        return _Corrida(nombre, puerto, adaptador, pid, nodos, sesion)

    def _dar_internet(self, c: _Corrida) -> NodoGns3:
        """Enlaza un NAT de GNS3 al puerto libre, lo pone en DHCP y comprueba que sale a internet."""
        nat = self._nat_temporal(c)
        self._e.gns3.iniciar_nodo(c.pid, nat.node_id)
        c.sesion.enviar_lineas(["config system interface", f"edit {c.puerto}", "set mode dhcp", "set allowaccess ping",
                                "set defaultgw enable", "set status up", "next", "end"])
        self._e.salida(f"{c.puerto} en DHCP contra el NAT de GNS3; espero la direccion y pruebo salida a internet")
        self._e.reloj.dormir(20)
        if c.sesion.paquetes_recibidos("8.8.8.8") == 0:
            raise ErrorEstado(f"{c.nombre} no tiene salida a internet por {c.puerto} (ping a 8.8.8.8 sin respuesta). Revisa el nodo {NAT}.")
        self._e.salida("salida a internet: ok")
        return nat

    def _nat_temporal(self, c: _Corrida) -> NodoGns3:
        """El nodo NAT de GNS3 enlazado al puerto libre del FortiGate; lo reutiliza si ya existe."""
        if NAT in c.nodos:
            return c.nodos[NAT]
        nat = self._e.gns3.crear_nodo(c.pid, NuevoNodo("NAT", NAT, c.fgt.x, c.fgt.y - 150))
        self._e.gns3.conectar(c.pid, (nat.node_id, Puerto(0, 0)), (c.fgt.node_id, Puerto(c.adaptador, 0)))
        return nat

    def _pedir_licencia(self, sesion: SesionFortigate, cuenta: CredencialesForticloud) -> None:
        sesion.enviar_lineas([f"execute vm-license-options account-id {cuenta.correo}",
                              f"execute vm-license-options account-password {cuenta.clave}"], pausa=1)
        sesion.limpiar()
        sesion.enviar("execute vm-license")
        r = sesion.esperar([r"\(y/n\)", r"[Ff]ail", r"[Ee]rror"], 90)
        if r != r"\(y/n\)":
            detalle = "\n  ".join(sesion.ultimas_lineas(8))
            raise ErrorEstado("FortiCloud no entrego la licencia:\n  " + detalle)
        sesion.enviar("y")
        self._e.salida("licencia aceptada; el FortiGate se reinicia, espero hasta 8 minutos")

    def _verificar(self, c: _Corrida) -> None:
        nuevo = self._esperar_reinicio(c)
        self._e.salida(f"licencia despues del reinicio: {nuevo}")
        if nuevo != "Valid":
            raise ErrorEstado("La licencia no quedo Valid. Revisa en el FortiGate: get system status y diagnose debug vm-print-license")

    def _esperar_reinicio(self, c: _Corrida) -> str | None:
        """Reintenta entrar cada 25 s hasta que la licencia figure Valid o se agote el plazo. Deja en `c` la sesion nueva."""
        estado, fin = None, self._e.reloj.ahora() + _ESPERA_REINICIO
        while self._e.reloj.ahora() < fin and estado != "Valid":
            self._e.reloj.dormir(25)
            try:
                otra = self._e.sesion_fortigate(c.fgt.console)
                if otra.iniciar(40, estricto=False):
                    otra.salida_estandar()
                    estado, c.sesion = otra.estado_licencia(), otra
            except (OSError, ErrorConexionConsola):
                pass                      # el FortiGate aun reinicia: se reintenta
        return estado

    def _retirar_nat(self, c: _Corrida, nat: NodoGns3) -> None:
        """El puerto vuelve a quedar sin uso y se quita el NAT temporal."""
        c.sesion.enviar_lineas(["config system interface", f"edit {c.puerto}", "set mode static", "set ip 0.0.0.0 0.0.0.0",
                                "unset allowaccess", "set status down", "next", "end"])
        self._e.gns3.borrar_nodo(c.pid, nat.node_id)
