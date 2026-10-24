from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple
from xml.sax.saxutils import escape, quoteattr

from maqueta.nucleo.modelo import Nota, Proyecto, Zona

Z_CAJA, Z_TEXTO = -2, -1
INTERLINEA = 1.9


class Tono(NamedTuple):
    fondo: str
    borde: str
    texto: str


PALETA = {
    "neutro": Tono("#ffffff", "#9ca3af", "#1f2937"),
    "gris": Tono("#eceef3", "#c4c9d6", "#1f2937"),
    "ambar": Tono("#fdf0d8", "#dcc088", "#1f2937"),
    "verde": Tono("#dff0ea", "#98c5b4", "#1f2937"),
    "violeta": Tono("#f0e4f5", "#c7a6d4", "#1f2937"),
    "rojo": Tono("#fde4e1", "#c0392b", "#b02a1f"),
    "exito": Tono("#dcf0e4", "#2f8f4e", "#1e7a3e"),
}


@dataclass(frozen=True)
class Dibujo:
    clave: str
    svg: str
    x: int
    y: int
    z: int


@dataclass(frozen=True)
class _Caja:
    clave: str
    x: int
    y: int
    ancho: int
    alto: int
    tono: Tono


@dataclass(frozen=True)
class _Texto:
    clave: str
    texto: str
    x: int
    y: int
    tam: int
    negrita: bool
    color: str


def _caja(c: _Caja) -> Dibujo:
    svg = (f'<svg data-maqueta={quoteattr(c.clave)} height="{c.alto}" width="{c.ancho}">'
           f'<rect fill="{c.tono.fondo}" fill-opacity="1.0" height="{c.alto}" rx="14" ry="14" '
           f'stroke="{c.tono.borde}" stroke-width="2" width="{c.ancho}" /></svg>')
    return Dibujo(c.clave, svg, c.x, c.y, Z_CAJA)


def _texto(t: _Texto) -> Dibujo:
    ancho = int(len(t.texto) * t.tam * 0.8) + 10
    alto = int(t.tam * INTERLINEA)
    peso = "bold" if t.negrita else "normal"
    svg = (f'<svg data-maqueta={quoteattr(t.clave)} height="{alto}" width="{ancho}">'
           f'<text fill="{t.color}" fill-opacity="1.0" font-family="Sans Serif" font-size="{t.tam}.0" '
           f'font-weight="{peso}">{escape(t.texto)}</text></svg>')
    return Dibujo(t.clave, svg, t.x, t.y, Z_TEXTO)


def _zona(z: Zona) -> list[Dibujo]:
    tono = PALETA[z.tono]
    base = f"zona:{z.nombre}"
    dibujos = [_caja(_Caja(f"{base}:caja", z.x, z.y, z.ancho, z.alto, tono)),
               _texto(_Texto(f"{base}:titulo", z.nombre, z.x + 20, z.y + 16, 18, True, tono.texto))]
    for i, linea in enumerate(z.lineas):
        dibujos.append(_texto(_Texto(f"{base}:linea{i}", linea, z.x + 20, z.y + 56 + i * 24, 11, False, tono.texto)))
    return dibujos


def _nota(n: Nota, i: int) -> list[Dibujo]:
    tono = PALETA[n.tono]
    base = f"nota:{i}"
    dibujos, margen = [], 0
    if n.ancho is not None and n.alto is not None:
        dibujos.append(_caja(_Caja(f"{base}:caja", n.x, n.y, n.ancho, n.alto, tono)))
        margen = 12
    paso = int(n.tam * INTERLINEA)
    for j, linea in enumerate(n.texto.split("\n")):
        dibujos.append(_texto(_Texto(f"{base}:linea{j}", linea, n.x + margen, n.y + margen + j * paso,
                                     n.tam, n.negrita and j == 0, tono.texto)))
    return dibujos


def dibujos_de(proyecto: Proyecto) -> list[Dibujo]:
    zonas = [d for z in proyecto.zonas for d in _zona(z)]
    notas = [d for i, n in enumerate(proyecto.notas) for d in _nota(n, i)]
    return zonas + notas
