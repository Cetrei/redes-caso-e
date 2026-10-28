#!/usr/bin/env python3
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

for _flujo in (sys.stdout, sys.stderr):
    _flujo.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "pruebas" / "evidencias"
WWW = "www.g5.eif101o.test"
CURL = "curl -{f} -s -m 6 -o /dev/null -w 'http{f}=%{{http_code}}\\n' http://" + WWW + "/"

PRUEBAS = [
    ("P01", "PC-EXT", f"dig +short +time=4 +tries=1 @203.0.113.20 {WWW} A", r"^203\.0\.113\.20$"),
    ("P02", "PC-EXT", f"dig +short +time=4 +tries=1 @203.0.113.20 {WWW} AAAA", r"^2001:db8:105:30::10$"),
    ("P03", "PC-EXT", f"dig -4 +short +time=4 +tries=1 @203.0.113.20 {WWW} A", r"^203\.0\.113\.20$"),
    ("P04", "PC-EXT", f"dig -6 +short +time=4 +tries=1 @2001:db8:105:30::10 {WWW} A", r"^203\.0\.113\.20$"),
    ("P05", "PC-EXT", CURL.format(f=4), r"http4=200"),
    ("P06", "PC-EXT", CURL.format(f=6), r"http6=200"),
    ("E01", "PC-EXT", "ping -6 -c1 -W2 2001:db8:105:10::1", r"100% packet loss"),
    ("E03", "PC-EXT", "nc -zv -w3 203.0.113.20 22 2>&1", r"timed out"),
    ("E04", "PC-ADMIN", "timeout 3 bash -c '</dev/tcp/10.50.1.34/22' && echo ssh_admin_abierto", r"ssh_admin_abierto"),
    ("E05", "PC-USER", "/usr/bin/nc -zv -w3 10.50.1.34 22 2>&1", r"timed out"),
    ("E06a", "PC-USER", f"dig +short +time=4 +tries=1 @10.50.1.34 {WWW} A", r"^10\.50\.1\.34$"),
    ("E06b", "PC-USER", CURL.format(f=4), r"http4=200"),
    ("E07", "PC-USER", "ping -c1 -W2 10.50.1.10", r"100% packet loss"),
    ("E08", "PC-ADMIN", "ping -c1 -W2 10.50.0.10", r" 1 (packets )?received"),
    ("E02", "PC-EXT", "ping -c1 -W2 10.50.0.10 2>&1", r"100% packet loss|Unreachable|unreachable"),
    ("E09", "SRV-DMZ", "ping -c1 -W2 10.50.0.10 2>&1", r"100% packet loss|Unreachable|unreachable"),
    ("E11", "PC-EXT", "curl -k -s -m 5 -o /dev/null -w 'https=%{http_code}\\n' https://203.0.113.18/", r"https=000"),
    ("E12a", "PC-USER", "/usr/bin/nc -zv -w3 10.50.0.1 22 2>&1; echo rc=$?", r"(?s)(timed out|refused).*rc=1"),
    ("E12b", "PC-ADMIN", "timeout 3 bash -c '</dev/tcp/10.50.1.1/22' && echo ssh_rlan_abierto", r"ssh_rlan_abierto"),
    ("E13a", "PC-USER", "curl -k -s -m 5 -o /dev/null -w 'gui=%{http_code}\\n' https://10.50.1.49/", r"gui=000"),
    ("E13b", "PC-ADMIN", "curl -k -s -m 5 -o /dev/null -w 'gui=%{http_code}\\n' https://10.50.1.49/", r"gui=(200|301|302|303)"),
    ("E14", "SRV-DMZ", "ping -c1 -W2 198.51.100.10 2>&1", r"100% packet loss|Unreachable|unreachable"),
    ("E15a", "PC-USER", "ping -c1 -W2 10.50.99.9 2>&1", r"100% packet loss|Unreachable|unreachable"),
    ("E15b", "PC-USER", "ping -6 -c1 -W2 2001:db8:105:99::9 2>&1", r"100% packet loss|Unreachable|unreachable"),
]


class Consola:
    def __init__(self, puerto):
        self.s = socket.create_connection(("127.0.0.1", puerto), 5)
        self.s.settimeout(1)
        self.leer(1)
        self.s.sendall(b"\x03")
        self.leer(1)

    def leer(self, segundos):
        fin, datos = time.time() + segundos, b""
        while time.time() < fin:
            try:
                d = self.s.recv(65536)
            except OSError:
                continue
            if not d:
                break
            datos += d
        texto = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", datos.decode(errors="replace")).replace("\r", "")
        return re.sub(r"EXT4-fs error[^\n]*\n", "", texto)

    def linea(self, comando, espera):
        self.s.sendall(comando.encode() + b"\r")
        return self.leer(espera)

    def host(self, comando, espera=9):
        salida = self.linea(f"echo __INI__; {comando}; echo __FIN__", espera)
        m = re.search(r"^__INI__\n(.*?)^__FIN__$", salida, re.M | re.S)
        return (m.group(1) if m else salida).strip()

    def privilegiado(self, clave):
        if self.linea("", 1).rstrip().endswith(">"):
            self.linea("enable", 2)
            self.linea(clave, 2)
        self.linea("terminal length 0", 1)

    def entrar(self, usuario, clave):
        for _ in range(3):
            pantalla = self.linea("", 2)
            if "login:" in pantalla:
                self.linea(usuario, 2)
                self.linea(clave, 4)
            elif "Password:" in pantalla:
                self.s.sendall(b"\x03")
                self.leer(1)
            else:
                return

    def fortigate(self, comandos, espera=3):
        self.entrar("admin", "Fortinet.2026")
        return "\n".join(self.linea(c, espera) for c in comandos)


