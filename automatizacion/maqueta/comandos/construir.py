"""construir: crea el proyecto, los equipos, su configuracion inicial y los cables. Idempotente."""
import sys
from ..api import http, nodos, plantilla_id, proyecto
from ..config import CFG
from ..contexto import Contexto
from ..tipos import modulo, puerto
from .validar import verificar


def construir(_):
    err, av = verificar()
    if err:
        sys.exit("topologia/ tiene errores, corrige antes de construir:\n  " + "\n  ".join(err))
    pid = proyecto(crear=True)
    ctx = Contexto(pid)
    existentes = nodos(pid)
    for nombre, d in CFG["nodos"].items():
        if nombre in existentes:
            continue
        tid = plantilla_id(CFG["plantillas"][d["plantilla"]])
        n = http("POST", f"/projects/{pid}/templates/{tid}", {"x": d["x"], "y": d["y"], "compute_id": "local"})
        http("PUT", f"/projects/{pid}/nodes/{n['node_id']}", {"name": nombre})
        print(f"nodo {nombre} ({n['node_type']})")
    nd = nodos(pid)

    for nombre, d in CFG["nodos"].items():
        n = nd[nombre]
        esperado = CFG.get("tipos", {}).get(d["plantilla"])
        if esperado and esperado != n["node_type"]:
            ctx.avisos.append(f"{nombre}: GNS3 lo creo como {n['node_type']} y proyecto.yml > tipos dice {esperado}")
        modulo(n["node_type"]).preparar(ctx, nombre, d, n)

    enlaces = {frozenset((l["nodes"][0]["node_id"], l["nodes"][0]["adapter_number"], l["nodes"][0]["port_number"],
                          l["nodes"][1]["node_id"], l["nodes"][1]["adapter_number"], l["nodes"][1]["port_number"]))
               for l in http("GET", f"/projects/{pid}/links")}
    for a, pa, b, pb in CFG["enlaces"]:
        ea = (nd[a]["node_id"], *puerto(nd[a]["node_type"], pa))
        eb = (nd[b]["node_id"], *puerto(nd[b]["node_type"], pb))
        if frozenset((*ea, *eb)) in enlaces:
            continue
        http("POST", f"/projects/{pid}/links", {"nodes": [
            {"node_id": ea[0], "adapter_number": ea[1], "port_number": ea[2]},
            {"node_id": eb[0], "adapter_number": eb[1], "port_number": eb[2]}]})
        print(f"enlace {a} {pa} <-> {b} {pb}")
    print(f"\nProyecto '{CFG['proyecto']}' listo: {pid}")
    for t in ctx.avisos + [f"(validar) {x}" for x in av]:
        print("AVISO:", t)


COMANDOS = {"construir": (construir, "crea proyecto, equipos, configs iniciales y cables (idempotente)", None)}
