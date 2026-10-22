#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "paramiko"]
# ///
"""Arma y opera la maqueta del Caso E en un servidor GNS3 2.2 a partir de topologia.yml.

Es idempotente: se puede repetir cualquier subcomando sin duplicar nada.
  imagen      construye caso-e/srv-dmz en la VM (SSH) y crea su plantilla Docker
  construir   crea proyecto, nodos, switches, enlaces, configs de routers y red de los contenedores
  iniciar     enciende todos los nodos        detener   los apaga
  fortigate   pega configs/FGT-01.conf (o FGT-01-planB.conf si plan_b: true) por la consola telnet del FortiGate
  estado      lista nodos, estado y puerto de consola
  destruir    borra el proyecto
"""
import argparse, json, re, socket, sys, time, urllib.request, urllib.error
from pathlib import Path
import yaml

RAIZ = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((Path(__file__).parent / "topologia.yml").read_text(encoding="utf-8"))
API = CFG["servidor"].rstrip("/") + "/v2"


# ---------- HTTP ----------
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


# ---------- traduccion de puertos y configs ----------
def puerto(tipo, nombre):
    """Nombre de la especificacion -> (adapter_number, port_number)."""
    if tipo == "dynamips":
        m = re.fullmatch(r"Gi0/(\d)", nombre)           # Gi0/N -> slot N+1, puerto 0
        return int(m.group(1)) + 1, 0
    if tipo == "qemu":
        return int(re.fullmatch(r"port(\d+)", nombre).group(1)) - 1, 0
    if tipo == "docker":
        return int(re.fullmatch(r"eth(\d+)", nombre).group(1)), 0
    if tipo == "ethernet_switch":
        return 0, int(re.fullmatch(r"p(\d+)", nombre).group(1))
    sys.exit(f"Tipo de nodo no soportado: {tipo}")


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


# ---------- subcomandos ----------
def construir(_):
    pid = proyecto(crear=True)
    existentes = nodos(pid)
    for nombre, d in CFG["nodos"].items():
        if nombre in existentes:
            continue
        tid = plantilla_id(CFG["plantillas"][d["plantilla"]])
        n = http("POST", f"/projects/{pid}/templates/{tid}", {"x": d["x"], "y": d["y"], "compute_id": "local"})
        http("PUT", f"/projects/{pid}/nodes/{n['node_id']}", {"name": nombre})
        print(f"nodo {nombre} ({n['node_type']})")
    nd = nodos(pid)

    avisos = []
    redes = {}
    for nombre, d in CFG["nodos"].items():
        n, props = nd[nombre], {}
        if n["node_type"] == "dynamips":
            props.update(CFG["dynamips_slots"])
            if "config" in d:
                texto, ex = config_router(d["config"])
                avisos += [f"{nombre}: ejecutar por consola ya encendido: {x}" for x in ex]
                http("PUT", f"/projects/{pid}/nodes/{n['node_id']}", {"properties": props})
                props = {}
                # startup_config_content solo se acepta al crear: se escribe el archivo que Dynamips lee al arrancar
                http("POST", f"/projects/{pid}/nodes/{n['node_id']}/files/configs/i{n['properties']['dynamips_id']}_startup-config.cfg",
                     crudo=texto.encode())
                print(f"config de {nombre} escrita desde {d['config']}")
        if n["node_type"] == "ethernet_switch" and "puertos" in d:
            props["ports_mapping"] = [{"name": f"Ethernet{p['n']}", "port_number": p["n"],
                                       "type": p["tipo"], "vlan": p["vlan"]} for p in d["puertos"]]
        if props:
            http("PUT", f"/projects/{pid}/nodes/{n['node_id']}", {"properties": props})
        if n["node_type"] == "docker" and "red" in d:
            redes.setdefault(d["red"], bloques_hosts(d["red"]))
            if nombre in redes[d["red"]]:
                http("POST", f"/projects/{pid}/nodes/{n['node_id']}/files/etc/network/interfaces",
                     crudo=redes[d["red"]][nombre].encode())
                print(f"red de {nombre} escrita desde {d['red']}")
            else:
                avisos.append(f"{nombre}: no hay bloque en {d['red']}")

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
    for a in avisos:
        print("AVISO:", a)


def cambiar(accion):
    def f(_):
        pid = proyecto()
        http("POST", f"/projects/{pid}/nodes/{accion}", {})
        print(f"nodos: {accion} enviado")
    return f


def estado(_):
    pid = proyecto()
    for n in sorted(nodos(pid).values(), key=lambda n: n["name"]):
        print(f"{n['name']:<12}{n['node_type']:<16}{n['status']:<9}consola {n.get('console_host', '')}:{n.get('console', '-')}")


def destruir(_):
    http("DELETE", f"/projects/{proyecto()}")
    print("proyecto borrado")


