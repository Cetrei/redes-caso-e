import unittest

from maqueta.nucleo.errores import ErrorGns3, ErrorValidacion

from tests.dobles.escenario import Escenario


class Construccion(unittest.TestCase):
    def setUp(self):
        self.e = Escenario()
        self.addCleanup(self.e.cerrar)

    def construir(self):
        return self.e.recargar().constructor().construir()

    def test_crea_proyecto_equipos_y_cables(self):
        self.construir()
        g = self.e.gns3
        self.assertEqual([p["name"] for p in g.proyectos.values()], ["casoT"])
        self.assertEqual(g.nombres(), ["FGT-01", "PC", "R1", "SW"])
        self.assertEqual((g.nodo("R1")["x"], g.nodo("R1")["y"]), (-200, -100))
        self.assertEqual(len(g.enlaces[g.pid()]), 3)

    def test_los_cables_usan_los_puertos_traducidos(self):
        self.construir()
        g = self.e.gns3
        ids = {n["name"]: n["node_id"] for n in g.nodos[g.pid()].values()}
        esperado = {frozenset({(ids["R1"], 2, 0), (ids["FGT-01"], 0, 0)}),
                    frozenset({(ids["FGT-01"], 1, 0), (ids["SW"], 0, 0)}),
                    frozenset({(ids["SW"], 0, 1), (ids["PC"], 0, 0)})}
        real = {frozenset((n["node_id"], n["adapter_number"], n["port_number"]) for n in e["nodes"]) for e in g.enlaces[g.pid()]}
        self.assertEqual(real, esperado)

    def test_escribe_la_startup_config_del_router_traducida(self):
        self.construir()
        g = self.e.gns3
        config = g.archivo("R1", f"configs/i{g.nodo('R1')['properties']['dynamips_id']}_startup-config.cfg").decode()
        self.assertIn("interface GigabitEthernet2/0", config)
        self.assertNotIn("crypto key", config)
        self.assertEqual(g.nodo("R1")["properties"]["slot1"], "PA-GE")

    def test_escribe_la_red_del_contenedor_desde_hosts_md(self):
        self.construir()
        self.assertEqual(self.e.gns3.archivo("PC", "etc/network/interfaces").decode(), "auto eth0\niface eth0 inet static\n")

    def test_configura_los_puertos_del_switch(self):
        self.construir()
        mapa = self.e.gns3.nodo("SW")["properties"]["ports_mapping"]
        self.assertEqual([(p["name"], p["type"], p["vlan"]) for p in mapa], [("Ethernet0", "access", 1), ("Ethernet1", "access", 1)])

    def test_avisa_de_lo_que_hay_que_hacer_a_mano(self):
        self.construir()
        self.assertIn("AVISO: R1: ejecutar por consola ya encendido: crypto key generate rsa modulus 2048", self.e.salida)

    def test_equipo_sin_bloque_de_red_es_un_aviso(self):
        self.e.escribir("hosts/hosts.md", "### OTRO\n\n```\nx\n```\n")
        self.construir()
        self.assertIn("AVISO: PC: no hay bloque en hosts/hosts.md", self.e.salida)

    def test_repetirlo_no_duplica_nada(self):
        self.construir()
        antes = (self.e.gns3.nombres(), len(self.e.gns3.enlaces[self.e.gns3.pid()]))
        self.e.salida.clear()
        self.construir()
        self.assertEqual((self.e.gns3.nombres(), len(self.e.gns3.enlaces[self.e.gns3.pid()])), antes)
        self.assertEqual(len(self.e.gns3.proyectos), 1)
        self.assertFalse([t for t in self.e.salida if t.startswith(("nodo ", "enlace "))])

    def test_con_errores_de_validacion_no_toca_gns3(self):
        self.e.borrar("configs/R1.txt")
        with self.assertRaisesRegex(ErrorValidacion, "corrige antes de construir:\n  nodos/R1.yml: no existe configs/R1.txt"):
            self.construir()
        self.assertEqual(self.e.gns3.llamadas, [])

    def test_avisa_si_gns3_creo_otro_tipo_que_el_declarado(self):
        ruta = "automatizacion/topologia/proyecto.yml"
        self.e.reemplazar(ruta, "cliente: CL}", "cliente: CL, extra: CL}")
        self.e.reemplazar(ruta, "cliente: docker}", "cliente: docker, extra: ethernet_switch}")
        self.e.escribir("automatizacion/topologia/nodos/EXTRA.yml", "plantilla: extra\nx: 300\ny: 300\n")
        self.construir()
        self.assertTrue(any("EXTRA: GNS3 lo creo como docker y proyecto.yml > tipos dice ethernet_switch" in t for t in self.e.salida))


