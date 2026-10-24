import unittest

from .apoyo import Escenario


class Validacion(unittest.TestCase):
    def setUp(self):
        self.e = Escenario()
        self.addCleanup(self.e.cerrar)

    def validar(self):
        return self.e.recargar().validador().validar()

    def test_la_topologia_de_juguete_esta_limpia(self):
        informe = self.validar()
        self.assertEqual((informe.errores, informe.avisos), ((), ()))
        self.assertTrue(informe.ok)

    def test_plantilla_que_no_esta_en_proyecto(self):
        self.e.reemplazar("automatizacion/topologia/nodos/PC.yml", "cliente", "fantasma")
        self.assertIn("nodos/PC.yml: la plantilla 'fantasma' no esta en proyecto.yml > plantillas", self.validar().errores)

    def test_tipo_sin_modulo(self):
        self.e.reemplazar("automatizacion/topologia/proyecto.yml", "cliente: docker", "cliente: vpcs")
        self.assertIn("proyecto.yml > tipos > cliente: 'vpcs' no tiene modulo en maqueta/tipos/", self.validar().errores)

    def test_alias_sin_tipo_es_solo_un_aviso(self):
        self.e.reemplazar("automatizacion/topologia/proyecto.yml", ", cliente: docker}", "}")
        informe = self.validar()
        self.assertTrue(informe.ok)
        self.assertIn("nodos/PC.yml: falta proyecto.yml > tipos > cliente; no se validan sus puertos", informe.avisos)

    def test_coordenada_que_no_es_entero(self):
        self.e.reemplazar("automatizacion/topologia/nodos/R1.yml", "y: -100", "y: arriba")
        self.assertIn("nodos/R1.yml: 'y' debe ser un entero (coordenada del lienzo de GNS3)", self.validar().errores)

    def test_archivo_referenciado_que_no_existe(self):
        self.e.borrar("configs/R1.txt")
        self.assertIn("nodos/R1.yml: no existe configs/R1.txt", self.validar().errores)

    def test_equipo_sin_bloque_en_hosts_md(self):
        self.e.escribir("hosts/hosts.md", "### OTRO\n\n```\nauto eth0\n```\n")
        self.assertIn("nodos/PC.yml: hosts/hosts.md no tiene un bloque '### PC'", self.validar().avisos)

    def test_dos_equipos_en_la_misma_posicion(self):
        self.e.reemplazar("automatizacion/topologia/nodos/PC.yml", "x: 200\ny: 100", "x: 0\ny: 100")
        self.assertIn("PC, SW estan en la misma posicion (0, 100)", self.validar().avisos)

    def test_puerto_usado_en_dos_cables(self):
        self.e.escribir("automatizacion/topologia/enlaces/extra.yml", "- [R1, Gi0/1, SW, p1]\n")
        errores = self.validar().errores
        self.assertTrue(any(t.startswith("el puerto R1 Gi0/1 esta en dos cables") for t in errores), errores)

    def test_puerto_con_nombre_invalido(self):
        self.e.reemplazar("automatizacion/topologia/enlaces/red.yml", "SW, p1, PC, eth0", "SW, p1, PC, eth")
        self.assertIn("cable SW p1 <-> PC eth: puerto 'eth' invalido para un contenedor (se espera como eth0)", self.validar().errores)

    def test_cable_a_un_equipo_sin_archivo(self):
        self.e.escribir("automatizacion/topologia/enlaces/extra.yml", "- [R1, Gi0/2, R9, Gi0/0]\n")
        self.assertIn("cable R1 Gi0/2 <-> R9 Gi0/0: 'R9' no tiene archivo en nodos/", self.validar().errores)

    def test_equipo_conectado_consigo_mismo(self):
        self.e.escribir("automatizacion/topologia/enlaces/extra.yml", "- [R1, Gi0/2, R1, Gi0/3]\n")
        self.assertIn("cable R1 Gi0/2 <-> R1 Gi0/3: un equipo no se conecta consigo mismo", self.validar().errores)

    def test_equipo_sin_ningun_cable(self):
        self.e.escribir("automatizacion/topologia/nodos/R2.yml", "plantilla: router\nx: 400\ny: 400\n")
        self.assertIn("R2 no tiene ningun cable en enlaces/", self.validar().avisos)

    def test_fortigate_de_proyecto_sin_archivo(self):
        self.e.reemplazar("automatizacion/topologia/proyecto.yml", "nodo: FGT-01", "nodo: FGT-99")
        self.assertIn("proyecto.yml > fortigate > nodo: 'FGT-99' no tiene archivo en nodos/", self.validar().errores)

    def test_plan_b_sin_config_plan_b(self):
        self.e.reemplazar("automatizacion/topologia/proyecto.yml", "plan_b: false", "plan_b: true")
        self.e.reemplazar("automatizacion/topologia/nodos/FGT-01.yml", "config_plan_b: configs/FGT-01-planB.conf\n", "")
        self.assertIn("plan_b esta activo pero nodos/FGT-01.yml no tiene config_plan_b", self.validar().avisos)


if __name__ == "__main__":
    unittest.main()
