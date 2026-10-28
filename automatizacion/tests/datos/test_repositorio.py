import dataclasses
import unittest

from maqueta.datos.hosts_md import bloques
from maqueta.nucleo.errores import ErrorTopologia

from tests.dobles.escenario import Escenario


class CargaDeTopologia(unittest.TestCase):
    def setUp(self):
        self.e = Escenario()
        self.addCleanup(self.e.cerrar)

    def cargar(self):
        return self.e.app.repositorio.cargar()

    def test_el_nombre_del_equipo_es_el_del_archivo(self):
        self.assertEqual(sorted(self.cargar().nodos), ["FGT-01", "PC", "R1", "SW"])

    def test_lee_posicion_config_y_puertos_del_switch(self):
        p = self.cargar()
        self.assertEqual(p.nodos["R1"].posicion, (-200, -100))
        self.assertEqual(p.nodos["R1"].config, "configs/R1.txt")
        self.assertEqual([(q.n, q.tipo, q.vlan) for q in p.nodos["SW"].puertos], [(0, "access", 1), (1, "access", 1)])

    def test_lee_cables_y_secciones_de_proyecto(self):
        p = self.cargar()
        self.assertEqual(str(p.enlaces[0]), "R1 Gi0/1 <-> FGT-01 port1")
        self.assertEqual(len(p.enlaces), 3)
        self.assertEqual((p.nombre, p.plan_b, p.fortigate.nodo, p.fortigate.puerto_internet), ("casoT", False, "FGT-01", "port4"))
        self.assertEqual(p.ssh.puerto, 2222)
        self.assertEqual(p.imagenes[0].plantilla, "IMG")

    def test_la_consola_de_la_imagen_es_telnet_salvo_que_diga_otra(self):
        self.assertEqual(self.cargar().imagenes[0].consola, "telnet")
        self.e.reemplazar("automatizacion/topologia/proyecto.yml", "plantilla: IMG}", "plantilla: IMG, consola: vnc}")
        self.assertEqual(self.cargar().imagenes[0].consola, "vnc")

    def test_el_modelo_es_inmutable(self):
        p = self.cargar()
        with self.assertRaises(TypeError):
            p.nodos["X"] = p.nodos["R1"]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            p.nodos["R1"].x = 5
        with self.assertRaises(TypeError):
            p.plantillas["router"] = "otra"

    def test_una_coordenada_que_no_es_entero_no_rompe_la_carga(self):
        self.e.reemplazar("automatizacion/topologia/nodos/R1.yml", "x: -200", "x: izquierda")
        self.assertIsNone(self.cargar().nodos["R1"].x)

    def test_config_para_prefiere_el_plan_b_solo_si_esta_activo(self):
        fgt = self.cargar().nodos["FGT-01"]
        self.assertEqual(fgt.config_para(False), "configs/FGT-01.conf")
        self.assertEqual(fgt.config_para(True), "configs/FGT-01-planB.conf")
        self.assertEqual(self.cargar().nodos["R1"].config_para(True), "configs/R1.txt")

    def test_cable_mal_formado(self):
        self.e.escribir("automatizacion/topologia/enlaces/roto.yml", "- [R1, Gi0/1, FGT-01]\n")
        with self.assertRaisesRegex(ErrorTopologia, r"enlaces/roto.yml: cada cable es \[equipo, puerto, equipo, puerto\]"):
            self.cargar()

    def test_yaml_invalido(self):
        self.e.escribir("automatizacion/topologia/nodos/R1.yml", "plantilla: [router\n")
        with self.assertRaisesRegex(ErrorTopologia, "nodos/R1.yml: YAML invalido"):
            self.cargar()

    def test_archivo_de_nodo_que_no_es_un_mapa(self):
        self.e.escribir("automatizacion/topologia/nodos/R1.yml", "- uno\n- dos\n")
        with self.assertRaisesRegex(ErrorTopologia, "nodos/R1.yml: debe ser un mapa"):
            self.cargar()

    def test_proyecto_sin_servidor(self):
        self.e.reemplazar("automatizacion/topologia/proyecto.yml", "servidor: http://127.0.0.1:3080\n", "")
        with self.assertRaisesRegex(ErrorTopologia, "proyecto.yml: falta 'servidor'"):
            self.cargar()

    def test_seccion_incompleta(self):
        self.e.reemplazar("automatizacion/topologia/proyecto.yml", "usuario: admin, ", "")
        with self.assertRaisesRegex(ErrorTopologia, "fortigate: falta 'usuario'"):
            self.cargar()

    def test_actualizar_posicion_conserva_comentarios_y_resto(self):
        self.e.app.repositorio.actualizar_posicion("FGT-01", 300, -400)
        texto = (self.e.base / "topologia/nodos/FGT-01.yml").read_text(encoding="utf-8")
        self.assertIn("# el FortiGate", texto)
        self.assertIn("x: 300\ny: -400\n", texto)
        self.assertIn("config: configs/FGT-01.conf", texto)


class LecturaDeHosts(unittest.TestCase):
    def test_primer_bloque_de_cada_equipo(self):
        md = "### A\n\n```\nuno\n```\n\n```\nsegundo\n```\n### B\n```\ndos\n```\n"
        self.assertEqual(bloques(md), {"A": "uno\n", "B": "dos\n"})

    def test_texto_fuera_de_un_equipo_se_ignora(self):
        self.assertEqual(bloques("```\nsuelto\n```\n"), {})


if __name__ == "__main__":
    unittest.main()
