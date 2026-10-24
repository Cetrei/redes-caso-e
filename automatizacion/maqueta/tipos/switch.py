from __future__ import annotations

import re

from ..gns3 import NodoGns3
from ..modelo import Nodo, Puerto
from .base import ContextoPreparacion, TipoNodo


class SwitchEthernet(TipoNodo):
    clave = "ethernet_switch"
    ejemplo = "p1"
    descripcion = "un switch"

    def puerto(self, nombre: str) -> Puerto:
        m = re.fullmatch(r"p(\d+)", nombre)
        if not m:
            raise self.puerto_invalido(nombre)
        return Puerto(0, int(m.group(1)))

    def preparar(self, ctx: ContextoPreparacion, nodo: Nodo, creado: NodoGns3) -> None:
        if not nodo.puertos:
            return
        mapa = [{"name": f"Ethernet{p.n}", "port_number": p.n, "type": p.tipo, "vlan": p.vlan} for p in nodo.puertos]
        ctx.gns3.actualizar_nodo(ctx.pid, creado.node_id, {"properties": {"ports_mapping": mapa}})