class Ciclo(unittest.TestCase):
    def setUp(self):
        self.e = Escenario()
        self.addCleanup(self.e.cerrar)
        self.e.app.constructor().construir()

    def test_iniciar_y_detener(self):
        self.e.app.ciclo().cambiar("start")
        self.assertEqual({n["status"] for n in self.e.gns3.nodos[self.e.gns3.pid()].values()}, {"started"})
        self.e.app.ciclo().cambiar("stop")
        self.assertEqual({n["status"] for n in self.e.gns3.nodos[self.e.gns3.pid()].values()}, {"stopped"})

    def test_estado_lista_los_nodos_ordenados(self):
        self.e.salida.clear()
        self.e.app.ciclo().estado()
        self.assertEqual([t.split()[0] for t in self.e.salida], ["FGT-01", "PC", "R1", "SW"])
        self.assertIn("consola 127.0.0.1:", self.e.salida[0])

    def test_estado_de_un_nodo_con_vnc_muestra_el_auxiliar_como_consola(self):
        nodo = self.e.gns3.nodo("PC")
        nodo["console_type"] = "vnc"
        nodo["properties"]["aux"] = 6001
        self.e.salida.clear()
        self.e.app.ciclo().estado()
        pc = next(t for t in self.e.salida if t.startswith("PC "))
        self.assertIn("consola 127.0.0.1:6001  vnc 127.0.0.1:", pc)

    def test_destruir_borra_el_proyecto(self):
        self.e.app.ciclo().destruir()
        self.assertEqual(self.e.gns3.proyectos, {})

    def test_sin_proyecto_el_mensaje_dice_que_hacer(self):
        self.e.app.ciclo().destruir()
        with self.assertRaisesRegex(ErrorGns3, "El proyecto casoT no existe. Corre: gns3ctl.py construir"):
            self.e.app.ciclo().estado()


class Imagenes(unittest.TestCase):
    def test_sube_servicios_construye_y_crea_la_plantilla_una_vez(self):
        e = Escenario()
        self.addCleanup(e.cerrar)
        e.app.imagenes().construir()
        self.assertEqual(e.canal.subidas, [(e.raiz / "servicios", "/home/gns3/servicios")])
        self.assertEqual(e.canal.comandos, ["cd /home/gns3 && docker build -t caso/x servicios 2>&1 | tail -15"])
        self.assertTrue(e.canal.cerrado)
        self.assertEqual([p["name"] for p in e.gns3.plantillas_creadas], ["IMG"])
        e.app.imagenes().construir()
        self.assertEqual(len(e.gns3.plantillas_creadas), 1)

    def test_la_plantilla_nace_con_la_consola_pedida(self):
        e = Escenario()
        self.addCleanup(e.cerrar)
        e.app.imagenes().construir()
        self.assertEqual(e.gns3.plantillas_creadas[0]["console_type"], "telnet")
        e2 = Escenario()
        self.addCleanup(e2.cerrar)
        e2.reemplazar("automatizacion/topologia/proyecto.yml", "plantilla: IMG}", "plantilla: IMG, consola: vnc}")
        e2.app.imagenes().construir()
        self.assertEqual(e2.gns3.plantillas_creadas[0]["console_type"], "vnc")


if __name__ == "__main__":
    unittest.main()
