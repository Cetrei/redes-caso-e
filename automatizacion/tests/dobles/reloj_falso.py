from __future__ import annotations


class RelojFalso:
    def __init__(self) -> None:
        self.t = 0.0

    def ahora(self) -> float:
        return self.t

    def dormir(self, segundos: float) -> None:
        self.t += segundos
