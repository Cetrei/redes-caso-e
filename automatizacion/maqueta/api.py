"""Cliente minimo de la API REST de GNS3 2.2 y las busquedas que todos los comandos repiten."""
import json, sys, urllib.request, urllib.error
from .config import CFG

API = CFG["servidor"].rstrip("/") + "/v2"


def http(metodo, ruta, cuerpo=None, crudo=None):
    datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req = urllib.request.Request(API + ruta, data=datos, method=metodo)
    if datos is not None and crudo is None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            texto = r.read().decode()
            return json.loads(texto) if texto and texto.lstrip()[0] in "[{" else texto
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR {e.code} en {metodo} {ruta}: {e.read().decode()[:1500]}")
    except urllib.error.URLError as e:
        sys.exit(f"No hay conexion con {API}: {e.reason}. Arranca la VM con gns3vm/start-gns3vm.sh")


def proyecto(crear=False):
    for p in http("GET", "/projects"):
        if p["name"] == CFG["proyecto"]:
            if p["status"] != "opened":
                http("POST", f"/projects/{p['project_id']}/open")
            return p["project_id"]
    if not crear:
        sys.exit(f"El proyecto {CFG['proyecto']} no existe. Corre: gns3ctl.py construir")
    return http("POST", "/projects", {"name": CFG["proyecto"]})["project_id"]


def nodos(pid):
    return {n["name"]: n for n in http("GET", f"/projects/{pid}/nodes")}


def plantilla_id(nombre):
    for t in http("GET", "/templates"):
        if t["name"] == nombre:
            return t["template_id"]
    sys.exit(f"No existe la plantilla '{nombre}' en el servidor.")
