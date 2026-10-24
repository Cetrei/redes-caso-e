"""Lectura de hosts/hosts.md: la red de cada contenedor."""
from __future__ import annotations


def bloques(texto: str) -> dict[str, str]:
    """Devuelve {equipo: /etc/network/interfaces}: el primer bloque ``` bajo cada encabezado '### NOMBRE'."""
    res: dict[str, str] = {}
    actual, dentro, buf = None, False, []
    for linea in texto.splitlines():
        if linea.startswith("### "):
            actual = linea[4:].strip()
        elif linea.startswith("```"):
            if dentro:
                res.setdefault(actual, "\n".join(buf) + "\n")
                dentro, buf = False, []
            elif actual and actual not in res:
                dentro = True
        elif dentro:
            buf.append(linea)
    return res
