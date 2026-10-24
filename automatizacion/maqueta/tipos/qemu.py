"""Nodos QEMU (FortiGate): puertos portN. Su configuracion se pega por consola con el comando `fortigate`."""
import re
from ..config import ErrorTopologia

EJEMPLO = "port1"


def puerto(nombre):
    m = re.fullmatch(r"port(\d+)", nombre)
    if not m:
        raise ErrorTopologia(f"puerto '{nombre}' invalido para el FortiGate (se espera como {EJEMPLO})")
    return int(m.group(1)) - 1, 0


def preparar(ctx, nombre, d, n):
    pass
