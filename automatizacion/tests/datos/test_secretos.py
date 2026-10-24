import os
import tempfile
import unittest
from pathlib import Path

from maqueta.datos.secretos import AlmacenSecretos, leer_env
from maqueta.nucleo.errores import ErrorSecretos


class LeerEnvTest(unittest.TestCase):
    def test_ignora_comentarios_y_lineas_vacias(self):
        self.assertEqual(leer_env("# https://ejemplo.com\n\nA=1\n# B=2\n"), {"A": "1"})

    def test_quita_comillas_que_envuelven_el_valor(self):
        self.assertEqual(leer_env("A=\"uno dos\"\nB='tres'\n"), {"A": "uno dos", "B": "tres"})

    def test_el_valor_conserva_signos_iguales_y_numeral(self):
        self.assertEqual(leer_env("CLAVE=ab=c#d\n"), {"CLAVE": "ab=c#d"})


class AlmacenSecretosTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ruta = Path(self._tmp.name) / ".env"
        self.salida: list[str] = []

    def almacen(self, texto: str, modo: int = 0o600) -> AlmacenSecretos:
        self.ruta.write_text(texto, encoding="utf-8")
        os.chmod(self.ruta, modo)
        return AlmacenSecretos(self.ruta, self.salida.append)

    def test_lee_la_cuenta(self):
        cuenta = self.almacen("FORTICLOUD_CORREO=a@b.com\nFORTICLOUD_CLAVE=Clave1\n").forticloud()
        self.assertEqual((cuenta.correo, cuenta.clave), ("a@b.com", "Clave1"))
        self.assertNotIn("Clave1", repr(cuenta))

    def test_plantilla_sin_llenar_pide_llenarla(self):
        with self.assertRaisesRegex(ErrorSecretos, "llena FORTICLOUD_CORREO y FORTICLOUD_CLAVE"):
            self.almacen("FORTICLOUD_CORREO=\nFORTICLOUD_CLAVE=\n").forticloud()

    def test_avisa_si_otros_usuarios_pueden_leerlo(self):
        self.almacen("FORTICLOUD_CORREO=a@b.com\nFORTICLOUD_CLAVE=Clave1\n", modo=0o644).forticloud()
        self.assertEqual(len(self.salida), 1)
        self.assertIn("chmod 600", self.salida[0])
