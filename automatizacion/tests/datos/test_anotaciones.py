import unittest

from maqueta.datos.anotaciones import leer_notas, leer_zonas
from maqueta.nucleo.errores import ErrorTopologia

from tests.dobles.escenario import Escenario

ZONA = {"nombre": "WAN", "x": -380, "y": -470, "ancho": 430, "alto": 940, "tono": "ambar", "lineas": ["203.0.113.16/29"]}


class LecturaDeZonas(unittest.TestCase):
    def test_lee_una_zona_completa(self):
        z = leer_zonas([ZONA])[0]
        self.assertEqual((z.nombre, z.x, z.y, z.ancho, z.alto, z.tono), ("WAN", -380, -470, 430, 940, "ambar"))
        self.assertEqual(z.lineas, ("203.0.113.16/29",))

    def test_sin_archivo_no_hay_zonas(self):
        self.assertEqual(leer_zonas(None), ())

    def test_las_lineas_son_opcionales(self):
        self.assertEqual(leer_zonas([{**ZONA, "lineas": None}])[0].lineas, ())

    def test_tono_desconocido_dice_cuales_hay(self):
        with self.assertRaisesRegex(ErrorTopologia, r"zonas.yml\[0\]: el tono 'azul' no existe, usa uno de: neutro, gris"):
            leer_zonas([{**ZONA, "tono": "azul"}])

    def test_falta_un_campo_dice_cual(self):
        sin_ancho = {k: v for k, v in ZONA.items() if k != "ancho"}
        with self.assertRaisesRegex(ErrorTopologia, r"zonas.yml\[0\]: 'ancho' debe ser un entero"):
            leer_zonas([sin_ancho])

    def test_medidas_no_positivas(self):
        with self.assertRaisesRegex(ErrorTopologia, "'alto' debe ser mayor que 0"):
            leer_zonas([{**ZONA, "alto": 0}])

    def test_nombres_repetidos(self):
        with self.assertRaisesRegex(ErrorTopologia, "nombres repetidos: WAN"):
            leer_zonas([ZONA, ZONA])

    def test_debe_ser_una_lista_de_mapas(self):
        with self.assertRaisesRegex(ErrorTopologia, "zonas.yml: debe ser una lista"):
            leer_zonas({"nombre": "WAN"})
        with self.assertRaisesRegex(ErrorTopologia, r"zonas.yml\[1\]: debe ser un mapa"):
            leer_zonas([ZONA, "WAN"])


class LecturaDeNotas(unittest.TestCase):
    def test_lee_una_nota_simple_con_valores_por_defecto(self):
        n = leer_notas([{"texto": "198.51.100.0/24", "x": -790, "y": -125}])[0]
        self.assertEqual((n.texto, n.x, n.y, n.tono, n.ancho, n.alto, n.tam, n.negrita),
                         ("198.51.100.0/24", -790, -125, "neutro", None, None, 10, False))

    def test_lee_una_nota_con_caja(self):
        n = leer_notas([{"texto": "ok", "x": 0, "y": 0, "tono": "exito", "ancho": 170, "alto": 64, "negrita": True, "tam": 12}])[0]
        self.assertEqual((n.tono, n.ancho, n.alto, n.tam, n.negrita), ("exito", 170, 64, 12, True))

    def test_la_caja_pide_ancho_y_alto_juntos(self):
        with self.assertRaisesRegex(ErrorTopologia, r"notas.yml\[0\]: una caja necesita 'ancho' y 'alto' juntos"):
            leer_notas([{"texto": "x", "x": 0, "y": 0, "ancho": 100}])

    def test_el_texto_es_obligatorio(self):
        with self.assertRaisesRegex(ErrorTopologia, "falta 'texto'"):
            leer_notas([{"x": 0, "y": 0}])


class CargaDesdeElRepositorio(unittest.TestCase):
    def setUp(self):
        self.e = Escenario()
        self.addCleanup(self.e.cerrar)

    def cargar(self):
        return self.e.app.repositorio.cargar()

    def test_sin_archivos_no_hay_zonas_ni_notas(self):
        p = self.cargar()
        self.assertEqual((p.zonas, p.notas), ((), ()))

    def test_lee_zonas_yml_y_notas_yml(self):
        self.e.escribir("automatizacion/topologia/zonas.yml",
                        "- {nombre: DMZ, x: 430, y: 30, ancho: 490, alto: 440, tono: violeta, lineas: [\"10.50.1.32/28\"]}\n")
        self.e.escribir("automatizacion/topologia/notas.yml", "- {texto: \"tránsito\", x: 1, y: 2}\n")
        p = self.cargar()
        self.assertEqual([z.nombre for z in p.zonas], ["DMZ"])
        self.assertEqual([n.texto for n in p.notas], ["tránsito"])

    def test_un_error_en_zonas_yml_es_de_topologia(self):
        self.e.escribir("automatizacion/topologia/zonas.yml", "- {nombre: DMZ}\n")
        with self.assertRaisesRegex(ErrorTopologia, r"zonas.yml\[0\]"):
            self.cargar()


if __name__ == "__main__":
    unittest.main()
