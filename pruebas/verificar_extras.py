#!/usr/bin/env python3
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verificar_maqueta import SALIDA, Consola, puertos

PERDIDA = r"100% packet loss|Unreachable|unreachable"
SYSLOG = "/tmp/syslog-pcadmin.log"


def lote(consola, comandos, espera=2):
    return "\n".join(consola.linea(c, espera) for c in comandos)


def router(puerto):
    c = Consola(puerto)
    c.privilegiado("admin")
    return c


def tablas():
    esperado = {
        "R-ISP ipv4": (5000, "show ip route", [
            r"C\s+192\.0\.2\.0/24", r"C\s+198\.51\.100\.0/24", r"C\s+203\.0\.113\.0/30",
            r"S\s+203\.0\.113\.16/29 \[1/0\] via 203\.0\.113\.2"]),
        "R-ISP ipv6": (5000, "show ipv6 route", [
            r"C\s+2001:DB8:FFFF:1::/64", r"C\s+2001:DB8:FFFF:100::/64", r"C\s+2001:DB8:FFFF:200::/64",
            r"S\s+2001:DB8:105::/48 \[1/0\]\s+via 2001:DB8:FFFF:1::2"]),
        "R-EDGE ipv4": (5004, "show ip route", [
            r"S\*\s+0\.0\.0\.0/0 \[1/0\] via 203\.0\.113\.1", r"C\s+203\.0\.113\.0/30", r"C\s+203\.0\.113\.16/29"]),
        "R-EDGE ipv6": (5004, "show ipv6 route", [
            r"S\s+::/0 \[1/0\]\s+via 2001:DB8:FFFF:1::1", r"S\s+2001:DB8:105::/48 \[1/0\]\s+via 2001:DB8:105:FF01::2",
            r"C\s+2001:DB8:105:FF01::/64", r"C\s+2001:DB8:FFFF:1::/64"]),
        "R-LAN ipv4": (5007, "show ip route", [
            r"O\*E2\s+0\.0\.0\.0/0 \[110/\d+\] via 10\.50\.1\.49", r"C\s+10\.50\.0\.0/24", r"C\s+10\.50\.1\.0/27",
            r"C\s+10\.50\.1\.48/30", r"O\s+10\.50\.1\.32/28 \[110/\d+\] via 10\.50\.1\.49"]),
        "R-LAN ipv6": (5007, "show ipv6 route", [
            r"OE2 ::/0 \[110/\d+\]\s+via FE80::", r"C\s+2001:DB8:105:10::/64", r"C\s+2001:DB8:105:20::/64",
            r"C\s+2001:DB8:105:FF00::/64", r"O\s+2001:DB8:105:30::/64 \[110/\d+\]\s+via FE80::"]),
    }
    resultados = []
    for nombre, (puerto, comando, patrones) in esperado.items():
        salida = router(puerto).linea(comando, 4)
        faltan = [p for p in patrones if not re.search(p, salida)]
        resultados.append((nombre, not faltan, salida, faltan))
    return resultados


def tablas_fgt(fgt):
    v4 = fgt.fortigate(["get router info routing-table all"], 5)
    v6 = fgt.fortigate(["get router info6 routing-table"], 5)
    p4 = [r"S\*\s+0\.0\.0\.0/0 \[10/0\] via 203\.0\.113\.17, port1",
          r"S\s+10\.50\.0\.0/16 \[254/0\] is a summary, Null",
          r"O\s+10\.50\.0\.0/24 \[110/\d+\] via 10\.50\.1\.50, port2",
          r"O\s+10\.50\.1\.0/27 \[110/\d+\] via 10\.50\.1\.50, port2",
          r"C\s+10\.50\.1\.32/28 is directly connected, port3",
          r"C\s+10\.50\.1\.48/30 is directly connected, port2",
          r"C\s+203\.0\.113\.16/29 is directly connected, port1"]
    p6 = [r"S\*?\s+::/0", r"S\s+2001:db8:105::/48.*Null", r"O\s+2001:db8:105:10::/64", r"O\s+2001:db8:105:20::/64",
          r"C\s+2001:db8:105:30::/64", r"C\s+2001:db8:105:ff00::/64", r"C\s+2001:db8:105:ff01::/64"]
    return [("FGT-01 ipv4", v4, [p for p in p4 if not re.search(p, v4)]),
            ("FGT-01 ipv6", v6, [p for p in p6 if not re.search(p, v6, re.I)])]


def registros(fgt, filtro):
    return fgt.fortigate(["execute log filter reset", "execute log filter device disk", "execute log filter category 0",
                          f"execute log filter field {filtro}", "execute log display"], 6)


