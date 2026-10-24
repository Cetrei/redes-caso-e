"""Consola telnet de los nodos de GNS3 (telnetlib ya no existe en Python 3.13+).

`Conexion` es el seam con el socket: la real es `ConexionTcp`, las pruebas usan una que responde con guion.
`Consola` pone encima lo que no depende del socket: filtrar la negociacion telnet, acumular lo recibido y
esperar patrones con un plazo medido por el `Reloj`.
"""
from __future__ import annotations

import re
import socket
from typing import Protocol, Sequence

from .errores import ErrorConexionConsola
from .reloj import Reloj

_IAC = 255
_WILL, _WONT, _DO, _DONT = 251, 252, 253, 254


class Conexion(Protocol):
    def leer(self, timeout: float) -> bytes | None:
        """Bytes recibidos, o None si no llego nada en `timeout` segundos."""
        ...

    def enviar(self, datos: bytes) -> None: ...


class ConexionTcp:
    def __init__(self, puerto: int, host: str = "127.0.0.1"):
        try:
            self._s = socket.create_connection((host, puerto), timeout=10)
        except OSError as e:
            raise ErrorConexionConsola(f"No pude abrir la consola {host}:{puerto}: {e}") from e

    def leer(self, timeout: float) -> bytes | None:
        self._s.settimeout(timeout)
        try:
            return self._s.recv(4096)
        except (socket.timeout, TimeoutError):
            return None

    def enviar(self, datos: bytes) -> None:
        self._s.sendall(datos)


class Consola:
    def __init__(self, conexion: Conexion, reloj: Reloj):
        self._c = conexion
        self._reloj = reloj
        self.buffer = ""

    def leer(self, timeout: float) -> bool:
        """Lee lo que haya durante `timeout` y lo suma a `buffer`. False si no llego nada."""
        datos = self._c.leer(timeout)
        if datos is None:
            return False
        self.buffer += self._sin_negociacion(datos)
        return True

    def esperar(self, patrones: Sequence[str], timeout: float = 120) -> str | None:
        """Espera a que `buffer` coincida con alguno de los patrones. Devuelve el patron (y vacia el buffer) o None."""
        fin = self._reloj.ahora() + timeout
        while self._reloj.ahora() < fin:
            for p in patrones:
                if re.search(p, self.buffer):
                    self.buffer = ""
                    return p
            self.leer(1)
        return None

    def enviar(self, texto: str) -> None:
        self._c.enviar(texto.encode() + b"\r")

    def limpiar(self) -> None:
        self.buffer = ""

    def _sin_negociacion(self, datos: bytes) -> str:
        """Quita las secuencias IAC rechazando toda opcion que proponga el nodo."""
        out, i = bytearray(), 0
        while i < len(datos):
            if datos[i] == _IAC and i + 2 < len(datos):
                if datos[i + 1] in (_WILL, _WONT):
                    self._c.enviar(bytes([_IAC, _DONT, datos[i + 2]]))
                elif datos[i + 1] in (_DO, _DONT):
                    self._c.enviar(bytes([_IAC, _WONT, datos[i + 2]]))
                i += 3
            else:
                out.append(datos[i])
                i += 1
        return out.decode(errors="ignore")
