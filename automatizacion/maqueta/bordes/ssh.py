from __future__ import annotations

from pathlib import Path
from typing import Protocol

from maqueta.nucleo.errores import ErrorVm
from maqueta.nucleo.modelo import ConfigSsh


class CanalVm(Protocol):
    def subir_arbol(self, origen: Path, destino: str) -> None:
        ...

    def ejecutar(self, comando: str, timeout: int = 900) -> str: ...

    def cerrar(self) -> None: ...


class CanalSsh:
    def __init__(self, config: ConfigSsh):
        try:
            import paramiko
        except ImportError as e:
            raise ErrorVm("Falta el paquete paramiko: corre el script con `uv run` (instala pyyaml y paramiko solo) o instalalo con pip.") from e
        self._cliente = paramiko.SSHClient()
        self._cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._cliente.connect(config.host, port=config.puerto, username=config.usuario, password=config.clave,
                                  allow_agent=False, look_for_keys=False)
        except (OSError, paramiko.SSHException) as e:
            raise ErrorVm(f"No pude conectar por SSH a {config.host}:{config.puerto}: {e}") from e

    def subir_arbol(self, origen: Path, destino: str) -> None:
        sftp = self._cliente.open_sftp()
        try:
            self._mkdir(sftp, destino)
            for ruta in sorted(p for p in origen.rglob("*") if p.is_file() and p.name != ".gitkeep"):
                rel = ruta.relative_to(origen).as_posix()
                carpetas = rel.split("/")[:-1]
                for i in range(len(carpetas)):
                    self._mkdir(sftp, f"{destino}/" + "/".join(carpetas[:i + 1]))
                sftp.put(str(ruta), f"{destino}/{rel}")
        finally:
            sftp.close()

    def ejecutar(self, comando: str, timeout: int = 900) -> str:
        _, salida, _ = self._cliente.exec_command(comando, timeout=timeout)
        return salida.read().decode()

    def cerrar(self) -> None:
        self._cliente.close()

    @staticmethod
    def _mkdir(sftp, ruta: str) -> None:
        try:
            sftp.mkdir(ruta)
        except OSError:
            pass
