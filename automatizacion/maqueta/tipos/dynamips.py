"""Routers Dynamips c7200: puertos GigabitEthernet(N+1)/0 y startup-config escrita como archivo."""
from __future__ import annotations

import re

from ..gns3 import NodoGns3
from ..modelo import Nodo, Puerto
from .base import ContextoPreparacion, TipoNodo


def configuracion_arranque(texto: str, plan_b: bool) -> tuple[str, list[str]]:
    """Config de IOS lista para startup-config: sin comentarios, hasta el primer 'end', Gi0/N -> Gi(N+1)/0.

    Devuelve (config, comandos_exec): los comandos de modo exec (crypto key generate) no caben en la
    startup y hay que correrlos por consola con el router ya encendido."""
    salida, comandos_exec = [], []
    for linea in texto.splitlines():
        s = linea.strip()
        if s.startswith("!") or not s:
            continue
        if s.startswith("crypto key generate"):
            comandos_exec.append(s)
            continue
        if plan_b:   # plan B: se activan las lineas 35 de las ACL de usuarios, que el archivo trae como remark
            linea = re.sub(r"^(\s*)remark ((?:sequence )?35 )", r"\1\2", linea)
        salida.append(linea.rstrip())
        if s == "end":
            break
    config = "\n".join(salida) + "\n"
    config = re.sub(r"\b(GigabitEthernet|Gi)0/(\d)", lambda m: f"{m.group(1)}{int(m.group(2)) + 1}/0", config)
    return config, comandos_exec


class Dynamips(TipoNodo):
    clave = "dynamips"
    ejemplo = "Gi0/1"
    descripcion = "un router"

    def puerto(self, nombre: str) -> Puerto:
        m = re.fullmatch(r"Gi0/(\d)", nombre)               # Gi0/N -> slot N+1, puerto 0
        if not m:
            raise self.puerto_invalido(nombre)
        return Puerto(int(m.group(1)) + 1, 0)

    def preparar(self, ctx: ContextoPreparacion, nodo: Nodo, creado: NodoGns3) -> None:
        ctx.gns3.actualizar_nodo(ctx.pid, creado.node_id, {"properties": dict(ctx.proyecto.dynamips_slots)})
        if not nodo.config:
            return
        config, comandos_exec = configuracion_arranque(ctx.repositorio.leer(nodo.config), ctx.proyecto.plan_b)
        ctx.avisos += [f"{nodo.nombre}: ejecutar por consola ya encendido: {c}" for c in comandos_exec]
        # startup_config_content solo se acepta al crear: se escribe el archivo que Dynamips lee al arrancar
        ctx.gns3.escribir_archivo(ctx.pid, creado.node_id,
                                  f"configs/i{creado.propiedades['dynamips_id']}_startup-config.cfg", config.encode())
        ctx.salida(f"config de {nodo.nombre} escrita desde {nodo.config}")
