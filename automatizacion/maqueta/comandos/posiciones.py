"""posiciones: la posicion de cada equipo en el lienzo de GNS3 es x e y de su archivo en nodos/.
Sin opciones aplica el repo a GNS3; con --guardar copia lo que moviste en la GUI de vuelta a los archivos."""
import re
from ..api import http, nodos, proyecto
from ..config import CFG, DIR


def posiciones(a):
    pid = proyecto()
    nd = nodos(pid)
    movidos = 0
    for nombre, d in CFG["nodos"].items():
        n = nd.get(nombre)
        if not n or (n["x"], n["y"]) == (d["x"], d["y"]):
            continue
        movidos += 1
        if a.guardar:
            f = DIR / "nodos" / f"{nombre}.yml"
            t = f.read_text(encoding="utf-8")
            t = re.sub(r"(?m)^x: .*$", f"x: {n['x']}", t, count=1)
            t = re.sub(r"(?m)^y: .*$", f"y: {n['y']}", t, count=1)
            f.write_text(t, encoding="utf-8")
            print(f"{nombre}: archivo actualizado a x={n['x']} y={n['y']}")
        else:
            http("PUT", f"/projects/{pid}/nodes/{n['node_id']}", {"x": d["x"], "y": d["y"]})
            print(f"{nombre}: movido de ({n['x']}, {n['y']}) a ({d['x']}, {d['y']})")
    print("sin cambios" if not movidos else f"{movidos} equipo(s) {'guardados en nodos/' if a.guardar else 'movidos en GNS3'}")


def args(p):
    p.add_argument("--guardar", action="store_true", help="GNS3 -> repo: escribe en nodos/*.yml las posiciones actuales del lienzo")


COMANDOS = {"posiciones": (posiciones, "aplica x,y de nodos/ al lienzo de GNS3 (--guardar hace lo contrario)", args)}