def main():
    p = puertos()
    pc_ext, pc_user, pc_admin = (Consola(p[n]) for n in ("PC-EXT", "PC-USER", "PC-ADMIN"))
    fgt = Consola(p["FGT-01"])
    informe, fallas = [], 0

    def anotar(tid, ok, detalle):
        nonlocal fallas
        fallas += 0 if ok else 1
        informe.append(f"[{'OK   ' if ok else 'FALLA'}] {tid:<6} {detalle}")
        print(informe[-1], flush=True)

    for nombre, ok, salida, faltan in tablas():
        anotar("R02", ok, f"{nombre}: faltan {faltan}\n{salida.strip()}")
    for nombre, salida, faltan in tablas_fgt(fgt):
        anotar("R02", not faltan, f"{nombre}: faltan {faltan}\n{salida.strip()}")

    isp, edge = router(p["R-ISP"]), router(p["R-EDGE"])
    try:
        lote(isp, ["configure terminal", "ip route 10.50.0.0 255.255.0.0 203.0.113.2", "end"])
        lote(edge, ["configure terminal", "ip route 10.50.0.0 255.255.0.0 203.0.113.18", "end"])
        time.sleep(3)
        ping = pc_ext.host("ping -c2 -W2 10.50.0.10 2>&1", 12)
        time.sleep(8)
        log = registros(fgt, "dstip 10.50.0.10")
    finally:
        lote(isp, ["configure terminal", "no ip route 10.50.0.0 255.255.0.0 203.0.113.2", "end"])
        lote(edge, ["configure terminal", "no ip route 10.50.0.0 255.255.0.0 203.0.113.18", "end"])
    llego = re.search(r'srcintf="port1".*dstip=10\.50\.0\.10.*action="deny"', log) is not None
    anotar("E02b", "100% packet loss" in ping and llego,
           f"ping con ruta filtrada: {ping[-90:]}\n        log del FGT: {'denegado en port1' if llego else log[-400:]}")
    despues = pc_ext.host("ping -c1 -W2 10.50.0.10 2>&1", 8)
    anotar("E02c", re.search(PERDIDA, despues) is not None, f"rutas temporales retiradas: {despues[-90:]}")

    try:
        lote(edge, ["clear ip access-list counters ACL-BORDE-IN"], 2)
        lote(isp, ["configure terminal", "interface Loopback99", "ip address 10.99.99.99 255.255.255.255", "no shutdown", "end"])
        ping = isp.linea("ping 203.0.113.20 source Loopback99 repeat 3 timeout 1", 10)
        acl = edge.linea("show ip access-lists ACL-BORDE-IN", 3)
        registro = edge.linea("show logging | include IPACCESSLOGP", 3)
    finally:
        lote(isp, ["configure terminal", "no interface Loopback99", "end"])
    m = re.search(r"10 deny\s+ip 10\.0\.0\.0 0\.255\.255\.255 any log \((\d+) match", acl)
    anotar("E10", bool(m and int(m[1]) > 0),
           f"ping desde 10.99.99.99: {ping.strip()[-60:]}\n        contador entrada 10 de ACL-BORDE-IN: {m[1] if m else 'sin dato'}\n{acl.strip()}\n{registro.strip()[-300:]}")

    pc_admin.host("pkill socat; rm -f " + SYSLOG)
    pc_admin.host(f"(socat -u UDP-RECV:514 OPEN:{SYSLOG},creat,append >/dev/null 2>&1 &)")
    time.sleep(2)
    pc_ext.host("ping -6 -c1 -W2 2001:db8:105:10::1 2>&1")
    pc_user.host("ping -c1 -W2 10.50.1.10 2>&1")
    pc_user.host("/usr/bin/nc -zv -w3 10.50.0.1 22 2>&1; echo rc=$?", 10)
    time.sleep(25)
    for tid, patron, que in (
            ("E16a", r'devname="FGT-01"[^<]*dstip=2001:db8:105:10::1[^<]*action="deny"', "FGT-01: E01 denegado"),
            ("E16b", r"IPACCESSLOG[A-Z]+: list ACL-SEG-USUARIOS denied", "R-LAN: E07 ACL-SEG-USUARIOS"),
            ("E16c", r"IPACCESSLOG[A-Z]+: list ACL-VTY-ADMIN denied", "R-LAN: E12 ACL-VTY-ADMIN")):
        n = pc_admin.host(f"grep -aEo '{patron}' {SYSLOG} | wc -l").strip()
        espera = time.time() + (330 if tid == "E16c" else 0)
        while not (n.isdigit() and int(n) > 0) and time.time() < espera:
            time.sleep(20)
            n = pc_admin.host(f"grep -aEo '{patron}' {SYSLOG} | wc -l").strip()
        anotar(tid, n.isdigit() and int(n) > 0, f"{que} en el syslog de PC-ADMIN: {n} mensajes")
    muestra = pc_admin.host(f"sed 's/<1[0-9][0-9]>/\\n&/g' {SYSLOG} | cut -c1-330", 6)
    pc_admin.host("pkill socat")

    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / f"extras-{datetime.now():%Y%m%d-%H%M}.txt"
    destino.write_text("\n".join(informe) + f"\n\n== Syslog recibido en PC-ADMIN ({SYSLOG}) ==\n{muestra}\n", encoding="utf-8")
    print(f"{len(informe) - fallas} de {len(informe)} OK; evidencia en {destino}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
