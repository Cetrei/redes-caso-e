"""secretos.yml: la cuenta de FortiCloud. Vive fuera de git (ver .gitignore); plantilla: secretos.ejemplo.yml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from .errores import ErrorSecretos


@dataclass(frozen=True)
class CredencialesForticloud:
    correo: str
    clave: str

    def __repr__(self) -> str:        # la clave nunca sale en trazas ni en logs
        return f"CredencialesForticloud(correo={self.correo!r}, clave='***')"


class AlmacenSecretos:
    def __init__(self, ruta: Path, salida: Callable[[str], None]):
        self._ruta = ruta
        self._salida = salida

    def forticloud(self) -> CredencialesForticloud:
        ruta = self._ruta
        if not ruta.exists():
            raise ErrorSecretos(f"Falta automatizacion/{ruta.name}. Copia secretos.ejemplo.yml como secretos.yml y pon tu correo y clave de FortiCloud.")
        if ruta.stat().st_mode & 0o077:
            self._salida(f"aviso: {ruta.name} es legible por otros usuarios; conviene: chmod 600 {ruta}")
        cf = (yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}).get("forticloud") or {}
        correo, clave = str(cf.get("correo") or ""), str(cf.get("clave") or "")
        if "@" not in correo or not clave or "tu_correo" in correo or clave == "tu_clave_de_forticloud":
            raise ErrorSecretos(f"{ruta.name}: llena forticloud.correo y forticloud.clave con los datos de tu cuenta de FortiCloud.")
        return CredencialesForticloud(correo, clave)
