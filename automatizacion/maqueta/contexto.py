"""Estado compartido durante un `construir`: proyecto, avisos para el final y cache de archivos leidos."""


class Contexto:
    def __init__(self, pid):
        self.pid = pid
        self.avisos = []
        self.cache = {}
