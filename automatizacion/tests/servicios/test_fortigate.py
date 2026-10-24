import unittest

from maqueta.nucleo.errores import ErrorConsola, ErrorEstado, ErrorTopologia

from tests.dobles.escenario import Escenario


class PegarConfig(unittest.TestCase):
    def setUp(self):
        self.e = Escenario()
        self.addCleanup(self.e.cerrar)
        self.e.app.constructor().construir()

    def pegar(self, equipo=None):
        self.e.salida.clear()
        self.e.app.pegador_fortigate().pegar(equipo)

    def test_pega_la_config_sin_comentarios(self):
        self.e.app.ciclo().cambiar("start")
        self.pegar()
        r = self.e.fortigate.recibido
        self.assertIn("config system interface", r)
        self.assertIn("edit port1", r)
        self.assertNotIn("# comentario", r)
        self.assertIn("usando configs/FGT-01.conf", self.e.salida)

    def test_con_plan_b_usa_la_config_del_plan_b(self):
        self.e.reemplazar("automatizacion/topologia/proyecto.yml", "plan_b: false", "plan_b: true")
        self.e.recargar()
        self.e.app.ciclo().cambiar("start")
        self.pegar()
        self.assertIn("set alias planb", self.e.fortigate.recibido)
        self.assertIn("usando configs/FGT-01-planB.conf", self.e.salida)

    def test_avisa_de_las_lineas_que_fortios_rechaza(self):
        self.e.fortigate.rechazadas = {"edit port1"}
        self.e.app.ciclo().cambiar("start")
        with self.assertRaisesRegex(ErrorConsola, "rechazo 1 linea"):
            self.pegar()
        self.assertTrue(any(s.startswith("rechazada: edit port1") for s in self.e.salida))

    def test_sin_cupo_en_la_licencia_pasa_al_plan_b(self):
        self.e.fortigate.sin_cupo = {"set alias plana"}
        self.e.app.ciclo().cambiar("start")
        self.pegar()
        self.assertIn("set alias planb", self.e.fortigate.recibido)
        self.assertTrue(any("aplico el plan B" in s for s in self.e.salida))
        self.assertIn("usando configs/FGT-01-planB.conf", self.e.salida)

    def test_sin_cupo_en_el_plan_b_ya_no_tiene_respaldo(self):
        self.e.reemplazar("automatizacion/topologia/proyecto.yml", "plan_b: false", "plan_b: true")
        self.e.recargar()
        self.e.fortigate.sin_cupo = {"set alias planb"}
        self.e.app.ciclo().cambiar("start")
        with self.assertRaisesRegex(ErrorConsola, "rechazo 1 linea"):
            self.pegar()

    def test_el_vip_en_uso_no_cuenta_como_rechazo(self):
        self.e.fortigate.en_uso = {"set extintf port1"}
        self.e.app.ciclo().cambiar("start")
        self.pegar()
        self.assertIn("hecho. Verifica con: get system status / show system interface", self.e.salida)

    def test_apagado_dice_que_hacer(self):
        with self.assertRaisesRegex(ErrorEstado, "FGT-01 no esta encendido. Corre: gns3ctl.py iniciar"):
            self.pegar()

    def test_equipo_sin_archivo_en_nodos(self):
        with self.assertRaisesRegex(ErrorTopologia, "FGT-99 no tiene archivo en nodos/"):
            self.pegar("FGT-99")

    def test_no_construido_dice_que_construir(self):
        self.e.app.ciclo().destruir()
        with self.assertRaisesRegex(Exception, "casoT no existe"):
            self.pegar()


if __name__ == "__main__":
    unittest.main()
