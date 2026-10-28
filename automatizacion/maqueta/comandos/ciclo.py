from __future__ import annotations

from maqueta.comandos.base import Comando


class Iniciar(Comando):
    nombre = "iniciar"
    ayuda = "enciende todos los nodos"
    orden = 50

    def ejecutar(self, app, args):
        app.ciclo().cambiar("start")


class Detener(Comando):
    nombre = "detener"
    ayuda = "apaga todos los nodos"
    orden = 51

    def ejecutar(self, app, args):
        app.ciclo().cambiar("stop")


class Estado(Comando):
    nombre = "estado"
    ayuda = "lista nodos, estado y puerto de consola (telnet; con VNC, el auxiliar y el puerto vnc)"
    orden = 52

    def ejecutar(self, app, args):
        app.ciclo().estado()


class Destruir(Comando):
    nombre = "destruir"
    ayuda = "borra el proyecto (el FortiGate pierde su licencia de evaluacion)"
    orden = 53

    def ejecutar(self, app, args):
        app.ciclo().destruir()
