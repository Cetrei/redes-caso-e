from __future__ import annotations

from typing import Any, Callable, TypeVar

from maqueta.nucleo.dibujo import PALETA
from maqueta.nucleo.errores import ErrorTopologia
from maqueta.nucleo.modelo import Nota, Zona

T = TypeVar("T")


def _entero(d: dict, campo: str) -> int:
    valor = d.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ErrorTopologia(f"'{campo}' debe ser un entero, no {valor!r}")
    return valor


def _positivo(d: dict, campo: str) -> int:
    valor = _entero(d, campo)
    if valor <= 0:
        raise ErrorTopologia(f"'{campo}' debe ser mayor que 0, no {valor}")
    return valor


def _texto(d: dict, campo: str) -> str:
    valor = d.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorTopologia(f"falta '{campo}'")
    return valor


def _tono(d: dict) -> str:
    valor = str(d.get("tono", "neutro"))
    if valor not in PALETA:
        raise ErrorTopologia(f"el tono {valor!r} no existe, usa uno de: {', '.join(PALETA)}")
    return valor


def _lineas(valor: Any) -> tuple[str, ...]:
    if valor is None:
        return ()
    if not isinstance(valor, list):
        raise ErrorTopologia(f"'lineas' debe ser una lista, no {valor!r}")
    return tuple(str(linea) for linea in valor)


def _zona(d: dict) -> Zona:
    return Zona(nombre=_texto(d, "nombre"), x=_entero(d, "x"), y=_entero(d, "y"), ancho=_positivo(d, "ancho"),
                alto=_positivo(d, "alto"), tono=_tono(d), lineas=_lineas(d.get("lineas")))


def _medida_caja(d: dict) -> tuple[int | None, int | None]:
    if ("ancho" in d) != ("alto" in d):
        raise ErrorTopologia("una caja necesita 'ancho' y 'alto' juntos")
    return (_positivo(d, "ancho"), _positivo(d, "alto")) if "ancho" in d else (None, None)


def _nota(d: dict) -> Nota:
    ancho, alto = _medida_caja(d)
    return Nota(texto=_texto(d, "texto"), x=_entero(d, "x"), y=_entero(d, "y"), tono=_tono(d), ancho=ancho, alto=alto,
                tam=_positivo(d, "tam") if "tam" in d else 10, negrita=bool(d.get("negrita", False)))


def _elementos(datos: Any, archivo: str, fabrica: Callable[[dict], T]) -> tuple[T, ...]:
    if datos is None:
        return ()
    if not isinstance(datos, list):
        raise ErrorTopologia(f"{archivo}: debe ser una lista")
    elementos = []
    for i, d in enumerate(datos):
        if not isinstance(d, dict):
            raise ErrorTopologia(f"{archivo}[{i}]: debe ser un mapa, no {d!r}")
        try:
            elementos.append(fabrica(d))
        except ErrorTopologia as e:
            raise ErrorTopologia(f"{archivo}[{i}]: {e}") from e
    return tuple(elementos)


def leer_zonas(datos: Any) -> tuple[Zona, ...]:
    zonas = _elementos(datos, "zonas.yml", _zona)
    nombres = [z.nombre for z in zonas]
    repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
    if repetidos:
        raise ErrorTopologia(f"zonas.yml: nombres repetidos: {', '.join(repetidos)}")
    return zonas


def leer_notas(datos: Any) -> tuple[Nota, ...]:
    return _elementos(datos, "notas.yml", _nota)
