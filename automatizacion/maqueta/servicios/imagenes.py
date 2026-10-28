from __future__ import annotations

from typing import Callable

from maqueta.bordes.ssh import CanalVm
from maqueta.nucleo.modelo import ConfigSsh
from maqueta.servicios.entorno import Entorno

DESTINO = "/home/gns3/servicios"


class ConstructorImagenes:
    def __init__(self, entorno: Entorno, abrir_canal: Callable[[ConfigSsh], CanalVm]):
        self._gns3 = entorno.gns3
        self._p = entorno.proyecto
        self._repo = entorno.repositorio
        self._salida = entorno.salida
        self._abrir_canal = abrir_canal

    def construir(self) -> None:
        canal = self._abrir_canal(self._p.ssh_requerido())
        try:
            canal.subir_arbol(self._repo.servicios, DESTINO)
            for im in self._p.imagenes:
                self._salida(canal.ejecutar(f"cd /home/gns3 && docker build -t {im.etiqueta} {im.ruta} 2>&1 | tail -15", 900))
        finally:
            canal.cerrar()
        existentes = self._gns3.plantillas()
        for im in self._p.imagenes:
            if im.plantilla not in existentes:
                self._gns3.crear_plantilla_docker(im.plantilla, im.etiqueta, im.consola)
                self._salida(f"plantilla {im.plantilla} creada")
