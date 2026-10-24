"""El tiempo como dependencia: las esperas largas (arranque del FortiGate, reinicio por licencia) se prueban sin esperar."""
from __future__ import annotations

import time
from typing import Protocol


class Reloj(Protocol):
    def ahora(self) -> float: ...

    def dormir(self, segundos: float) -> None: ...


class RelojReal:
    def ahora(self) -> float:
        return time.monotonic()

    def dormir(self, segundos: float) -> None:
        time.sleep(segundos)
