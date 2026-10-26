from __future__ import annotations

import re
from typing import Sequence

from maqueta.bordes.consola import Consola
from maqueta.bordes.reloj import Reloj
from maqueta.nucleo.errores import ErrorConsola
from maqueta.nucleo.modelo import ConfigFortigate

_PROMPT = r"[#$] $"
_RECHAZO, _NUEVA, _USUARIO, _CLAVE = r"Login incorrect", r"New Password:", r"login:", r"Password:"
_ORDEN = (_RECHAZO, _NUEVA, _USUARIO, _CLAVE, _PROMPT)
_INTENTOS = 3
_PAUSA_RECHAZO = 65
_FALLO = re.compile(r"Command fail|parse error|Unknown action|node_check_object fail|maximum number|not found|invalid", re.IGNORECASE)
_CIERRES = ("end", "next")


class SesionFortigate:
    def __init__(self, consola: Consola, credenciales: ConfigFortigate, reloj: Reloj):
        self._c = consola
        self._cred = credenciales
        self._reloj = reloj

    def iniciar(self, espera: float = 240, estricto: bool = True) -> bool:
        intentos = _INTENTOS if estricto else 1
        for intento in range(intentos):
            if intento:
                self._reloj.dormir(_PAUSA_RECHAZO)
            resultado = self._intentar(espera)
            if resultado is not None:
                return resultado
        if estricto:
            raise ErrorConsola(f"El FortiGate rechazo la clave {intentos} veces seguidas. Tambien la rechaza mientras arranca o "
                               "tras 3 fallos en 60 s. Si de verdad es otra, ajusta fortigate.clave en topologia/proyecto.yml")
        return False

    def _intentar(self, espera: float) -> bool | None:
        self._c.despertar()
        for _ in range(8):
            r = self._c.esperar(_ORDEN, espera)
            if r == _RECHAZO:
                return None
            if r == _NUEVA:
                raise ErrorConsola("El FortiGate pide cambiar la clave en el primer ingreso: hacelo a mano una vez y reintenta.")
            if r == _USUARIO:
                self._c.enviar(self._cred.usuario)
            elif r == _CLAVE:
                self._c.enviar(self._cred.clave)
            elif r:
                return True
            else:
                self._c.despertar()
        return False

    def enviar(self, texto: str) -> None:
        self._c.enviar(texto)

    def limpiar(self) -> None:
        self._c.limpiar()

    def enviar_lineas(self, lineas: Sequence[str], pausa: float = 0.3) -> None:
        for l in lineas:
            self._c.enviar(l)
            self._reloj.dormir(pausa)

    def pegar(self, lineas: Sequence[str]) -> list[str]:
        fallos = []
        for l in lineas:
            antes = len(self._c.buffer)
            self._c.enviar(l)
            self._reloj.dormir(0.6 if l.strip() in _CIERRES else 0.15)
            self._drenar(0.05)
            fallo = self._primer_fallo(self._c.buffer[antes:])
            if fallo:
                fallos.append(f"{l.strip()}  ->  {fallo}")
        self._reloj.dormir(2)
        self._drenar(1)
        return fallos

    def _drenar(self, espera: float) -> None:
        while self._c.leer(espera):
            pass

    @staticmethod
    def _primer_fallo(texto: str) -> str | None:
        return next((x.strip() for x in texto.splitlines() if _FALLO.search(x)), None)

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
