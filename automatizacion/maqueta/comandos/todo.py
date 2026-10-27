from __future__ import annotations

import argparse

from maqueta.comandos.base import Comando
from maqueta.datos.secretos import AlmacenSecretos
from maqueta.nucleo.errores import ErrorMaqueta

PASOS_POR_DEFECTO = ("construir", "iniciar", "licenciar")
ESPERA_ARRANQUE = 180


def _predeterminados(comando: Comando) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    comando.argumentos(parser)
    return parser.parse_args([])


def _disponibles(pasos: list[str]) -> dict[str, Comando]:
    from maqueta.comandos import descubrir

    if "destruir" in pasos:
        raise ErrorMaqueta("destruir borra el FortiGate y con el su licencia: córrelo por separado si de verdad quieres.")
    todos = {c.nombre: c for c in descubrir() if c.nombre != "todo"}
    desconocidos = [p for p in pasos if p not in todos]
    if desconocidos:
        raise ErrorMaqueta(f"subcomandos desconocidos: {', '.join(desconocidos)}")
    return todos


class Todo(Comando):
    nombre = "todo"
    ayuda = "encadena construir, iniciar y licenciar (o los pasos que indiques) esperando al FortiGate"
    orden = 80

    def argumentos(self, parser):
        parser.add_argument("pasos", nargs="*", help="subcomandos en orden; por defecto construir iniciar licenciar")

    def ejecutar(self, app, args):
        pasos = list(args.pasos) or list(PASOS_POR_DEFECTO)
        comandos = _disponibles(pasos)
        if "licenciar" in pasos:
            AlmacenSecretos(app.repositorio.base / ".env", app.salida).forticloud()
        iniciado = False
        for paso in pasos:
            app.salida(f"\n==> {paso}")
            if paso == "licenciar" and iniciado:
                app.salida("esperando el arranque del FortiGate (3 minutos)")
                app.adaptadores.reloj.dormir(ESPERA_ARRANQUE)
            comandos[paso].ejecutar(app, _predeterminados(comandos[paso]))
            iniciado = iniciado or paso == "iniciar"
        app.salida("\nlisto. No corras destruir: la licencia queda ligada a esta instancia del FortiGate.")
