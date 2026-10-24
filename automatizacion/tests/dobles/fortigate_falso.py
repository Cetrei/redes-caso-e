from __future__ import annotations

from tests.dobles.reloj_falso import RelojFalso


class EstadoFortigate:
    def __init__(self, licencia: str = "Invalid", clave: str = "Fortinet.2026", internet: bool = True):
        self.licencia = licencia
        self.clave = clave
        self.internet = internet
        self.rechazos = 0
        self.rechazos_clave = 0
        self.pings_perdidos = 0
        self.rechazadas: set[str] = set()
        self.sin_cupo: set[str] = set()
        self.en_uso: set[str] = set()
        self.recibido: list[str] = []


class ConexionFortigate:
    def __init__(self, estado: EstadoFortigate, reloj: RelojFalso):
        self._estado = estado
        self._reloj = reloj
        self._cola: list[bytes] = []
        self._fase = "login"
        self._confirmando = False

    def leer(self, timeout: float) -> bytes | None:
        if self._cola:
            datos, self._cola = b"".join(self._cola), []
            return datos
        self._reloj.dormir(timeout)
        return None

    def enviar(self, datos: bytes) -> None:
        linea = datos.decode(errors="ignore").strip("\r")
        if datos[:1] == b"\xff":
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
            if linea in ("", "\x03"):
                self._decir("FortiGate-VM64 login: ")
            elif linea == "admin":
                self._fase = "clave"
                self._decir("Password: ")
        elif linea == self._estado.clave and not self._estado.rechazos_clave:
            self._fase = "sesion"
            self._decir("FGVM # ")
        else:
            self._estado.rechazos_clave = max(0, self._estado.rechazos_clave - 1)
            self._fase = "login"
            self._decir("Login incorrect\r\n\r\nFGVM login: ")

    def _comando(self, linea: str) -> None:
        e = self._estado
        if linea == "get system status":
            self._decir(f"Version: FortiGate-VM64 v8.0\r\nLicense Status: {e.licencia}\r\nFGVM # ")
        elif linea.startswith("execute ping"):
            recibidos = 5 if e.internet and not e.pings_perdidos else 0
            e.pings_perdidos = max(0, e.pings_perdidos - 1)
            self._decir(f"5 packets transmitted, {recibidos} packets received, 0% packet loss\r\nFGVM # ")
        elif linea == "execute vm-license":
            self._confirmando = True
            self._decir("This operation will reboot the system ! Do you want to continue? (y/n)")
        elif linea in e.rechazadas:
            self._decir("command parse error before 'x'\r\nCommand fail. Return code -61\r\nFGVM # ")
        elif linea in e.sin_cupo:
            self._decir("The maximum number of entries has been reached.\r\nCommand fail. Return code -61\r\nFGVM # ")
        elif linea in e.en_uso:
            self._decir("Command fail. Return code -23\r\nFGVM # ")
        elif linea == "y" and self._confirmando:
            self._confirmando = False
            e.licencia, e.rechazos = "Valid", 2
        else:
            self._decir("FGVM # ")
