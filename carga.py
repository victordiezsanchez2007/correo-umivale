"""Lectura de los correos de ejemplo y del listado de delegaciones.

Acepta CSV y JSON con las mismas columnas, que es el formato que anunció UMivale
para la muestra de datos (además de .eml, que dejamos para más adelante).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from modelo import (
    Categoria,
    Correo,
    Destino,
    Remitente,
    ResultadoEsperado,
    TipoRemitente,
    normalizar,
)

COLUMNAS_CORREOS = ["id", "fecha", "remitente", "asunto", "cuerpo", "adjuntos"]
COLUMNAS_ESPERADAS = ["categoria_esperada", "destino_esperado", "dudoso_esperado"]
COLUMNAS_DELEGACIONES = ["correo", "tipo", "delegacion"]


class ErrorDeCarga(Exception):
    """Error con un mensaje que se puede enseñar tal cual al usuario."""


def _leer_filas(ruta: str | Path) -> list[dict[str, str]]:
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorDeCarga(f"No se encuentra el archivo {ruta}")
    try:
        if ruta.suffix.lower() == ".json":
            with ruta.open(encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, list):
                raise ErrorDeCarga("El JSON debe ser una lista de objetos")
            return [{k: "" if v is None else str(v) for k, v in fila.items()} for fila in datos]
        with ruta.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error) as e:
        raise ErrorDeCarga(f"No se ha podido leer {ruta.name}: {e}") from e


def _comprobar_columnas(filas: list[dict[str, str]], obligatorias: list[str], nombre: str) -> None:
    if not filas:
        raise ErrorDeCarga(f"El archivo de {nombre} está vacío")
    faltan = [c for c in obligatorias if c not in filas[0]]
    if faltan:
        raise ErrorDeCarga(f"Al archivo de {nombre} le faltan las columnas: {', '.join(faltan)}")


def cargar_delegaciones(ruta: str | Path) -> dict[str, Remitente]:
    """Devuelve un diccionario correo -> Remitente."""
    filas = _leer_filas(ruta)
    _comprobar_columnas(filas, COLUMNAS_DELEGACIONES, "delegaciones")
    remitentes: dict[str, Remitente] = {}
    for n, fila in enumerate(filas, start=2):
        correo = normalizar(fila["correo"])
        if not correo:
            continue
        try:
            tipo = TipoRemitente.desde_texto(fila["tipo"])
        except ValueError as e:
            raise ErrorDeCarga(f"Delegaciones, línea {n}: {e}") from e
        nombre_dt = (fila.get("delegacion") or "").strip()
        delegacion = Destino(nombre_dt, es_delegacion=True) if nombre_dt else None
        remitentes[correo] = Remitente(correo, tipo, delegacion)
    return remitentes


def _a_booleano(texto: str) -> bool:
    return normalizar(texto) in ("si", "sí", "true", "1", "x")


def cargar_correos(ruta: str | Path) -> list[Correo]:
    """Lee los correos. Si traen la respuesta correcta, la guarda en `esperado`."""
    filas = _leer_filas(ruta)
    _comprobar_columnas(filas, COLUMNAS_CORREOS, "correos")
    con_respuesta = all(c in filas[0] for c in COLUMNAS_ESPERADAS)
    correos = []
    for n, fila in enumerate(filas, start=2):
        adjuntos = [a.strip() for a in (fila.get("adjuntos") or "").split(";") if a.strip()]
        esperado = None
        if con_respuesta:
            try:
                esperado = ResultadoEsperado(
                    categoria=Categoria.desde_texto(fila["categoria_esperada"]),
                    destino=(fila["destino_esperado"] or "").strip(),
                    dudoso=_a_booleano(fila["dudoso_esperado"]),
                )
            except ValueError as e:
                raise ErrorDeCarga(f"Correos, línea {n}: {e}") from e
        correos.append(
            Correo(
                id=(fila["id"] or str(n - 1)).strip(),
                fecha=(fila["fecha"] or "").strip(),
                remitente=normalizar(fila["remitente"]),
                asunto=(fila["asunto"] or "").strip(),
                cuerpo=(fila["cuerpo"] or "").strip(),
                adjuntos=adjuntos,
                esperado=esperado,
            )
        )
    return correos
