import unittest

from maqueta.cli import main

from tests.dobles.escenario import Escenario

ZONAS = "- {nombre: WAN, x: 0, y: 0, ancho: 100, alto: 50, tono: ambar, lineas: [\"203.0.113.16/29\"]}\n"
NOTAS = "- {texto: \"uno\\ndos\", x: 5, y: 6}\n"
ZONAS_YML = "automatizacion/topologia/zonas.yml"
NOTAS_YML = "automatizacion/topologia/notas.yml"


class Dibujar(unittest.TestCase):
    def setUp(self):
        self.e = Escenario()
        self.addCleanup(self.e.cerrar)
        self.e.escribir(ZONAS_YML, ZONAS)
        self.e.escribir(NOTAS_YML, NOTAS)
        self.e.app.constructor().construir()

    def dibujos(self):
        return self.e.gns3.dibujos[self.e.gns3.pid()]

    def aplicar(self):
        self.e.salida.clear()
        self.e.gns3.llamadas.clear()
        self.e.app.dibujos().aplicar()

    def escrituras(self):
        return [(m, r) for m, r, _ in self.e.gns3.llamadas if "/drawings" in r and m != "GET"]

    def test_crea_cada_dibujo(self):
        self.aplicar()
        self.assertEqual(len(self.dibujos()), 5)
        self.assertIn("dibujos: 5 creados, 0 actualizados, 0 retirados", self.e.salida)

    def test_es_idempotente(self):
        self.aplicar()
        self.aplicar()
        self.assertEqual(self.escrituras(), [])
        self.assertEqual(self.e.salida, ["dibujos: sin cambios"])

    def test_actualiza_lo_que_cambio_sin_duplicar(self):
        self.aplicar()
        self.e.reemplazar(ZONAS_YML, "x: 0", "x: 40")
        self.e.recargar()
        self.aplicar()
        self.assertEqual(len(self.dibujos()), 5)
        self.assertIn("dibujos: 0 creados, 3 actualizados, 0 retirados", self.e.salida)
        self.assertEqual(min(d["x"] for d in self.dibujos().values() if "zona:WAN:caja" in d["svg"]), 40)

    def test_retira_lo_que_ya_no_esta_en_los_archivos(self):
        self.aplicar()
        self.e.escribir(NOTAS_YML, "[]\n")
        self.e.recargar()
        self.aplicar()
        self.assertEqual(len(self.dibujos()), 3)
        self.assertIn("dibujos: 0 creados, 0 actualizados, 2 retirados", self.e.salida)

    def test_no_toca_lo_que_dibujaste_a_mano(self):
        pid = self.e.gns3.pid()
        self.e.gns3.solicitar("POST", f"/projects/{pid}/drawings", {"svg": "<svg><rect/></svg>", "x": 1, "y": 2, "z": 0})
        self.e.escribir(ZONAS_YML, "[]\n")
        self.e.escribir(NOTAS_YML, "[]\n")
        self.e.recargar()
        self.aplicar()
        self.assertEqual([d["svg"] for d in self.dibujos().values()], ["<svg><rect/></svg>"])

    def test_sin_zonas_ni_notas_no_hace_nada(self):
        self.e.borrar(ZONAS_YML)
        self.e.borrar(NOTAS_YML)
        self.e.recargar()
        self.aplicar()
        self.assertEqual(self.escrituras(), [])
        self.assertEqual(self.e.salida, ["dibujos: sin cambios"])

    def test_sin_el_proyecto_construido_dice_que_construir(self):
        self.e.app.ciclo().destruir()
        with self.assertRaisesRegex(Exception, "casoT no existe"):
            self.aplicar()


class ComandosQueDibujan(unittest.TestCase):
    def setUp(self):
        self.e = Escenario()
        self.addCleanup(self.e.cerrar)
        self.e.escribir(ZONAS_YML, ZONAS)
        self.e.escribir(NOTAS_YML, NOTAS)

    def dibujos(self):
        return self.e.gns3.dibujos[self.e.gns3.pid()]

    def test_construir_tambien_dibuja(self):
        self.assertEqual(main(self.e.base, ["construir"], app=self.e.app), 0)
        self.assertEqual(len(self.dibujos()), 5)

    def test_posiciones_dibuja_y_mueve_los_equipos(self):
        main(self.e.base, ["construir"], app=self.e.app)
        self.e.gns3.nodo("R1")["x"] = 999
        self.e.gns3.dibujos[self.e.gns3.pid()].clear()
        self.assertEqual(main(self.e.base, ["posiciones"], app=self.e.app), 0)
        self.assertEqual(self.e.gns3.nodo("R1")["x"], -200)
        self.assertEqual(len(self.dibujos()), 5)

    def test_posiciones_guardar_no_toca_los_dibujos(self):
        main(self.e.base, ["construir"], app=self.e.app)
        self.e.gns3.dibujos[self.e.gns3.pid()].clear()
        self.assertEqual(main(self.e.base, ["posiciones", "--guardar"], app=self.e.app), 0)
        self.assertEqual(self.dibujos(), {})


if __name__ == "__main__":
    unittest.main()
