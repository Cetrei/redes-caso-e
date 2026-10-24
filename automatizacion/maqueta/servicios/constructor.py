"""construir: crea el proyecto, los equipos, su configuracion inicial y los cables. Idempotente."""
from __future__ import annotations

from typing import Callable

from ..errores import ErrorValidacion
from ..gns3 import ClienteGns3, Extremo
from ..modelo import Proyecto
from ..repositorio import Repositorio
from ..tipos import ContextoPreparacion, RegistroTipos
from ..validacion import Validador


class Constructor:
    def __init__(self, gns3: ClienteGns3, proyecto: Proyecto, repositorio: Repositorio, tipos: RegistroTipos,
                 validador: Validador, salida: Callable[[str], None]):
        self._gns3 = gns3
        self._p = proyecto
        self._repo = repositorio
        self._tipos = tipos
        self._validador = validador
        self._salida = salida

    def construir(self) -> str:
        """Arma la maqueta en GNS3 y devuelve el id del proyecto. Repetirlo no duplica nada."""
        informe = self._validador.validar()
        if not informe.ok:
            raise ErrorValidacion(informe.errores)
        pid = self._gns3.abrir_proyecto(crear=True)
        ctx = ContextoPreparacion(pid, self._gns3, self._p, self._repo, self._salida)
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
            creado = self._gns3.crear_nodo(pid, self._p.plantilla_gns3(nodo), nodo.nombre, nodo.x, nodo.y)
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
