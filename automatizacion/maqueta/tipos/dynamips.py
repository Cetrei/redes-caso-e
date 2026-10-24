"""Routers Dynamips c7200: puertos GigabitEthernet(N+1)/0 y startup-config escrita como archivo."""
import re
from ..api import http
from ..config import CFG, RAIZ, ErrorTopologia

EJEMPLO = "Gi0/1"


def puerto(nombre):
    m = re.fullmatch(r"Gi0/(\d)", nombre)               # Gi0/N -> slot N+1, puerto 0
    if not m:
        raise ErrorTopologia(f"puerto '{nombre}' invalido para un router (se espera como {EJEMPLO})")
    return int(m.group(1)) + 1, 0


def config_router(ruta):
    """Config de IOS lista para startup-config: sin comentarios, hasta el primer 'end', Gi0/N -> Gi(N+1)/0.
    Devuelve (texto, lineas_exec) donde lineas_exec son comandos de modo exec que no caben en la startup."""
    salida, exec_ = [], []
    for linea in (RAIZ / ruta).read_text(encoding="utf-8").splitlines():
        s = linea.strip()
        if s.startswith("!") or not s:
            continue
        if s.startswith("crypto key generate"):
            exec_.append(s)
            continue
        if CFG.get("plan_b"):   # plan B: se activan las lineas 35 de las ACL de usuarios, que el archivo trae como remark
            linea = re.sub(r"^(\s*)remark ((?:sequence )?35 )", r"\1\2", linea)
        salida.append(linea.rstrip())
        if s == "end":
            break
    texto = "\n".join(salida) + "\n"
    texto = re.sub(r"\b(GigabitEthernet|Gi)0/(\d)", lambda m: f"{m.group(1)}{int(m.group(2)) + 1}/0", texto)
    return texto, exec_


def preparar(ctx, nombre, d, n):
    http("PUT", f"/projects/{ctx.pid}/nodes/{n['node_id']}", {"properties": dict(CFG["dynamips_slots"])})
    if "config" in d:
        texto, ex = config_router(d["config"])
        ctx.avisos += [f"{nombre}: ejecutar por consola ya encendido: {x}" for x in ex]
        # startup_config_content solo se acepta al crear: se escribe el archivo que Dynamips lee al arrancar
        http("POST", f"/projects/{ctx.pid}/nodes/{n['node_id']}/files/configs/i{n['properties']['dynamips_id']}_startup-config.cfg",
             crudo=texto.encode())
        print(f"config de {nombre} escrita desde {d['config']}")
