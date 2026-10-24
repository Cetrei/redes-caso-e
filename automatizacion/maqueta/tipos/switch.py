"""Switch Ethernet de GNS3: puertos pN y modo/VLAN de cada uno (clave `puertos` del nodo)."""
import re
from ..api import http
from ..config import ErrorTopologia

EJEMPLO = "p1"


def puerto(nombre):
    m = re.fullmatch(r"p(\d+)", nombre)
    if not m:
        raise ErrorTopologia(f"puerto '{nombre}' invalido para un switch (se espera como {EJEMPLO})")
    return 0, int(m.group(1))


def preparar(ctx, nombre, d, n):
    if "puertos" in d:
        mapa = [{"name": f"Ethernet{p['n']}", "port_number": p["n"], "type": p["tipo"], "vlan": p["vlan"]} for p in d["puertos"]]
        http("PUT", f"/projects/{ctx.pid}/nodes/{n['node_id']}", {"properties": {"ports_mapping": mapa}})
