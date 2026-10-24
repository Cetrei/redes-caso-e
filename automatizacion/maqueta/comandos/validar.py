"""validar: revisa topologia/ sin tocar GNS3. Corrélo antes de cada PR; construir lo corre solo y se detiene si hay errores."""
import sys
from ..config import CFG, RAIZ, ErrorTopologia
from ..tipos import TIPOS, modulo
from ..tipos.docker import bloques_hosts


def verificar():
    """Devuelve (errores, avisos) como listas de texto."""
    err, av = [], []
    plantillas, tipos = CFG.get("plantillas", {}), CFG.get("tipos", {})
    for nombre, d in CFG["nodos"].items():
        f = f"nodos/{nombre}.yml"
        alias = d.get("plantilla")
        if alias not in plantillas:
            err.append(f"{f}: la plantilla '{alias}' no esta en proyecto.yml > plantillas")
        elif alias not in tipos:
            av.append(f"{f}: falta proyecto.yml > tipos > {alias}; no se validan sus puertos")
        elif tipos[alias] not in TIPOS:
            err.append(f"proyecto.yml > tipos > {alias}: '{tipos[alias]}' no tiene modulo en maqueta/tipos/")
        for k in ("x", "y"):
            if not isinstance(d.get(k), int):
                err.append(f"{f}: '{k}' debe ser un entero (coordenada del lienzo de GNS3)")
        for k in ("config", "config_plan_b", "red"):
            if k in d and not (RAIZ / d[k]).exists():
                err.append(f"{f}: no existe {d[k]}")
        if "red" in d and (RAIZ / d["red"]).exists() and nombre not in bloques_hosts(d["red"]):
            av.append(f"{f}: {d['red']} no tiene un bloque '### {nombre}'")
    posiciones = {}
    for nombre, d in CFG["nodos"].items():
        posiciones.setdefault((d.get("x"), d.get("y")), []).append(nombre)
    for pos, nombres in posiciones.items():
        if len(nombres) > 1:
            av.append(f"{', '.join(nombres)} estan en la misma posicion {pos}")

    usados, conectados = {}, set()
    for a, pa, b, pb in CFG["enlaces"]:
        cable = f"{a} {pa} <-> {b} {pb}"
        if a == b:
            err.append(f"cable {cable}: un equipo no se conecta consigo mismo")
        for n, p in ((a, pa), (b, pb)):
            if n not in CFG["nodos"]:
                err.append(f"cable {cable}: '{n}' no tiene archivo en nodos/")
                continue
            conectados.add(n)
            tipo = tipos.get(CFG["nodos"][n].get("plantilla"))
            if tipo not in TIPOS:
                continue
            try:
                clave = (n, *modulo(tipo).puerto(p))
            except ErrorTopologia as e:
                err.append(f"cable {cable}: {e}")
                continue
            if clave in usados:
                err.append(f"el puerto {n} {p} esta en dos cables: {usados[clave]} y {cable}")
            usados[clave] = cable
    for n in CFG["nodos"]:
        if n not in conectados:
            av.append(f"{n} no tiene ningun cable en enlaces/")

    fg = CFG.get("fortigate", {})
    if fg.get("nodo") and fg["nodo"] not in CFG["nodos"]:
        err.append(f"proyecto.yml > fortigate > nodo: '{fg['nodo']}' no tiene archivo en nodos/")
    if CFG.get("plan_b") and fg.get("nodo") in CFG["nodos"] and "config_plan_b" not in CFG["nodos"][fg["nodo"]]:
        av.append(f"plan_b esta activo pero nodos/{fg['nodo']}.yml no tiene config_plan_b")
    return err, av


def validar(_):
    err, av = verificar()
    for t in err:
        print("ERROR:", t)
    for t in av:
        print("aviso:", t)
    if err:
        sys.exit(f"\n{len(err)} error(es) en topologia/")
    print(f"topologia ok: {len(CFG['nodos'])} equipos, {len(CFG['enlaces'])} cables, {len(av)} aviso(s)")


COMANDOS = {"validar": (validar, "revisa topologia/ sin tocar GNS3 (corrélo antes de cada PR)", None)}
