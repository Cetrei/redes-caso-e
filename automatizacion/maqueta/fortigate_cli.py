from __future__ import annotations

import re
from typing import Sequence

from .consola import Consola
from .errores import ErrorConsola
from .modelo import ConfigFortigate
from .reloj import Reloj

_PROMPT = r"[#$] $"


class SesionFortigate:
    def __init__(self, consola: Consola, credenciales: ConfigFortigate, reloj: Reloj):
        self._c = consola
        self._cred = credenciales
        self._reloj = reloj

    def iniciar(self, espera: float = 240, estricto: bool = True) -> bool:
        self._c.enviar("")
        for _ in range(8):
            r = self._c.esperar([r"login:", r"Password:", r"New Password:", _PROMPT, r"Login incorrect"], espera)
            if r == "login:":
                self._c.enviar(self._cred.usuario)
            elif r == "Password:":
                self._c.enviar(self._cred.clave)
            elif r == "New Password:":
                raise ErrorConsola("El FortiGate pide cambiar la clave en el primer ingreso: hacelo a mano una vez y reintenta.")
            elif r == "Login incorrect":
                if estricto:
                    raise ErrorConsola("Clave del FortiGate incorrecta: ajusta fortigate.clave en topologia/proyecto.yml")
                return False
            elif r:
                return True
            else:
                self._c.enviar("")
        return False

    def enviar(self, texto: str) -> None:
        self._c.enviar(texto)

    def limpiar(self) -> None:
        self._c.limpiar()

    def enviar_lineas(self, lineas: Sequence[str], pausa: float = 0.3) -> None:
        for l in lineas:
            self._c.enviar(l)
            self._reloj.dormir(pausa)

    def pegar(self, lineas: Sequence[str]) -> None:
        for l in lineas:
            self._c.enviar(l)
            self._reloj.dormir(0.15)
            self._c.leer(0.05)
        self._reloj.dormir(2)
        self._c.leer(1)

    def esperar(self, patrones: Sequence[str], timeout: float) -> str | None:
        return self._c.esperar(patrones, timeout)

    def ultimas_lineas(self, n: int) -> list[str]:
        return [l for l in self._c.buffer.splitlines() if l.strip()][-n:]

    def ejecutar(self, comando: str, espera: float = 0.0, leer: float = 1.0) -> str:
        self._c.limpiar()
        self._c.enviar(comando)
        if espera:
            self._reloj.dormir(espera)
        self._c.leer(leer)
        return self._c.buffer

    def salida_estandar(self) -> None:
        self.enviar_lineas(["config system console", "set output standard", "end"])

    def estado_licencia(self) -> str | None:
        m = re.search(r"License Status:\s*(\w+)", self.ejecutar("get system status", espera=2.5))
        return m.group(1) if m else None

    def paquetes_recibidos(self, destino: str) -> int:
        m = re.search(r"(\d+) packets received", self.ejecutar(f"execute ping {destino}", espera=9))
        return int(m.group(1)) if m else 0
