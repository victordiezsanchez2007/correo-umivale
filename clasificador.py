"""Clasificador por reglas: propone categoría y destino, y detecta los dudosos.

Cómo decide (en resumen, para poder explicarlo):
1. Busca palabras y frases típicas de cada categoría en el asunto, en el cuerpo
   y en el nombre de los adjuntos. Cada coincidencia suma puntos: más si está en
   el asunto o en el adjunto, y más cuanto más larga es la frase.
2. La categoría con más puntos es la propuesta. La confianza baja si otra
   categoría le va cerca o si hay muy pocas pistas.
3. El destino sale de la categoría: la DT del remitente (según el listado) o una
   dirección central.
4. Si algo no cuadra, el correo se marca como dudoso y se explica por qué.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from modelo import (
    ARCHIVO,
    DIR_ATENCION_CLIENTE,
    DIR_JURIDICA,
    DIR_MEDICA,
    DIR_ORGANIZACION,
    DIR_PRESTACIONES,
    DIR_TECNOLOGIA,
    Categoria,
    Correo,
    Destino,
    Propuesta,
    Remitente,
    TipoRemitente,
    normalizar,
)

# Palabras clave en minúsculas. Al comparar se quitan las tildes de ambos lados.
PALABRAS_CLAVE: dict[Categoria, list[str]] = {
    Categoria.BAJAS: [
        "baja", "parte de baja", "parte baja", "parte de alta", "parte alta",
        "alta médica", "parte de confirmación", "parte confirmación", "confirmación",
        "incapacidad temporal", "accidente de trabajo", "accidente laboral",
    ],
    Categoria.ASISTENCIA: [
        "cita", "consulta médica", "informe médico", "rehabilitación", "fisioterapia",
        "resonancia", "prueba médica", "especialista", "traumatólogo", "hospital",
        "ingreso", "ingresado", "ingreso hospitalario", "secuelas", "centro concertado",
    ],
    Categoria.PRESTACIONES: [
        "pago", "pago directo", "pago directo de la baja", "prestación", "cobrar",
        "cobrado", "no he cobrado", "pagáis", "riesgo durante el embarazo", "lactancia",
        "cuidado de menores", "cese de actividad",
    ],
    Categoria.EMPRESAS: [
        "certificado", "estar al corriente", "adhesión", "cobertura", "empresa asociada",
        "licitación", "trabajadores de la empresa",
    ],
    Categoria.RECLAMACIONES: [
        "reclamación", "queja", "quejarme", "inaceptable", "hoja de reclamaciones",
        "nadie me contesta", "mal atendido", "indignado",
    ],
    Categoria.NO_RELEVANTE: [
        "descuento", "oferta", "promoción", "publicidad", "newsletter", "webinar",
        "darte de baja", "darse de baja", "recibir más correos",
    ],
}

# «Asuntos internos o de terceros» se divide en tres tipos, cada uno con su dirección.
INTERNOS: dict[str, tuple[Destino, list[str]]] = {
    "judicial": (DIR_JURIDICA, [
        "requerimiento judicial", "juzgado", "procedimiento", "tribunal", "oficio",
        "diligencia",
    ]),
    "proveedores": (DIR_ORGANIZACION, ["factura", "proveedor", "presupuesto", "albarán", "pedido"]),
    "tecnologia": (DIR_TECNOLOGIA, [
        "web", "aplicación", "app", "contraseña", "no puedo acceder", "error al entrar",
    ]),
}

# Palabras que mandan la asistencia sanitaria a Dir. Médica en vez de a la DT.
PALABRAS_DIR_MEDICA = ["hospital", "ingreso", "ingresado", "especialista", "traumatólogo",
                       "secuelas", "centro concertado"]

# Peso de cada parte del correo.
PESO_ASUNTO = 2
PESO_ADJUNTO = 2
PESO_CUERPO = 1

UMBRAL_POR_DEFECTO = 0.6     # por debajo, el correo es dudoso
PUNTOS_SUFICIENTES = 3       # con menos puntos hay «poca información»
MARGEN_CONTRADICCION = 0.75  # si la 2.ª categoría tiene el 75 % de puntos de la 1.ª


@dataclass
class Pista:
    """Una palabra encontrada, para poder explicar la decisión."""

    frase: str
    campo: str
    puntos: int


def _contiene(texto: str, frase: str) -> bool:
    """¿Aparece la frase como palabras completas? (el texto ya viene normalizado)"""
    return re.search(rf"\b{re.escape(normalizar(frase))}\b", texto) is not None


def _texto_adjuntos(adjuntos: list[str]) -> str:
    # «parte_baja.pdf» -> «parte baja pdf»
    return normalizar(" ".join(re.sub(r"[_\-.]+", " ", a) for a in adjuntos))


class ClasificadorPorReglas:
    def __init__(self, remitentes: dict[str, Remitente], umbral: float = UMBRAL_POR_DEFECTO):
        self.remitentes = remitentes
        self.umbral = umbral

    # ---------- puntuación ----------

    @staticmethod
    def _palabras_de(categoria: Categoria) -> list[str]:
        if categoria is Categoria.INTERNOS:
            return [p for _, palabras in INTERNOS.values() for p in palabras]
        return PALABRAS_CLAVE[categoria]

    def _puntuar(self, campos: dict[str, tuple[str, int]]) -> dict[Categoria, list[Pista]]:
        """Para cada categoría, las pistas encontradas en los campos indicados."""
        pistas: dict[Categoria, list[Pista]] = {c: [] for c in Categoria}
        for categoria in Categoria:
            for frase in self._palabras_de(categoria):
                for campo, (texto, peso) in campos.items():
                    if _contiene(texto, frase):
                        pistas[categoria].append(Pista(frase, campo, peso * len(frase.split())))
        return pistas

    @staticmethod
    def _total(pistas: list[Pista]) -> int:
        return sum(p.puntos for p in pistas)

    @staticmethod
    def _mejor(pistas: dict[Categoria, list[Pista]]) -> Categoria | None:
        puntos = {c: sum(p.puntos for p in ps) for c, ps in pistas.items()}
        mejor = max(puntos, key=puntos.get)
        return mejor if puntos[mejor] > 0 else None

    # ---------- destino ----------

    def _destino(self, categoria: Categoria, remitente: Remitente | None, texto: str) -> tuple[Destino | None, bool]:
        """Devuelve (destino, necesita_dt)."""
        if categoria is Categoria.PRESTACIONES:
            return DIR_PRESTACIONES, False
        if categoria is Categoria.RECLAMACIONES:
            return DIR_ATENCION_CLIENTE, False
        if categoria is Categoria.NO_RELEVANTE:
            return ARCHIVO, False
        if categoria is Categoria.INTERNOS:
            destino, _ = max(INTERNOS.values(), key=lambda d: sum(_contiene(texto, p) for p in d[1]))
            return destino, False
        if categoria is Categoria.ASISTENCIA and any(_contiene(texto, p) for p in PALABRAS_DIR_MEDICA):
            return DIR_MEDICA, False
        # Bajas, empresas y asistencia normal: la DT de quien escribe.
        return (remitente.delegacion if remitente else None), True

    # ---------- clasificación ----------

    def clasificar(self, correo: Correo) -> Propuesta:
        asunto = normalizar(correo.asunto)
        cuerpo = normalizar(correo.cuerpo)
        adjuntos = _texto_adjuntos(correo.adjuntos)
        remitente = self.remitentes.get(correo.remitente)

        pistas = self._puntuar({
            "asunto": (asunto, PESO_ASUNTO),
            "cuerpo": (cuerpo, PESO_CUERPO),
            "adjunto": (adjuntos, PESO_ADJUNTO),
        })
        if remitente and remitente.tipo in (TipoRemitente.EMPRESA, TipoRemitente.ASESORIA) \
                and pistas[Categoria.EMPRESAS]:
            pistas[Categoria.EMPRESAS].append(Pista("lo envía una empresa o asesoría", "remitente", 1))

        ordenadas = sorted(Categoria, key=lambda c: self._total(pistas[c]), reverse=True)
        primera, segunda = ordenadas[0], ordenadas[1]
        p1, p2 = self._total(pistas[primera]), self._total(pistas[segunda])

        # Sin ninguna pista no se puede proponer nada.
        if p1 == 0:
            return Propuesta(correo, None, None, 0.0,
                             ["Poca información: ni el texto ni el nombre del adjunto dan pistas"], True)

        confianza = (p1 / (p1 + p2)) * min(1.0, p1 / PUNTOS_SUFICIENTES)
        motivos: list[str] = []
        dudoso = False

        if p1 < PUNTOS_SUFICIENTES:
            dudoso = True
            motivos.append("Poca información para decidir")
        if p2 > 0 and p2 >= MARGEN_CONTRADICCION * p1:
            dudoso = True
            motivos.append(f"Señales contradictorias: también podría ser «{segunda.value}»")

        # Texto y adjunto por separado: si apuntan a categorías distintas, es dudoso.
        del_texto = self._mejor(self._puntuar({"t": (f"{asunto} {cuerpo}", 1)}))
        del_adjunto = self._mejor(self._puntuar({"a": (adjuntos, 1)}))
        if del_texto and del_adjunto and del_texto != del_adjunto:
            dudoso = True
            motivos.append(f"El texto apunta a «{del_texto.value}» y el adjunto a «{del_adjunto.value}»")

        texto_completo = f"{asunto} {cuerpo} {adjuntos}"
        destino, necesita_dt = self._destino(primera, remitente, texto_completo)
        if necesita_dt and destino is None:
            dudoso = True
            if remitente is None:
                motivos.append("Remitente no encontrado en el listado de delegaciones: no sabemos su DT")
            else:
                motivos.append("El remitente no tiene DT asignada en el listado")
        elif remitente is None:
            motivos.append("Remitente fuera del listado (no hace falta para este destino)")

        if primera is Categoria.NO_RELEVANTE:
            dudoso = True
            motivos.append("Posible no relevante: nunca se archiva sin que lo revise una persona")

        if confianza < self.umbral and not dudoso:
            dudoso = True
            motivos.append(f"Confianza baja ({confianza:.0%})")

        mejores = sorted(pistas[primera], key=lambda p: p.puntos, reverse=True)[:3]
        motivos.append("Pistas: " + ", ".join(f"«{p.frase}» ({p.campo})" for p in mejores))

        return Propuesta(correo, primera, destino, round(confianza, 2), motivos, dudoso)

    def clasificar_todos(self, correos: list[Correo]) -> list[Propuesta]:
        return [self.clasificar(c) for c in correos]
