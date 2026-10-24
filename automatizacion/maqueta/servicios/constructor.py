from __future__ import annotations

from ..entorno import Entorno
from ..errores import ErrorValidacion
from ..gns3 import Extremo, NuevoNodo
from ..tipos import ContextoPreparacion
from ..validacion import Validador


class Constructor:
    def __init__(self, entorno: Entorno, validador: Validador):
        self._e = entorno
        self._gns3 = entorno.gns3
        self._p = entorno.proyecto
        self._tipos = entorno.tipos
        self._salida = entorno.salida
        self._validador = validador

    def construir(self) -> str:
        informe = self._validador.validar()
        if not informe.ok:
            raise ErrorValidacion(informe.errores)
        pid = self._gns3.abrir_proyecto(crear=True)
        ctx = ContextoPreparacion(pid, self._e)
        self._crear_nodos(pid)
        nodos = self._gns3.nodos(pid)
        self._preparar_nodos(ctx, nodos)
        self._conectar(pid, nodos)
        self._salida(f"\nProyecto '{self._p.nombre}' listo: {pid}")
        for aviso in ctx.avisos + [f"(validar) {a}" for a in informe.avisos]:
            self._salida(f"AVISO: {aviso}")
        return pid

    def _crear_nodos(self, pid: str) -> None:
        existentes = self._gns3.nodos(pid)
        for nodo in self._p.nodos.values():
            if nodo.nombre in existentes:
                continue
            nuevo = NuevoNodo(self._p.plantilla_gns3(nodo), nodo.nombre, nodo.x, nodo.y)
            creado = self._gns3.crear_nodo(pid, nuevo)
            self._salida(f"nodo {nodo.nombre} ({creado.tipo})")

    def _preparar_nodos(self, ctx: ContextoPreparacion, en_gns3: dict) -> None:
        for nodo in self._p.nodos.values():
            creado = en_gns3[nodo.nombre]
            esperado = self._p.tipo_de(nodo)
            if esperado and esperado != creado.tipo:
                ctx.avisos.append(f"{nodo.nombre}: GNS3 lo creo como {creado.tipo} y proyecto.yml > tipos dice {esperado}")
            self._tipos.obtener(creado.tipo).preparar(ctx, nodo, creado)

    def _conectar(self, pid: str, en_gns3: dict) -> None:
        existentes = self._gns3.enlaces(pid)
        for cable in self._p.enlaces:
            (a, pa), (b, pb) = cable.extremos
            ea = (en_gns3[a].node_id, self._tipos.puerto(en_gns3[a].tipo, pa))
            eb = (en_gns3[b].node_id, self._tipos.puerto(en_gns3[b].tipo, pb))
            if frozenset((Extremo(ea[0], *ea[1]), Extremo(eb[0], *eb[1]))) in existentes:
                continue
            self._gns3.conectar(pid, ea, eb)
            self._salida(f"enlace {cable}")
