"""Ventana de escritorio (Tkinter) para ver las propuestas del clasificador.

La interfaz solo muestra: toda la lógica está en clasificador.py, para poder
reutilizarla en P2 aunque cambie la forma de presentarla.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from carga import ErrorDeCarga, cargar_correos, cargar_delegaciones
from clasificador import ClasificadorPorReglas
from evaluacion import resumir
from modelo import Propuesta

COLUMNAS = [
    ("id", "Id", 40),
    ("remitente", "Remitente", 190),
    ("asunto", "Asunto", 230),
    ("categoria", "Categoría propuesta", 190),
    ("destino", "Destino", 180),
    ("confianza", "Confianza", 75),
    ("estado", "Estado", 120),
    ("acierta", "¿Coincide?", 80),
]


class VentanaPrincipal(tk.Tk):
    def __init__(self, ruta_correos: Path | None = None, ruta_delegaciones: Path | None = None):
        super().__init__()
        self.title("UMivale · Clasificación de correos · Sprint 1")
        self.geometry("1200x680")
        self.minsize(900, 500)

        self.ruta_correos = ruta_correos
        self.ruta_delegaciones = ruta_delegaciones
        self.propuestas: list[Propuesta] = []

        self._crear_barra_superior()
        self._crear_tabla()
        self._crear_detalle()
        self._crear_barra_estado()

        if ruta_correos and ruta_delegaciones:
            self.clasificar()

    # ---------- construcción de la ventana ----------

    def _crear_barra_superior(self) -> None:
        barra = ttk.Frame(self, padding=8)
        barra.pack(fill="x")
        ttk.Button(barra, text="Cargar correos…", command=self._elegir_correos).pack(side="left")
        ttk.Button(barra, text="Cargar delegaciones…", command=self._elegir_delegaciones).pack(side="left", padx=6)
        ttk.Button(barra, text="Clasificar", command=self.clasificar).pack(side="left")
        self.etiqueta_archivos = ttk.Label(barra, text="")
        self.etiqueta_archivos.pack(side="left", padx=12)
        self._actualizar_etiqueta_archivos()

    def _crear_tabla(self) -> None:
        marco = ttk.Frame(self, padding=(8, 0))
        marco.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(marco, columns=[c[0] for c in COLUMNAS], show="headings", height=14)
        for clave, titulo, ancho in COLUMNAS:
            self.tabla.heading(clave, text=titulo)
            self.tabla.column(clave, width=ancho, anchor="w")
        self.tabla.tag_configure("dudoso", background="#FFF4CC")
        self.tabla.tag_configure("no_coincide", foreground="#B00020")
        barra_v = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra_v.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra_v.pack(side="right", fill="y")
        self.tabla.bind("<<TreeviewSelect>>", self._mostrar_detalle)

    def _crear_detalle(self) -> None:
        marco = ttk.LabelFrame(self, text="Detalle del correo seleccionado", padding=8)
        marco.pack(fill="both", padx=8, pady=8)
        self.detalle = tk.Text(marco, height=9, wrap="word", state="disabled")
        self.detalle.pack(fill="both", expand=True)

    def _crear_barra_estado(self) -> None:
        self.estado = ttk.Label(self, text="Carga los correos y el listado de delegaciones.", padding=(8, 0, 8, 8))
        self.estado.pack(fill="x")

    # ---------- acciones ----------

    def _elegir_correos(self) -> None:
        ruta = filedialog.askopenfilename(title="Correos de ejemplo",
                                          filetypes=[("CSV o JSON", "*.csv *.json"), ("Todos", "*.*")])
        if ruta:
            self.ruta_correos = Path(ruta)
            self._actualizar_etiqueta_archivos()

    def _elegir_delegaciones(self) -> None:
        ruta = filedialog.askopenfilename(title="Listado de delegaciones",
                                          filetypes=[("CSV o JSON", "*.csv *.json"), ("Todos", "*.*")])
        if ruta:
            self.ruta_delegaciones = Path(ruta)
            self._actualizar_etiqueta_archivos()

    def _actualizar_etiqueta_archivos(self) -> None:
        correos = self.ruta_correos.name if self.ruta_correos else "—"
        delegaciones = self.ruta_delegaciones.name if self.ruta_delegaciones else "—"
        self.etiqueta_archivos.config(text=f"Correos: {correos}   ·   Delegaciones: {delegaciones}")

    def clasificar(self) -> None:
        if not (self.ruta_correos and self.ruta_delegaciones):
            messagebox.showwarning("Faltan archivos", "Carga primero los correos y el listado de delegaciones.")
            return
        try:
            remitentes = cargar_delegaciones(self.ruta_delegaciones)
            correos = cargar_correos(self.ruta_correos)
        except ErrorDeCarga as e:
            messagebox.showerror("No se han podido cargar los datos", str(e))
            return
        self.propuestas = ClasificadorPorReglas(remitentes).clasificar_todos(correos)
        self._rellenar_tabla()
        self.estado.config(text=resumir(self.propuestas).texto())

    def _rellenar_tabla(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        for indice, p in enumerate(self.propuestas):
            acierta = p.acierta()
            etiquetas = []
            if p.dudoso:
                etiquetas.append("dudoso")
            if acierta is False:
                etiquetas.append("no_coincide")
            self.tabla.insert("", "end", iid=str(indice), tags=etiquetas, values=(
                p.correo.id,
                p.correo.remitente,
                p.correo.asunto,
                p.categoria.value if p.categoria else "—",
                p.destino.nombre if p.destino else "—",
                f"{p.confianza:.0%}",
                p.estado,
                {True: "Sí", False: "No", None: "—"}[acierta],
            ))
        self._escribir_detalle("")

    def _mostrar_detalle(self, _evento=None) -> None:
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        p = self.propuestas[int(seleccion[0])]
        c = p.correo
        lineas = [
            f"De: {c.remitente}    Fecha: {c.fecha}",
            f"Asunto: {c.asunto}",
            f"Adjuntos: {', '.join(c.adjuntos) or 'ninguno'}",
            "",
            c.cuerpo or "(sin texto)",
            "",
            f"Propuesta: {p.categoria.value if p.categoria else '—'} → {p.destino or '—'} ({p.estado})",
            "Por qué:",
            *[f"  • {m}" for m in p.motivos],
        ]
        if c.esperado:
            e = c.esperado
            lineas.append(f"Respuesta correcta: {e.categoria.value if e.categoria else '—'} → "
                          f"{e.destino or '—'}{' (dudoso)' if e.dudoso else ''}")
        self._escribir_detalle("\n".join(lineas))

    def _escribir_detalle(self, texto: str) -> None:
        self.detalle.config(state="normal")
        self.detalle.delete("1.0", "end")
        self.detalle.insert("1.0", texto)
        self.detalle.config(state="disabled")
