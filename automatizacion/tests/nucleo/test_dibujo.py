import unittest
import xml.etree.ElementTree as ET

from maqueta.nucleo.dibujo import PALETA, Z_CAJA, Z_TEXTO, dibujos_de
from maqueta.nucleo.modelo import Nota, Proyecto, Zona


def proyecto(zonas=(), notas=()):
    return Proyecto(nombre="t", servidor="http://x", zonas=tuple(zonas), notas=tuple(notas))


WAN = Zona("WAN", -380, -470, 430, 940, "ambar", ("203.0.113.16/29", "2001:db8::/64"))


class DibujosDeZonasYNotas(unittest.TestCase):
    def claves(self, **kwargs):
        return [d.clave for d in dibujos_de(proyecto(**kwargs))]

    def test_una_zona_es_caja_titulo_y_una_linea_por_renglon(self):
        self.assertEqual(self.claves(zonas=[WAN]),
                         ["zona:WAN:caja", "zona:WAN:titulo", "zona:WAN:linea0", "zona:WAN:linea1"])

    def test_la_caja_ocupa_la_zona_y_queda_detras_del_texto(self):
        caja, titulo, *_ = dibujos_de(proyecto(zonas=[WAN]))
        self.assertEqual((caja.x, caja.y, caja.z), (-380, -470, Z_CAJA))
        self.assertLess(caja.z, titulo.z)
        self.assertEqual(titulo.z, Z_TEXTO)

    def test_el_titulo_queda_dentro_de_la_zona(self):
        _, titulo, linea, _ = dibujos_de(proyecto(zonas=[WAN]))
        self.assertGreater(titulo.x, WAN.x)
        self.assertGreater(titulo.y, WAN.y)
        self.assertGreater(linea.y, titulo.y)

    def test_la_caja_lleva_los_colores_del_tono(self):
        caja = dibujos_de(proyecto(zonas=[WAN]))[0]
        raiz = ET.fromstring(caja.svg)
        rect = raiz[0]
        self.assertEqual(rect.get("fill"), PALETA["ambar"].fondo)
        self.assertEqual(rect.get("stroke"), PALETA["ambar"].borde)
        self.assertEqual((rect.get("width"), rect.get("height")), ("430", "940"))

    def test_todo_svg_es_xml_valido_y_lleva_su_clave(self):
        notas = [Nota("a < b & c", 1, 2), Nota("x\ny", 3, 4, tono="rojo", ancho=100, alto=50, negrita=True)]
        for d in dibujos_de(proyecto(zonas=[WAN], notas=notas)):
            self.assertEqual(ET.fromstring(d.svg).get("data-maqueta"), d.clave)

    def test_el_texto_se_escapa(self):
        d = dibujos_de(proyecto(notas=[Nota("a < b & c", 1, 2)]))[0]
        self.assertIn("a &lt; b &amp; c", d.svg)

    def test_una_nota_de_varias_lineas_es_un_dibujo_por_linea(self):
        a, b = dibujos_de(proyecto(notas=[Nota("uno\ndos", 10, 20)]))
        self.assertEqual((a.clave, b.clave), ("nota:0:linea0", "nota:0:linea1"))
        self.assertEqual((a.x, a.y), (10, 20))
        self.assertGreater(b.y, a.y)

    def test_la_negrita_es_solo_de_la_primera_linea(self):
        a, b = dibujos_de(proyecto(notas=[Nota("uno\ndos", 0, 0, negrita=True)]))
        self.assertEqual(ET.fromstring(a.svg)[0].get("font-weight"), "bold")
        self.assertEqual(ET.fromstring(b.svg)[0].get("font-weight"), "normal")

    def test_una_nota_con_caja_deja_margen_y_dibuja_la_caja_primero(self):
        caja, linea = dibujos_de(proyecto(notas=[Nota("ok", 100, 200, tono="exito", ancho=170, alto=64)]))
        self.assertEqual((caja.clave, linea.clave), ("nota:0:caja", "nota:0:linea0"))
        self.assertGreater(linea.x, caja.x)
        self.assertGreater(linea.y, caja.y)
        self.assertEqual(ET.fromstring(linea.svg)[0].get("fill"), PALETA["exito"].texto)

    def test_una_nota_sin_caja_no_dibuja_caja(self):
        self.assertEqual(self.claves(notas=[Nota("solo", 0, 0)]), ["nota:0:linea0"])

    def test_las_claves_no_se_repiten(self):
        notas = [Nota("a\nb", 0, 0), Nota("a\nb", 0, 0)]
        claves = self.claves(zonas=[WAN], notas=notas)
        self.assertEqual(len(claves), len(set(claves)))

    def test_sin_zonas_ni_notas_no_hay_dibujos(self):
        self.assertEqual(dibujos_de(proyecto()), [])


if __name__ == "__main__":
    unittest.main()
