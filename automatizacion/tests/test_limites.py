import ast
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MAX_ARCHIVO, MAX_FUNCION, MAX_ARGUMENTOS = 300, 25, 3


def _archivos() -> list[Path]:
    return sorted(p for carpeta in ("maqueta", "tests") for p in (RAIZ / carpeta).rglob("*.py") if "__pycache__" not in p.parts)


def _funciones(arbol: ast.AST):
    return [f for f in ast.walk(arbol) if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _argumentos(f) -> list[str]:
    a = f.args
    todos = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
    todos += [x.arg for x in (a.vararg, a.kwarg) if x]
    return [n for n in todos if n not in ("self", "cls")]


class LimitesDeTamano(unittest.TestCase):
    def test_hay_archivos_que_revisar(self):
        self.assertGreater(len(_archivos()), 20)

    def test_ningun_archivo_pasa_de_300_lineas(self):
        largos = [f"{p.relative_to(RAIZ)}: {len(p.read_text().splitlines())}" for p in _archivos()
                  if len(p.read_text().splitlines()) > MAX_ARCHIVO]
        self.assertEqual(largos, [])

    def test_ninguna_funcion_pasa_de_25_lineas(self):
        largas = [f"{p.relative_to(RAIZ)}: {f.name} ({f.end_lineno - f.lineno + 1})"
                  for p in _archivos() for f in _funciones(ast.parse(p.read_text()))
                  if f.end_lineno - f.lineno + 1 > MAX_FUNCION]
        self.assertEqual(largas, [])

    def test_ninguna_funcion_recibe_mas_de_3_argumentos(self):
        anchas = [f"{p.relative_to(RAIZ)}: {f.name} {_argumentos(f)}"
                  for p in _archivos() for f in _funciones(ast.parse(p.read_text()))
                  if len(_argumentos(f)) > MAX_ARGUMENTOS]
        self.assertEqual(anchas, [])


if __name__ == "__main__":
    unittest.main()
