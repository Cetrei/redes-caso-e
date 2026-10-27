#!/usr/bin/env python3
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verificar_maqueta import SALIDA, Consola, puertos

TRAFICO = [
    ("E01", "PC-EXT", "ping -6 -c2 -W2 2001:db8:105:10::1"),
    ("E09", "SRV-DMZ", "ping -c2 -W2 10.50.0.10"),
    ("E04", "PC-ADMIN", "timeout 3 bash -c '</dev/tcp/10.50.1.34/22' && echo ssh_admin_abierto"),
    ("E03", "PC-EXT", "nc -zv -w3 203.0.113.20 22 2>&1"),
]
POLITICAS = (1, 2, 3, 0)


def esperar_fortigate(fgt, intentos=40):
    for _ in range(intentos):
        estado = fgt.fortigate(["get system status"], 4)
        vecinos = fgt.fortigate(["get router info ospf neighbor"], 4)
        if "License Status: Valid" in estado and "Full" in vecinos:
            return estado
        time.sleep(15)
    raise SystemExit("el FortiGate no llego a licencia valida con OSPF Full")


def log_de_politica(fgt, numero):
    comandos = ["execute log filter reset", "execute log filter device disk", "execute log filter category 0",
                f"execute log filter field policyid {numero}", "execute log filter view-lines 5",
                "execute log display"]
    return fgt.fortigate(comandos, 3).split("execute log display", 1)[-1]


def main():
    p = puertos()
    hosts = {n: Consola(p[n]) for n in ("PC-EXT", "PC-USER", "PC-ADMIN", "SRV-DMZ")}
    fgt = Consola(p["FGT-01"])
    estado = esperar_fortigate(fgt)
    partes = [f"== Estado ==\n{estado}"]
    for tid, nodo, cmd in TRAFICO:
        partes.append(f"== {tid} {nodo}: {cmd} ==\n{hosts[nodo].host(cmd)}")
    time.sleep(6)
    for numero in POLITICAS:
        partes.append(f"== Log de Forward Traffic con policyid={numero} ==\n{log_de_politica(fgt, numero)}")
    partes.append("== Contadores iprope ==\n" + fgt.fortigate(["diagnose firewall iprope list 100004"], 25))
    partes.append("== Politicas ==\n" + fgt.fortigate(["show firewall policy"], 6))
    SALIDA.mkdir(parents=True, exist_ok=True)
    archivo = SALIDA / f"politicas-{datetime.now():%Y%m%d-%H%M}.txt"
    archivo.write_text("\n\n".join(partes) + "\n", encoding="utf-8")
    print(f"Evidencia en {archivo}")


if __name__ == "__main__":
    main()
