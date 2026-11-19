"""Punto de entrada.

    python main.py              -> abre la ventana con los datos de ejemplo
    python main.py --consola    -> muestra el resultado en la terminal
    python main.py --correos otro.csv --delegaciones otro.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from carga import ErrorDeCarga, cargar_correos, cargar_delegaciones
from clasificador import ClasificadorPorReglas
from evaluacion import resumir

CARPETA_DATOS = Path(__file__).resolve().parent / "datos"


def ejecutar_en_consola(ruta_correos: Path, ruta_delegaciones: Path) -> int:
    try:
        remitentes = cargar_delegaciones(ruta_delegaciones)
        correos = cargar_correos(ruta_correos)
    except ErrorDeCarga as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    propuestas = ClasificadorPorReglas(remitentes).clasificar_todos(correos)
    for p in propuestas:
        categoria = p.categoria.value if p.categoria else "—"
        destino = p.destino.nombre if p.destino else "—"
        coincide = {True: "coincide", False: "NO coincide", None: ""}[p.acierta()]
        print(f"[{p.correo.id:>2}] {p.correo.asunto[:45]:<45} -> {categoria} / {destino} "
              f"({p.estado}, {p.confianza:.0%}) {coincide}")
        for m in p.motivos:
            print(f"       · {m}")
    print()
    print(resumir(propuestas).texto())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Clasificador de correos de UMivale (Sprint 1)")
    parser.add_argument("--correos", type=Path, default=CARPETA_DATOS / "correos_prueba.csv")
    parser.add_argument("--delegaciones", type=Path, default=CARPETA_DATOS / "delegaciones.csv")
    parser.add_argument("--consola", action="store_true", help="mostrar el resultado sin abrir la ventana")
    args = parser.parse_args()

    if args.consola:
        return ejecutar_en_consola(args.correos, args.delegaciones)

    from interfaz import VentanaPrincipal  # solo se importa Tkinter si hace falta

    VentanaPrincipal(args.correos, args.delegaciones).mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
