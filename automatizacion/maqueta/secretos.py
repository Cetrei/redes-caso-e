from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .errores import ErrorSecretos


@dataclass(frozen=True)
class CredencialesForticloud:
    correo: str
    clave: str

    def __repr__(self) -> str:
        return f"CredencialesForticloud(correo={self.correo!r}, clave='***')"


def leer_env(texto: str) -> dict[str, str]:
    valores: dict[str, str] = {}
    for linea in texto.splitlines():
        nombre, separador, valor = linea.strip().partition("=")
        if separador and not nombre.startswith("#"):
            valores[nombre.strip()] = _sin_comillas(valor.strip())
    return valores


def _sin_comillas(valor: str) -> str:
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        return valor[1:-1]
    return valor


class AlmacenSecretos:
    def __init__(self, ruta: Path, salida: Callable[[str], None]):
        self._ruta = ruta
        self._salida = salida

    def forticloud(self) -> CredencialesForticloud:
        valores = self._leer()
        correo, clave = valores.get("FORTICLOUD_CORREO", ""), valores.get("FORTICLOUD_CLAVE", "")
        if "@" not in correo or not clave:
            raise ErrorSecretos(f"{self._ruta.name}: llena FORTICLOUD_CORREO y FORTICLOUD_CLAVE con los datos de tu cuenta de FortiCloud.")
        return CredencialesForticloud(correo, clave)

    def _leer(self) -> dict[str, str]:
        ruta = self._ruta
        if not ruta.exists():
            raise ErrorSecretos(f"Falta automatizacion/{ruta.name}. Copia .env.example como {ruta.name} y llena tu correo y clave de FortiCloud.")
        if ruta.stat().st_mode & 0o077:
            self._salida(f"aviso: {ruta.name} es legible por otros usuarios; conviene: chmod 600 {ruta}")
        return leer_env(ruta.read_text(encoding="utf-8"))
