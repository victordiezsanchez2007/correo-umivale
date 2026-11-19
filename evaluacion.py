"""Resumen para validar el sistema con los correos de prueba.

Medir el acierto no es una capacidad del producto (lo acordamos el 12/11), sino
cómo comprobamos que funciona. Por eso va en un módulo aparte.
"""
from __future__ import annotations

from dataclasses import dataclass

from modelo import Propuesta


@dataclass
class Resumen:
    total: int
    dudosos: int
    con_respuesta: int
    aciertos: int

    @property
    def porcentaje_dudosos(self) -> float:
        return self.dudosos / self.total if self.total else 0.0

    def texto(self) -> str:
        partes = [f"{self.total} correos", f"{self.dudosos} dudosos ({self.porcentaje_dudosos:.0%})"]
        if self.con_respuesta:
            partes.append(f"coinciden con la respuesta correcta {self.aciertos} de {self.con_respuesta}")
        return " · ".join(partes)


def resumir(propuestas: list[Propuesta]) -> Resumen:
    resultados = [p.acierta() for p in propuestas]
    return Resumen(
        total=len(propuestas),
        dudosos=sum(p.dudoso for p in propuestas),
        con_respuesta=sum(r is not None for r in resultados),
        aciertos=sum(r is True for r in resultados),
    )
