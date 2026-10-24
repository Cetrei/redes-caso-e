import unittest

from maqueta.errores import ErrorEstado, ErrorSecretos

from .apoyo import Escenario


class Licencia(unittest.TestCase):
    def setUp(self):
        self.e = Escenario()
        self.addCleanup(self.e.cerrar)
        self.e.app.constructor().construir()

    def encender(self):
        self.e.app.ciclo().cambiar("start")

    def activar(self):
        self.e.salida.clear()
        self.e.app.activador_licencia().activar()

    def nombres(self):
        return self.e.gns3.nombres()

    def test_activa_la_licencia_y_retira_el_nat(self):
        self.encender()
        self.activar()
        self.assertEqual(self.e.fortigate.licencia, "Valid")
        self.assertNotIn("NAT-licencia", self.nombres())
        self.assertIn("listo: licencia de evaluacion activa y NAT temporal retirado", self.e.salida)

    def test_manda_la_cuenta_de_forticloud_y_confirma(self):
        self.encender()
        self.activar()
        r = self.e.fortigate.recibido
        self.assertIn("execute vm-license-options account-id alumno@ejemplo.com", r)
        self.assertIn("execute vm-license-options account-password ClaveSecreta1", r)
        self.assertLess(r.index("execute vm-license"), r.index("y"))

    def test_la_clave_nunca_sale_por_pantalla(self):
        self.encender()
        self.activar()
        self.assertNotIn("ClaveSecreta1", "\n".join(self.e.salida))

    def test_el_puerto_de_salida_vuelve_a_quedar_sin_uso(self):
        self.encender()
        self.activar()
        r = self.e.fortigate.recibido
        self.assertLess(r.index("set mode dhcp"), r.index("set status down"))
        self.assertIn("unset allowaccess", r)

    def test_si_ya_es_valida_no_toca_nada(self):
        self.e.fortigate.licencia = "Valid"
        self.encender()
        self.activar()
        self.assertIn("licencia actual: Valid", self.e.salida)
        self.assertNotIn("NAT-licencia", self.nombres())
        self.assertNotIn("execute vm-license", self.e.fortigate.recibido)

    def test_sin_internet_se_detiene_antes_de_pedir_la_licencia(self):
        self.e.fortigate.internet = False
        self.encender()
        with self.assertRaisesRegex(ErrorEstado, "no tiene salida a internet por port4"):
            self.activar()
        self.assertNotIn("execute vm-license", self.e.fortigate.recibido)

    def test_con_el_fortigate_apagado_dice_que_hacer(self):
        with self.assertRaisesRegex(ErrorEstado, "FGT-01 no esta encendido. Corre: gns3ctl.py iniciar"):
            self.activar()

    def test_sin_secretos_no_toca_gns3(self):
        self.e.borrar("automatizacion/.env")
        self.e.gns3.llamadas.clear()
        with self.assertRaisesRegex(ErrorSecretos, "Falta automatizacion/.env"):
            self.activar()
        self.assertEqual(self.e.gns3.llamadas, [])

    def test_espera_el_reinicio_sin_gastar_tiempo_real(self):
        self.encender()
        self.activar()
        self.assertGreaterEqual(self.e.reloj.t, 20 + 25)
        self.assertIn("licencia despues del reinicio: Valid", self.e.salida)


if __name__ == "__main__":
    unittest.main()
