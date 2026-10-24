import unittest

from maqueta.nucleo.errores import ErrorTopologia
from maqueta.nucleo.modelo import Puerto
from maqueta.tipos import registro_por_defecto
from maqueta.tipos.dynamips import configuracion_arranque

CONFIG = """\
!
hostname R1
interface GigabitEthernet0/1
 ip address 10.0.0.1 255.255.255.0
interface Gi0/3
crypto key generate rsa modulus 2048
ip access-list extended USUARIOS
 remark 35 permit tcp any any
 remark otra nota
end
esto queda fuera
"""


class Registro(unittest.TestCase):
    def test_descubre_los_cuatro_tipos(self):
        self.assertEqual(registro_por_defecto().claves(), ["docker", "dynamips", "ethernet_switch", "qemu"])

    def test_tipo_desconocido_dice_cuales_hay(self):
        with self.assertRaisesRegex(ErrorTopologia, "Tipo de nodo no soportado: vpcs. Hay modulos para: docker, dynamips"):
            registro_por_defecto().obtener("vpcs")


class Puertos(unittest.TestCase):
    def setUp(self):
        self.r = registro_por_defecto()

    def test_router_traduce_gi0_n_al_slot_n_mas_uno(self):
        self.assertEqual(self.r.puerto("dynamips", "Gi0/0"), Puerto(1, 0))
        self.assertEqual(self.r.puerto("dynamips", "Gi0/3"), Puerto(4, 0))

    def test_fortigate_portn_es_el_adaptador_n_menos_uno(self):
        self.assertEqual(self.r.puerto("qemu", "port1"), Puerto(0, 0))
        self.assertEqual(self.r.puerto("qemu", "port4"), Puerto(3, 0))

    def test_contenedor_ethn(self):
        self.assertEqual(self.r.puerto("docker", "eth2"), Puerto(2, 0))

    def test_switch_pn_es_el_puerto_n_del_adaptador_cero(self):
        self.assertEqual(self.r.puerto("ethernet_switch", "p5"), Puerto(0, 5))

    def test_nombre_invalido_dice_como_se_escribe(self):
        casos = [("dynamips", "eth0", "un router", "Gi0/1"), ("qemu", "Gi0/1", "el FortiGate", "port1"),
                 ("docker", "p1", "un contenedor", "eth0"), ("ethernet_switch", "eth0", "un switch", "p1")]
        for tipo, nombre, quien, ejemplo in casos:
            with self.subTest(tipo=tipo):
                with self.assertRaisesRegex(ErrorTopologia, f"puerto '{nombre}' invalido para {quien} \\(se espera como {ejemplo}\\)"):
                    self.r.puerto(tipo, nombre)


class ConfiguracionDeRouter(unittest.TestCase):
    def test_traduce_interfaces_corta_en_end_y_separa_comandos_exec(self):
        config, ejecutar = configuracion_arranque(CONFIG)
        self.assertIn("interface GigabitEthernet2/0", config)
        self.assertIn("interface Gi4/0", config)
        self.assertNotIn("hostname R1\n!", config)
        self.assertNotIn("esto queda fuera", config)
        self.assertNotIn("crypto key", config)
        self.assertTrue(config.endswith("end\n"))
        self.assertEqual(ejecutar, ["crypto key generate rsa modulus 2048"])

    def test_los_remark_pasan_tal_cual(self):
        config, _ = configuracion_arranque(CONFIG)
        self.assertIn(" remark 35 permit tcp any any", config)
        self.assertIn(" remark otra nota", config)


if __name__ == "__main__":
    unittest.main()