def puertos():
    texto = subprocess.run(["uv", "run", str(RAIZ / "automatizacion" / "gns3ctl.py"), "estado"],
                           capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return {m[1]: int(m[2]) for m in re.finditer(r"^(\S+)\s+\S+\s+started\s+consola\s+\S+:(\d+)", texto, re.M)}


def main():
    p = puertos()
    hosts = {n: Consola(p[n]) for n in ("PC-EXT", "PC-USER", "PC-ADMIN", "SRV-DMZ")}
    fgt = Consola(p["FGT-01"])
    informe, fallas = [], 0

    def anotar(tid, ok, detalle):
        nonlocal fallas
        fallas += 0 if ok else 1
        informe.append(f"[{'OK   ' if ok else 'FALLA'}] {tid:<5} {detalle}")
        print(informe[-1], flush=True)

    for tid, nodo, cmd, patron in PRUEBAS:
        salida = hosts[nodo].host(cmd)
        anotar(tid, bool(re.search(patron, salida, re.M)), f"{nodo}: {cmd}\n        -> {salida[:300]}")

    v2 = fgt.fortigate(["get router info ospf neighbor"], 4)
    v3 = fgt.fortigate(["get router info6 ospf neighbor"], 4)
    anotar("R01", "Full" in v2 and "Full" in v3, f"vecinos OSPFv2 y OSPFv3 de FGT-01\n{v2.strip()}\n{v3.strip()}")

    http_vip = "curl -4 -s -m 6 -o /dev/null -w 'http4=%{http_code}\\n' http://203.0.113.20/"
    fgt.fortigate(["config firewall policy", "edit 1", "set status disable", "next", "end"], 2)
    caido = hosts["PC-EXT"].host(http_vip)
    fgt.fortigate(["config firewall policy", "edit 1", "set status enable", "next", "end"], 2)
    vuelto = hosts["PC-EXT"].host(http_vip)
    anotar("F01", "http4=200" not in caido and "http4=200" in vuelto,
           f"politica 1 desactivada: {caido} ; reactivada: {vuelto}")

    rlan = Consola(p["R-LAN"])
    rlan.privilegiado("admin")
    try:
        rlan.fortigate(["configure terminal", "interface GigabitEthernet1/0", "shutdown", "end"], 2)
        time.sleep(60)
        vecinos = fgt.fortigate(["get router info ospf neighbor"], 4)
        desde_afuera = hosts["PC-EXT"].host(http_vip)
        desde_lan = hosts["PC-USER"].host(CURL.format(f=4), 12)
    finally:
        rlan.fortigate(["configure terminal", "interface GigabitEthernet1/0", "no shutdown", "end"], 2)
    time.sleep(70)
    vecinos2 = fgt.fortigate(["get router info ospf neighbor"], 4)
    vuelta = hosts["PC-USER"].host(CURL.format(f=4), 12)
    caida = "Full" not in vecinos and "http4=200" in desde_afuera and "http4=200" not in desde_lan
    anotar("F02", caida and "Full" in vecinos2 and "http4=200" in vuelta,
           f"R-LAN Gi1/0 apagada: {vecinos.strip()[-160:]} ; publicacion externa {desde_afuera} ; HTTP de usuarios {desde_lan[-40:]}\n        restaurada: {vecinos2.strip()[-160:]} ; HTTP de usuarios {vuelta[-40:]}")

    time.sleep(4)
    logs = fgt.fortigate(["execute log filter device disk", "execute log filter category 0", "execute log display"], 8)
    contadores = fgt.fortigate(["diagnose firewall iprope list 100004"], 6)
    estado = fgt.fortigate(["get system status"], 5)

    SALIDA.mkdir(parents=True, exist_ok=True)
    archivo = SALIDA / f"maqueta-{datetime.now():%Y%m%d-%H%M}.txt"
    archivo.write_text("\n".join(informe) + "\n\n== Logs de trafico del FortiGate ==\n" + logs +
                       "\n\n== Politicas en el kernel (iprope) ==\n" + contadores +
                       "\n\n== Estado del FortiGate ==\n" + estado + "\n", encoding="utf-8")
    print(f"\n{len(informe) - fallas}/{len(informe)} verificaciones OK. Evidencia en {archivo}")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