class Consola:
    """Cliente telnet minimo (telnetlib ya no existe en Python 3.13+)."""
    def __init__(self, puerto, host="127.0.0.1"):
        self.s = socket.create_connection((host, puerto), timeout=10)
        self.buf = ""

    def _leer(self, t):
        self.s.settimeout(t)
        try:
            d = self.s.recv(4096)
        except (socket.timeout, TimeoutError):
            return False
        out, i = bytearray(), 0
        while i < len(d):
            if d[i] == 255 and i + 2 < len(d):           # IAC: rechazar toda negociacion
                if d[i + 1] in (251, 252):
                    self.s.sendall(bytes([255, 254, d[i + 2]]))
                elif d[i + 1] in (253, 254):
                    self.s.sendall(bytes([255, 252, d[i + 2]]))
                i += 3
            else:
                out.append(d[i]); i += 1
        self.buf += out.decode(errors="ignore")
        return True

    def esperar(self, patrones, timeout=120):
        fin = time.time() + timeout
        while time.time() < fin:
            for p in patrones:
                if re.search(p, self.buf):
                    r, self.buf = p, ""
                    return r
            self._leer(1)
        return None

    def enviar(self, texto):
        self.s.sendall(texto.encode() + b"\r")


def fortigate(_):
    pid = proyecto()
    n = nodos(pid)["FGT-01"]
    if n["status"] != "started":
        sys.exit("FGT-01 no esta encendido. Corre: gns3ctl.py iniciar y espera 2 a 3 minutos.")
    c = Consola(n["console"])
    c.enviar("")
    cred = CFG["fortigate"]
    for _ in range(6):
        r = c.esperar([r"login:", r"Password:", r"New Password:", r"[#$] $", r"Login incorrect"], 180)
        if r == "login:":
            c.enviar(cred["usuario"])
        elif r == "Password:":
            c.enviar(cred["clave"])
        elif r in ("New Password:",):
            sys.exit("El FortiGate pide cambiar la clave en el primer ingreso: hacelo a mano una vez y reintenta.")
        elif r == "Login incorrect":
            sys.exit("Clave del FortiGate incorrecta: ajusta fortigate.clave en topologia.yml")
        elif r:
            break
        else:
            c.enviar("")
    d = CFG["nodos"]["FGT-01"]
    archivo = d["config_plan_b"] if CFG.get("plan_b") else d["config"]
    print(f"usando {archivo}")
    lineas = [l.rstrip() for l in (RAIZ / archivo).read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.lstrip().startswith("#")]
    print(f"pegando {len(lineas)} lineas en FGT-01 (consola {n['console']})")
    for l in lineas:
        c.enviar(l)
        time.sleep(0.15)
        c._leer(0.05)
    time.sleep(2)
    c._leer(1)
    print("hecho. Verifica con: get system status / show system interface")


def imagen(_):
    import paramiko
    srv = RAIZ / "servicios"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("127.0.0.1", port=2222, username="gns3", password="gns3", allow_agent=False, look_for_keys=False)
    sftp = ssh.open_sftp()
    for ruta in sorted(p for p in srv.rglob("*") if p.is_file() and p.name != ".gitkeep"):
        rel = ruta.relative_to(srv).as_posix()
        partes = rel.split("/")[:-1]
        for i in range(len(partes)):
            try:
                sftp.mkdir("/home/gns3/servicios/" + "/".join(partes[:i + 1]))
            except OSError:
                pass
        try:
            sftp.mkdir("/home/gns3/servicios")
        except OSError:
            pass
        sftp.put(str(ruta), f"/home/gns3/servicios/{rel}")
    for etiqueta, ruta in [("caso-e/srv-dmz", "servicios"), ("caso-e/cliente", "servicios/cliente")]:
        _, o, e = ssh.exec_command(f"cd /home/gns3 && docker build -t {etiqueta} {ruta} 2>&1 | tail -15", timeout=900)
        print(o.read().decode())
    if not any(t["name"] == "SRV-DMZ-img" for t in http("GET", "/templates")):
        http("POST", "/templates", {"name": "SRV-DMZ-img", "template_type": "docker", "image": "caso-e/srv-dmz",
                                    "adapters": 1, "console_type": "telnet", "start_command": "",
                                    "compute_id": "local", "category": "guest", "symbol": ":/symbols/docker_guest.svg"})
        print("plantilla SRV-DMZ-img creada")
    if not any(t["name"] == "Cliente-caso-e" for t in http("GET", "/templates")):
        http("POST", "/templates", {"name": "Cliente-caso-e", "template_type": "docker", "image": "caso-e/cliente",
                                    "adapters": 1, "console_type": "telnet", "start_command": "",
                                    "compute_id": "local", "category": "guest", "symbol": ":/symbols/docker_guest.svg"})
        print("plantilla Cliente-caso-e creada")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nombre, fn in [("imagen", imagen), ("construir", construir), ("iniciar", cambiar("start")),
                       ("detener", cambiar("stop")), ("fortigate", fortigate), ("estado", estado),
                       ("destruir", destruir)]:
        sub.add_parser(nombre).set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)
