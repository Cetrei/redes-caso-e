"""Carga la topologia desde automatizacion/topologia/: proyecto.yml, un archivo por equipo y uno por segmento de cables."""
from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parent.parent      # automatizacion/
RAIZ = BASE.parent                                 # raiz del repo
DIR = BASE / "topologia"


class ErrorTopologia(Exception):
    """Dato mal formado en topologia/: se muestra el mensaje y el programa termina."""


def _leer(ruta):
    try:
        return yaml.safe_load(ruta.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ErrorTopologia(f"{ruta.relative_to(RAIZ)}: YAML invalido: {e}")


def cargar():
    if not (DIR / "proyecto.yml").exists():
        raise ErrorTopologia(f"Falta {DIR / 'proyecto.yml'}")
    cfg = _leer(DIR / "proyecto.yml") or {}
    cfg["nodos"], cfg["enlaces"] = {}, []
    for f in sorted((DIR / "nodos").glob("*.yml")):
        d = _leer(f) or {}
        if not isinstance(d, dict):
            raise ErrorTopologia(f"nodos/{f.name}: debe ser un mapa con plantilla, x, y...")
        cfg["nodos"][f.stem] = d             # el nombre del equipo es el nombre del archivo
    for f in sorted((DIR / "enlaces").glob("*.yml")):
        lista = _leer(f) or []
        for l in lista if isinstance(lista, list) else [lista]:
            if not (isinstance(l, list) and len(l) == 4):
                raise ErrorTopologia(f"enlaces/{f.name}: cada cable es [equipo, puerto, equipo, puerto], no {l!r}")
            cfg["enlaces"].append([str(x) for x in l])
    return cfg


CFG = cargar()
