"""Consola telnet de los nodos de GNS3 (telnetlib ya no existe en Python 3.13+) y el inicio de sesion del FortiGate."""
import re, socket, sys, time


class Consola:
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


def entrar(c, cred, espera=240, estricto=True):
    """Inicia sesion en el CLI del FortiGate. True si llega al prompt.
    Con estricto=False una clave mala devuelve False en vez de terminar el programa."""
    c.enviar("")
    for _ in range(8):
        r = c.esperar([r"login:", r"Password:", r"New Password:", r"[#$] $", r"Login incorrect"], espera)
        if r == "login:":
            c.enviar(cred["usuario"])
        elif r == "Password:":
            c.enviar(cred["clave"])
        elif r == "New Password:":
            sys.exit("El FortiGate pide cambiar la clave en el primer ingreso: hacelo a mano una vez y reintenta.")
        elif r == "Login incorrect":
            if estricto:
                sys.exit("Clave del FortiGate incorrecta: ajusta fortigate.clave en topologia/proyecto.yml")
            return False
        elif r:
            return True
        else:
            c.enviar("")
    return False
