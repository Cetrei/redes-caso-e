from __future__ import annotations

from dataclasses import dataclass

from maqueta.datos import hosts_md
from maqueta.datos.repositorio import Repositorio
from maqueta.nucleo.errores import ErrorTopologia
from maqueta.nucleo.modelo import Proyecto
from maqueta.tipos import RegistroTipos


@dataclass(frozen=True)
class Informe:
    errores: tuple[str, ...]
    avisos: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errores


class _Hallazgos:
    def __init__(self) -> None:
        self.errores: list[str] = []
        self.avisos: list[str] = []

    def error(self, texto: str) -> None:
        self.errores.append(texto)

    def aviso(self, texto: str) -> None:
        self.avisos.append(texto)


class Validador:
    def __init__(self, proyecto: Proyecto, repositorio: Repositorio, tipos: RegistroTipos):
        self._p = proyecto
        self._repo = repositorio
        self._tipos = tipos

    def validar(self) -> Informe:
        h = _Hallazgos()
        for regla in (self._plantillas, self._coordenadas, self._archivos, self._posiciones_repetidas,
                      self._cables, self._nodos_sin_cable, self._fortigate):
            regla(h)
        return Informe(tuple(h.errores), tuple(h.avisos))

    def _plantillas(self, h: _Hallazgos) -> None:
        for nodo in self._p.nodos.values():
            alias = nodo.plantilla
            if alias not in self._p.plantillas:
                h.error(f"{nodo.archivo}: la plantilla '{alias}' no esta en proyecto.yml > plantillas")
            elif alias not in self._p.tipos:
                h.aviso(f"{nodo.archivo}: falta proyecto.yml > tipos > {alias}; no se validan sus puertos")
            elif self._p.tipos[alias] not in self._tipos:
                h.error(f"proyecto.yml > tipos > {alias}: '{self._p.tipos[alias]}' no tiene modulo en maqueta/tipos/")

    def _coordenadas(self, h: _Hallazgos) -> None:
        for nodo in self._p.nodos.values():
            for eje, valor in (("x", nodo.x), ("y", nodo.y)):
                if valor is None:
                    h.error(f"{nodo.archivo}: '{eje}' debe ser un entero (coordenada del lienzo de GNS3)")

    def _archivos(self, h: _Hallazgos) -> None:
        for nodo in self._p.nodos.values():
            for ruta in (nodo.config, nodo.config_plan_b, nodo.red):
                if ruta and not self._repo.existe(ruta):
                    h.error(f"{nodo.archivo}: no existe {ruta}")
            if nodo.red and self._repo.existe(nodo.red) and nodo.nombre not in hosts_md.bloques(self._repo.leer(nodo.red)):
                h.aviso(f"{nodo.archivo}: {nodo.red} no tiene un bloque '### {nodo.nombre}'")

    def _posiciones_repetidas(self, h: _Hallazgos) -> None:
        por_posicion: dict[tuple, list[str]] = {}
        for nodo in self._p.nodos.values():
            por_posicion.setdefault(nodo.posicion, []).append(nodo.nombre)
        for posicion, nombres in por_posicion.items():
            if len(nombres) > 1:
                h.aviso(f"{', '.join(nombres)} estan en la misma posicion {posicion}")

    def _cables(self, h: _Hallazgos) -> None:
        usados: dict[tuple, str] = {}
        for cable in self._p.enlaces:
            if cable.a == cable.b:
                h.error(f"cable {cable}: un equipo no se conecta consigo mismo")
            for nombre, puerto in cable.extremos:
                nodo = self._p.nodos.get(nombre)
                if nodo is None:
                    h.error(f"cable {cable}: '{nombre}' no tiene archivo en nodos/")
                    continue
                tipo = self._p.tipo_de(nodo)
                if tipo not in self._tipos:
                    continue
                try:
                    clave = (nombre, *self._tipos.puerto(tipo, puerto))
                except ErrorTopologia as e:
                    h.error(f"cable {cable}: {e}")
                    continue
                if clave in usados:
                    h.error(f"el puerto {nombre} {puerto} esta en dos cables: {usados[clave]} y {cable}")
                usados[clave] = str(cable)

    def _nodos_sin_cable(self, h: _Hallazgos) -> None:
        conectados = {nombre for cable in self._p.enlaces for nombre, _ in cable.extremos}
        for nombre in self._p.nodos:
            if nombre not in conectados:
                h.aviso(f"{nombre} no tiene ningun cable en enlaces/")

    def _fortigate(self, h: _Hallazgos) -> None:
        fg = self._p.fortigate
        if fg is None:
            return
        if fg.nodo not in self._p.nodos:
            h.error(f"proyecto.yml > fortigate > nodo: '{fg.nodo}' no tiene archivo en nodos/")
        elif self._p.plan_b and not self._p.nodos[fg.nodo].config_plan_b:
            h.aviso(f"plan_b esta activo pero nodos/{fg.nodo}.yml no tiene config_plan_b")
