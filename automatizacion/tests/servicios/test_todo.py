import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from maqueta.comandos.todo import Todo
from maqueta.nucleo.errores import ErrorMaqueta, ErrorSecretos
from tests.dobles.reloj_falso import RelojFalso


class _Paso:
    def __init__(self, nombre, registro):
        self.nombre, self._registro = nombre, registro

    def argumentos(self, parser):
        pass

    def ejecutar(self, app, args):
        self._registro.append(self.nombre)


class TodoTest(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self.carpeta.cleanup)
        self.registro, self.salida, self.reloj = [], [], RelojFalso()
        self.app = SimpleNamespace(salida=self.salida.append, adaptadores=SimpleNamespace(reloj=self.reloj),
                                   repositorio=SimpleNamespace(base=Path(self.carpeta.name)))
        pasos = [_Paso(n, self.registro) for n in ("construir", "iniciar", "licenciar", "destruir", "estado")]
        parche = mock.patch("maqueta.comandos.descubrir", return_value=pasos)
        parche.start()
        self.addCleanup(parche.stop)

    def _env(self, texto):
        (Path(self.carpeta.name) / ".env").write_text(texto, encoding="utf-8")

    def _correr(self, *pasos):
        Todo().ejecutar(self.app, SimpleNamespace(pasos=list(pasos)))

    def test_por_defecto_construye_inicia_espera_y_licencia(self):
        self._env("FORTICLOUD_CORREO=a@b.cr\nFORTICLOUD_CLAVE=x\n")
        self._correr()
        self.assertEqual(self.registro, ["construir", "iniciar", "licenciar"])
        self.assertEqual(self.reloj.t, 180)

    def test_no_espera_si_no_inicio_en_esta_corrida(self):
        self._env("FORTICLOUD_CORREO=a@b.cr\nFORTICLOUD_CLAVE=x\n")
        self._correr("licenciar")
        self.assertEqual(self.reloj.t, 0)

    def test_acepta_un_env_con_bom_y_saltos_de_windows(self):
        self._env("\ufeffFORTICLOUD_CORREO=a@b.cr\r\nFORTICLOUD_CLAVE=x\r\n")
        self._correr("licenciar")
        self.assertEqual(self.registro, ["licenciar"])

    def test_sin_env_lleno_no_hace_ningun_paso(self):
        with self.assertRaises(ErrorSecretos):
            self._correr("construir", "licenciar")
        self.assertEqual(self.registro, [])

    def test_se_niega_a_destruir(self):
        with self.assertRaises(ErrorMaqueta):
            self._correr("estado", "destruir")
        self.assertEqual(self.registro, [])

    def test_rechaza_subcomandos_desconocidos(self):
        with self.assertRaises(ErrorMaqueta):
            self._correr("volar")


if __name__ == "__main__":
    unittest.main()
