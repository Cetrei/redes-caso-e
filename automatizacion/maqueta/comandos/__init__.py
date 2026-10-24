"""Registro de subcomandos. Cada modulo define COMANDOS = {nombre: (funcion, ayuda, agregar_argumentos | None)}.
Para un comando nuevo: crear su modulo aca y agregarlo a MODULOS."""
from . import ciclo, construir, fortigate, imagen, posiciones, validar

MODULOS = [validar, imagen, construir, posiciones, ciclo, fortigate]


def todos():
    comandos = {}
    for m in MODULOS:
        comandos.update(m.COMANDOS)
    return comandos
