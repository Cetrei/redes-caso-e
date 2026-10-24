"""Contenedores Docker: puertos ethN y su /etc/network/interfaces tomado de hosts/hosts.md."""
import re
from ..api import http
from ..config import RAIZ, ErrorTopologia

EJEMPLO = "eth0"


def puerto(nombre):
    m = re.fullmatch(r"eth(\d+)", nombre)
    if not m:
        raise ErrorTopologia(f"puerto '{nombre}' invalido para un contenedor (se espera como {EJEMPLO})")
    return int(m.group(1)), 0


def bloques_hosts(ruta):
    """hosts.md: el primer bloque ``` bajo cada '### NOMBRE' es su /etc/network/interfaces."""
    res, actual, dentro, buf = {}, None, False, []
    for linea in (RAIZ / ruta).read_text(encoding="utf-8").splitlines():
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


def preparar(ctx, nombre, d, n):
    if "red" not in d:
        return
    redes = ctx.cache.setdefault("redes", {})
    redes.setdefault(d["red"], bloques_hosts(d["red"]))
    if nombre in redes[d["red"]]:
        http("POST", f"/projects/{ctx.pid}/nodes/{n['node_id']}/files/etc/network/interfaces",
             crudo=redes[d["red"]][nombre].encode())
        print(f"red de {nombre} escrita desde {d['red']}")
    else:
        ctx.avisos.append(f"{nombre}: no hay bloque en {d['red']}")
