from __future__ import annotations

from maqueta.comandos.base import Comando


class _ConNodo(Comando):
    def argumentos(self, parser):
        parser.add_argument("--nodo", help="equipo FortiGate (por defecto proyecto.yml > fortigate > nodo)")


class Fortigate(_ConNodo):
    nombre = "fortigate"
    ayuda = "pega configs/<FortiGate>.conf (o el plan B si plan_b: true) por su consola"
    orden = 60

    def ejecutar(self, app, args):
        app.pegador_fortigate().pegar(args.nodo)


class Licenciar(_ConNodo):
    nombre = "licenciar"
    ayuda = "activa la licencia de evaluacion del FortiGate con la cuenta de .env"
    orden = 70

    def ejecutar(self, app, args):
        app.activador_licencia().activar(args.nodo)
