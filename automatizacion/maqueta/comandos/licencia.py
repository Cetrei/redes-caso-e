"""licenciar: activa la licencia de evaluacion permanente del FortiGate con la cuenta FortiCloud de secretos.yml.
Sin esa licencia el FortiGate dice 'License Status: Invalid' y, segun la documentacion de Fortinet, no aplica politicas."""
import re, sys, time
import yaml
from ..api import http, nodos, plantilla_id, proyecto
from ..config import BASE, CFG
from ..consola import Consola, entrar
from ..tipos import puerto

SECRETOS = BASE / "secretos.yml"         # fuera de git (ver .gitignore); plantilla: secretos.ejemplo.yml
NAT = "NAT-licencia"


def _estado(c):
    c.buf = ""
    c.enviar("get system status")
    time.sleep(2.5)
    c._leer(1)
    m = re.search(r"License Status:\s*(\w+)", c.buf)
    return m.group(1) if m else None


def _lineas(c, lineas):
    for l in lineas:
        c.enviar(l)
        time.sleep(0.3)


def _credenciales():
    if not SECRETOS.exists():
        sys.exit(f"Falta automatizacion/{SECRETOS.name}. Copia secretos.ejemplo.yml como secretos.yml y pon tu correo y clave de FortiCloud.")
    if SECRETOS.stat().st_mode & 0o077:
        print(f"aviso: {SECRETOS.name} es legible por otros usuarios; conviene: chmod 600 {SECRETOS}")
    cf = (yaml.safe_load(SECRETOS.read_text(encoding="utf-8")) or {}).get("forticloud") or {}
    correo, clave = str(cf.get("correo") or ""), str(cf.get("clave") or "")
    if "@" not in correo or not clave or "tu_correo" in correo or clave == "tu_clave_de_forticloud":
        sys.exit(f"{SECRETOS.name}: llena forticloud.correo y forticloud.clave con los datos de tu cuenta de FortiCloud.")
    return correo, clave


def licenciar(a):
    correo, clave = _credenciales()
    nombre = a.nodo or CFG["fortigate"]["nodo"]
    salida = CFG["fortigate"].get("puerto_internet", "port4")
    adaptador = puerto("qemu", salida)[0]
    pid = proyecto()
    nd = nodos(pid)
    fgt = nd.get(nombre)
    if not fgt or fgt["status"] != "started":
        sys.exit(f"{nombre} no esta encendido. Corre: gns3ctl.py iniciar y espera 2 a 3 minutos.")
    if fgt["properties"].get("adapters", 0) <= adaptador:
        sys.exit(f"{nombre} no tiene el adaptador de {salida}.")
    c = Consola(fgt["console"])
    if not entrar(c, CFG["fortigate"]):
        sys.exit(f"No pude iniciar sesion en {nombre}.")
    _lineas(c, ["config system console", "set output standard", "end"])
    est = _estado(c)
    print(f"licencia actual: {est}")
    if est == "Valid":
        return

    # salida a internet temporal: nodo NAT de GNS3 enlazado al puerto libre del FortiGate
    nat = nd.get(NAT)
    if not nat:
        d = CFG["nodos"][nombre]
        nat = http("POST", f"/projects/{pid}/templates/{plantilla_id('NAT')}", {"x": d["x"], "y": d["y"] - 150, "compute_id": "local"})
        http("PUT", f"/projects/{pid}/nodes/{nat['node_id']}", {"name": NAT})
        http("POST", f"/projects/{pid}/links", {"nodes": [
            {"node_id": nat["node_id"], "adapter_number": 0, "port_number": 0},
            {"node_id": fgt["node_id"], "adapter_number": adaptador, "port_number": 0}]})
    http("POST", f"/projects/{pid}/nodes/{nat['node_id']}/start", {})
    _lineas(c, ["config system interface", f"edit {salida}", "set mode dhcp", "set allowaccess ping",
                "set defaultgw enable", "set status up", "next", "end"])
    print(f"{salida} en DHCP contra el NAT de GNS3; espero la direccion y pruebo salida a internet")
    time.sleep(20)
    c.buf = ""
    c.enviar("execute ping 8.8.8.8")
    time.sleep(9)
    c._leer(1)
    m = re.search(r"(\d+) packets received", c.buf)
    if not m or int(m.group(1)) == 0:
        sys.exit(f"{nombre} no tiene salida a internet por {salida} (ping a 8.8.8.8 sin respuesta). Revisa el nodo {NAT}.")
    print("salida a internet: ok")

    # los datos de FortiCloud se escriben sin imprimir lo que muestra la consola
    c.enviar(f"execute vm-license-options account-id {correo}")
    time.sleep(1)
    c.enviar(f"execute vm-license-options account-password {clave}")
    time.sleep(1)
    c.buf = ""
    c.enviar("execute vm-license")
    r = c.esperar([r"\(y/n\)", r"[Ff]ail", r"[Ee]rror"], 90)
    texto = [l for l in c.buf.splitlines() if l.strip()][-8:]
    if r != r"\(y/n\)":
        sys.exit("FortiCloud no entrego la licencia:\n  " + "\n  ".join(texto))
    c.enviar("y")
    print("licencia aceptada; el FortiGate se reinicia, espero hasta 8 minutos")

    nuevo, fin = None, time.time() + 480
    while time.time() < fin and nuevo != "Valid":
        time.sleep(25)
        try:
            c2 = Consola(fgt["console"])
            if entrar(c2, CFG["fortigate"], 40, estricto=False):
                _lineas(c2, ["config system console", "set output standard", "end"])
                nuevo = _estado(c2)
                c = c2
        except OSError:
            pass
    print(f"licencia despues del reinicio: {nuevo}")
    if nuevo != "Valid":
        sys.exit("La licencia no quedo Valid. Revisa en el FortiGate: get system status y diagnose debug vm-print-license")

    # el puerto vuelve a quedar sin uso y se quita el NAT temporal
    _lineas(c, ["config system interface", f"edit {salida}", "set mode static", "set ip 0.0.0.0 0.0.0.0",
                "unset allowaccess", "set status down", "next", "end"])
    http("DELETE", f"/projects/{pid}/nodes/{nat['node_id']}")
    print("listo: licencia de evaluacion activa y NAT temporal retirado")


def args(p):
    p.add_argument("--nodo", help="equipo FortiGate (por defecto proyecto.yml > fortigate > nodo)")


COMANDOS = {"licenciar": (licenciar, "activa la licencia de evaluacion del FortiGate con la cuenta de secretos.yml", args)}
