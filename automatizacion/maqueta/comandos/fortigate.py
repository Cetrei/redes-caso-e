"""fortigate: pega la configuracion del FortiGate por su consola telnet."""
import sys, time
from ..api import nodos, proyecto
from ..config import CFG, RAIZ
from ..consola import Consola, entrar


def fortigate(a):
    nombre = a.nodo or CFG["fortigate"]["nodo"]
    n = nodos(proyecto()).get(nombre)
    if not n:
        sys.exit(f"{nombre} no existe en el proyecto. Corre: gns3ctl.py construir")
    if n["status"] != "started":
        sys.exit(f"{nombre} no esta encendido. Corre: gns3ctl.py iniciar y espera 2 a 3 minutos.")
    c = Consola(n["console"])
    if not entrar(c, CFG["fortigate"]):
        sys.exit(f"No llegue al prompt de {nombre}. Espera a que termine de arrancar y reintenta.")
    d = CFG["nodos"][nombre]
    archivo = d["config_plan_b"] if CFG.get("plan_b") and "config_plan_b" in d else d["config"]
    print(f"usando {archivo}")
    lineas = [l.rstrip() for l in (RAIZ / archivo).read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.lstrip().startswith("#")]
    print(f"pegando {len(lineas)} lineas en {nombre} (consola {n['console']})")
    for l in lineas:
        c.enviar(l)
        time.sleep(0.15)
        c._leer(0.05)
    time.sleep(2)
    c._leer(1)
    print("hecho. Verifica con: get system status / show system interface")


def args(p):
    p.add_argument("--nodo", help="equipo FortiGate (por defecto proyecto.yml > fortigate > nodo)")


COMANDOS = {"fortigate": (fortigate, "pega configs/<FortiGate>.conf (o el plan B si plan_b: true) por su consola", args)}
