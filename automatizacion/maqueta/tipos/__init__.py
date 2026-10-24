"""Un modulo por tipo de nodo de GNS3. Cada uno define:
  puerto(nombre)               nombre de la especificacion -> (adaptador, puerto) de GNS3
  preparar(ctx, nombre, d, n)  propiedades y archivos del nodo recien creado (d = su archivo de nodos/, n = nodo de GNS3)
Para soportar un tipo nuevo: crear su modulo aca y agregarlo a TIPOS (y su alias en proyecto.yml > tipos)."""
from . import docker, dynamips, qemu, switch
from ..config import ErrorTopologia

TIPOS = {"dynamips": dynamips, "qemu": qemu, "docker": docker, "ethernet_switch": switch}


def modulo(tipo):
    if tipo not in TIPOS:
        raise ErrorTopologia(f"Tipo de nodo no soportado: {tipo}. Hay modulos para: {', '.join(TIPOS)}")
    return TIPOS[tipo]


def puerto(tipo, nombre):
    return modulo(tipo).puerto(nombre)
