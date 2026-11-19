"""Clases del dominio: correos, remitentes, categorías, destinos y propuestas.

Aquí no hay lógica de clasificación ni de interfaz: solo los datos con los que
trabajan el resto de módulos.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import Enum


def normalizar(texto: str) -> str:
    """Pasa a minúsculas y quita tildes, para comparar textos sin problemas."""
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return sin_tildes.lower().strip()


class Categoria(Enum):
    """Las categorías que propuso UMivale para el Reto 1."""

    BAJAS = "Bajas por enfermedad o accidente"
    ASISTENCIA = "Asistencia sanitaria"
    PRESTACIONES = "Prestaciones económicas"
    EMPRESAS = "Empresas y autónomos asociados"
    RECLAMACIONES = "Reclamaciones y quejas"
    INTERNOS = "Asuntos internos o de terceros"
    NO_RELEVANTE = "No relevante"

    @classmethod
    def desde_texto(cls, texto: str) -> Categoria | None:
        """Convierte el texto de un CSV en una categoría (None si está vacío)."""
        buscado = normalizar(texto)
        if not buscado:
            return None
        for categoria in cls:
            if buscado in (normalizar(categoria.value), normalizar(categoria.name)):
                return categoria
        raise ValueError(f"Categoría desconocida: «{texto}»")


class TipoRemitente(Enum):
    TRABAJADOR = "trabajador"
    EMPRESA = "empresa"
    ASESORIA = "asesoria"
    AUTONOMO = "autonomo"
    TERCERO = "tercero"

    @classmethod
    def desde_texto(cls, texto: str) -> TipoRemitente:
        buscado = normalizar(texto)
        for tipo in cls:
            if buscado == tipo.value:
                return tipo
        raise ValueError(f"Tipo de remitente desconocido: «{texto}»")


@dataclass(frozen=True)
class Destino:
    """Equipo al que se propone enviar el correo.

    Puede ser una delegación territorial (DT) o una dirección central.
    """

    nombre: str
    es_delegacion: bool = False

    def __str__(self) -> str:
        return self.nombre


# Direcciones centrales que nombra UMivale en sus respuestas.
DIR_PRESTACIONES = Destino("Dir. Prestaciones")
DIR_MEDICA = Destino("Dir. Médica")
DIR_ATENCION_CLIENTE = Destino("Dir. Atención al Cliente")
DIR_JURIDICA = Destino("Dir. Jurídica")
DIR_ORGANIZACION = Destino("Dir. Organización y Administración")
DIR_TECNOLOGIA = Destino("Dir. Tecnología")
ARCHIVO = Destino("Archivo (tras revisión)")


@dataclass(frozen=True)
class Remitente:
    """Una dirección de correo del listado de delegaciones."""

    correo: str
    tipo: TipoRemitente
    delegacion: Destino | None = None


@dataclass(frozen=True)
class ResultadoEsperado:
    """La respuesta correcta de un correo de prueba (para validar)."""

    categoria: Categoria | None
    destino: str
    dudoso: bool


@dataclass
class Correo:
    id: str
    fecha: str
    remitente: str
    asunto: str
    cuerpo: str
    adjuntos: list[str] = field(default_factory=list)
    esperado: ResultadoEsperado | None = None


@dataclass
class Propuesta:
    """Lo que el sistema propone hacer con un correo y por qué."""

    correo: Correo
    categoria: Categoria | None
    destino: Destino | None
    confianza: float
    motivos: list[str]
    dudoso: bool

    @property
    def estado(self) -> str:
        return "Dudoso" if self.dudoso else "Se podría repartir"

    @property
    def texto_motivo(self) -> str:
        return " · ".join(self.motivos)

    def acierta(self) -> bool | None:
        """Compara con la respuesta correcta. None si el correo no la trae."""
        esperado = self.correo.esperado
        if esperado is None:
            return None
        if esperado.dudoso:
            return self.dudoso
        if self.dudoso:
            return False
        destino = self.destino.nombre if self.destino else ""
        return self.categoria == esperado.categoria and destino == esperado.destino
