"""Contenedores Docker: puertos ethN y su /etc/network/interfaces tomado de hosts/hosts.md."""
from __future__ import annotations

import re

from ..gns3 import NodoGns3
from ..modelo import Nodo, Puerto
from .base import ContextoPreparacion, TipoNodo


class Docker(TipoNodo):
    clave = "docker"
    ejemplo = "eth0"
    descripcion = "un contenedor"

    def puerto(self, nombre: str) -> Puerto:
        m = re.fullmatch(r"eth(\d+)", nombre)
        if not m:
            raise self.puerto_invalido(nombre)
        return Puerto(int(m.group(1)), 0)

    def preparar(self, ctx: ContextoPreparacion, nodo: Nodo, creado: NodoGns3) -> None:
        if not nodo.red:
            return
        interfaces = ctx.bloque_red(nodo.red, nodo.nombre)
        if interfaces is None:
            ctx.avisos.append(f"{nodo.nombre}: no hay bloque en {nodo.red}")
            return
        ctx.gns3.escribir_archivo(ctx.pid, creado.node_id, "etc/network/interfaces", interfaces.encode())
        ctx.salida(f"red de {nodo.nombre} escrita desde {nodo.red}")
