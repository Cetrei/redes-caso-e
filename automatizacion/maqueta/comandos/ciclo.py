"""iniciar, detener, estado y destruir: el ciclo de vida de los nodos del proyecto."""
from ..api import http, nodos, proyecto


def cambiar(accion):
    def f(_):
        pid = proyecto()
        http("POST", f"/projects/{pid}/nodes/{accion}", {})
        print(f"nodos: {accion} enviado")
    return f


def estado(_):
    pid = proyecto()
    for n in sorted(nodos(pid).values(), key=lambda n: n["name"]):
        print(f"{n['name']:<12}{n['node_type']:<16}{n['status']:<9}consola {n.get('console_host', '')}:{n.get('console', '-')}")


def destruir(_):
    http("DELETE", f"/projects/{proyecto()}")
    print("proyecto borrado")


COMANDOS = {
    "iniciar": (cambiar("start"), "enciende todos los nodos", None),
    "detener": (cambiar("stop"), "apaga todos los nodos", None),
    "estado": (estado, "lista nodos, estado y puerto de consola", None),
    "destruir": (destruir, "borra el proyecto (el FortiGate pierde su licencia de evaluacion)", None),
}
