"""Una consola de FortiGate con guion: login, `get system status`, ping y `execute vm-license`."""
from __future__ import annotations

from .reloj_falso import RelojFalso


class EstadoFortigate:
    """Lo que sobrevive entre conexiones a la consola (la licencia, el reinicio)."""

    def __init__(self, licencia: str = "Invalid", clave: str = "Fortinet.2026", internet: bool = True):
        self.licencia = licencia
        self.clave = clave
        self.internet = internet
        self.rechazos = 0                  # conexiones que fallan porque el equipo esta reiniciando
        self.recibido: list[str] = []      # toda linea que llego, de cualquier conexion


class ConexionFortigate:
    def __init__(self, estado: EstadoFortigate, reloj: RelojFalso):
        self._estado = estado
        self._reloj = reloj
        self._cola: list[bytes] = []
        self._fase = "login"
        self._confirmando = False

    def leer(self, timeout: float) -> bytes | None:
        """Todo lo que haya llegado desde la ultima lectura, como en un socket de verdad."""
        if self._cola:
            datos, self._cola = b"".join(self._cola), []
            return datos
        self._reloj.dormir(timeout)
        return None

    def enviar(self, datos: bytes) -> None:
        linea = datos.decode(errors="ignore").strip("\r")
        if datos[:1] == b"\xff":           # respuesta de negociacion telnet: no es un comando
            return
        self._estado.recibido.append(linea)
        if self._fase == "sesion":
            self._comando(linea)
        else:
            self._entrar(linea)

    def _decir(self, texto: str) -> None:
        self._cola.append(texto.encode())

    def _entrar(self, linea: str) -> None:
        if self._fase == "login":
            if linea == "":
                self._decir("FortiGate-VM64 login: ")
            elif linea == "admin":
                self._fase = "clave"
                self._decir("Password: ")
        elif linea == self._estado.clave:
            self._fase = "sesion"
            self._decir("FGVM # ")
        else:
            self._fase = "login"
            self._decir("Login incorrect\r\n")

    def _comando(self, linea: str) -> None:
        e = self._estado
        if linea == "get system status":
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
