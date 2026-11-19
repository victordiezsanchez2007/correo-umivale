"""Ventana de escritorio (Tkinter) para ver las propuestas del clasificador.

La interfaz solo muestra: toda la lógica está en clasificador.py, para poder
reutilizarla en P2 aunque cambie la forma de presentarla.

Diseño: cabecera, tarjetas con el resumen, buscador y filtro, la tabla a la
izquierda y el detalle del correo seleccionado a la derecha.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from carga import ErrorDeCarga, cargar_correos, cargar_delegaciones
from clasificador import ClasificadorPorReglas
from evaluacion import resumir
from modelo import Propuesta, normalizar

# ---------- colores y tipografía ----------
FONDO = "#F4F6FA"
TARJETA = "#FFFFFF"
TEXTO = "#1F2937"
SECUNDARIO = "#6B7280"
BORDE = "#E5E7EB"
CABECERA = "#1E293B"
ACENTO = "#E30613"         # rojo UMivale
ACENTO_OSCURO = "#B8050F"
DUDOSO = "#FFF7E0"
DUDOSO_TEXTO = "#92400E"
OK_TEXTO = "#166534"
ERROR_TEXTO = "#B91C1C"
SELECCION = "#DBEAFE"
FUENTE = "Segoe UI"

COLUMNAS = [
    ("id", "#", 44, False),
    ("remitente", "Remitente", 210, True),
    ("asunto", "Asunto", 260, True),
    ("categoria", "Categoría", 200, True),
    ("destino", "Destino", 190, True),
    ("confianza", "Confianza", 84, False),
    ("estado", "Estado", 130, False),
]

FILTROS = ["Todos los correos", "Solo dudosos", "Solo para repartir", "No coinciden con la respuesta"]


def filtrar(propuestas: list[Propuesta], texto: str, filtro: str) -> list[int]:
    """Índices de las propuestas que cumplen la búsqueda y el filtro elegidos."""
    buscado = normalizar(texto)
    indices = []
    for i, p in enumerate(propuestas):
        if filtro == "Solo dudosos" and not p.dudoso:
            continue
        if filtro == "Solo para repartir" and p.dudoso:
            continue
        if filtro == "No coinciden con la respuesta" and p.acierta() is not False:
            continue
        if buscado:
            campos = [p.correo.remitente, p.correo.asunto, p.correo.cuerpo,
                      p.categoria.value if p.categoria else "", p.destino.nombre if p.destino else ""]
            if not any(buscado in normalizar(c) for c in campos):
                continue
        indices.append(i)
    return indices


class VentanaPrincipal(tk.Tk):
    def __init__(self, ruta_correos: Path | None = None, ruta_delegaciones: Path | None = None):
        super().__init__()
        self.title("UMivale · Clasificación de correos")
        self.geometry("1320x760")
        self.minsize(1000, 600)
        self.configure(background=FONDO)

        self.ruta_correos = ruta_correos
        self.ruta_delegaciones = ruta_delegaciones
        self.propuestas: list[Propuesta] = []

        self._crear_estilos()
        self._crear_cabecera()
        self._crear_tarjetas()
        self._crear_barra_filtros()
        self._crear_cuerpo()
        self._crear_barra_estado()

        if ruta_correos and ruta_delegaciones:
            self.clasificar()

    # ---------- estilos ----------

    def _crear_estilos(self) -> None:
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure(".", font=(FUENTE, 10), background=FONDO, foreground=TEXTO)
        estilo.configure("TFrame", background=FONDO)
        estilo.configure("Cabecera.TFrame", background=CABECERA)
        estilo.configure("Titulo.TLabel", background=CABECERA, foreground="white", font=(FUENTE, 17, "bold"))
        estilo.configure("Subtitulo.TLabel", background=CABECERA, foreground="#CBD5E1", font=(FUENTE, 10))
        estilo.configure("Tarjeta.TFrame", background=TARJETA)
        estilo.configure("TarjetaTitulo.TLabel", background=TARJETA, foreground=SECUNDARIO, font=(FUENTE, 9))
        estilo.configure("TarjetaNumero.TLabel", background=TARJETA, foreground=TEXTO, font=(FUENTE, 22, "bold"))
        estilo.configure("TarjetaDetalle.TLabel", background=TARJETA, foreground=SECUNDARIO, font=(FUENTE, 9))
        estilo.configure("Secundario.TLabel", background=FONDO, foreground=SECUNDARIO, font=(FUENTE, 9))

        estilo.configure("Acento.TButton", background=ACENTO, foreground="white", borderwidth=0,
                         focusthickness=0, padding=(14, 7), font=(FUENTE, 10, "bold"))
        estilo.map("Acento.TButton", background=[("active", ACENTO_OSCURO), ("pressed", ACENTO_OSCURO)])
        estilo.configure("Claro.TButton", background="#334155", foreground="white", borderwidth=0,
                         focusthickness=0, padding=(12, 7))
        estilo.map("Claro.TButton", background=[("active", "#475569"), ("pressed", "#475569")])

        estilo.configure("TEntry", fieldbackground=TARJETA, bordercolor=BORDE, lightcolor=BORDE,
                         darkcolor=BORDE, padding=6)
        estilo.configure("TCombobox", fieldbackground=TARJETA, background=TARJETA, bordercolor=BORDE,
                         lightcolor=BORDE, darkcolor=BORDE, padding=5, arrowsize=14)
        estilo.map("TCombobox", fieldbackground=[("readonly", TARJETA)])

        estilo.configure("Treeview", background=TARJETA, fieldbackground=TARJETA, foreground=TEXTO,
                         rowheight=32, borderwidth=0, font=(FUENTE, 10))
        estilo.configure("Treeview.Heading", background="#EEF1F6", foreground=SECUNDARIO,
                         font=(FUENTE, 9, "bold"), relief="flat", padding=(8, 8), borderwidth=0)
        estilo.map("Treeview.Heading", background=[("active", "#E2E8F0")])
        estilo.map("Treeview", background=[("selected", SELECCION)], foreground=[("selected", TEXTO)])

    # ---------- construcción de la ventana ----------

    def _crear_cabecera(self) -> None:
        cabecera = ttk.Frame(self, style="Cabecera.TFrame", padding=(24, 16))
        cabecera.pack(fill="x")
        textos = ttk.Frame(cabecera, style="Cabecera.TFrame")
        textos.pack(side="left")
        ttk.Label(textos, text="Clasificación de correos", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(textos, text="UMivale · Reto 1 · Sprint 1 · Equipo 3", style="Subtitulo.TLabel").pack(anchor="w")

        botones = ttk.Frame(cabecera, style="Cabecera.TFrame")
        botones.pack(side="right")
        ttk.Button(botones, text="Cargar correos", style="Claro.TButton",
                   command=self._elegir_correos).pack(side="left", padx=4)
        ttk.Button(botones, text="Cargar delegaciones", style="Claro.TButton",
                   command=self._elegir_delegaciones).pack(side="left", padx=4)
        ttk.Button(botones, text="Clasificar", style="Acento.TButton",
                   command=self.clasificar).pack(side="left", padx=(4, 0))

    def _crear_tarjetas(self) -> None:
        fila = ttk.Frame(self, padding=(24, 18, 24, 6))
        fila.pack(fill="x")
        self.tarjetas: dict[str, tuple[ttk.Label, ttk.Label]] = {}
        datos = [("total", "Correos cargados"), ("dudosos", "Dudosos"),
                 ("repartir", "Se podrían repartir"), ("coinciden", "Coinciden con la respuesta")]
        for columna, (clave, titulo) in enumerate(datos):
            fila.columnconfigure(columna, weight=1, uniform="tarjetas")
            tarjeta = ttk.Frame(fila, style="Tarjeta.TFrame", padding=(16, 12))
            tarjeta.grid(row=0, column=columna, sticky="nsew", padx=(0 if columna == 0 else 12, 0))
            ttk.Label(tarjeta, text=titulo.upper(), style="TarjetaTitulo.TLabel").pack(anchor="w")
            numero = ttk.Label(tarjeta, text="—", style="TarjetaNumero.TLabel")
            numero.pack(anchor="w", pady=(2, 0))
            detalle = ttk.Label(tarjeta, text="", style="TarjetaDetalle.TLabel")
            detalle.pack(anchor="w")
            self.tarjetas[clave] = (numero, detalle)

    def _crear_barra_filtros(self) -> None:
        barra = ttk.Frame(self, padding=(24, 10))
        barra.pack(fill="x")
        ttk.Label(barra, text="Buscar", style="Secundario.TLabel").pack(side="left", padx=(0, 6))
        self.busqueda = tk.StringVar()
        self.busqueda.trace_add("write", lambda *_: self._rellenar_tabla())
        ttk.Entry(barra, textvariable=self.busqueda, width=36).pack(side="left")
        ttk.Label(barra, text="Mostrar", style="Secundario.TLabel").pack(side="left", padx=(18, 6))
        self.filtro = tk.StringVar(value=FILTROS[0])
        combo = ttk.Combobox(barra, textvariable=self.filtro, values=FILTROS, state="readonly", width=28)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda _e: self._rellenar_tabla())
        self.etiqueta_archivos = ttk.Label(barra, text="", style="Secundario.TLabel")
        self.etiqueta_archivos.pack(side="right")
        self._actualizar_etiqueta_archivos()

    def _crear_cuerpo(self) -> None:
        paneles = ttk.PanedWindow(self, orient="horizontal")
        paneles.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        # Tabla
        marco_tabla = ttk.Frame(paneles, style="Tarjeta.TFrame", padding=1)
        self.tabla = ttk.Treeview(marco_tabla, columns=[c[0] for c in COLUMNAS], show="headings",
                                  selectmode="browse")
        for clave, titulo, ancho, estirar in COLUMNAS:
            self.tabla.heading(clave, text=titulo, anchor="w")
            self.tabla.column(clave, width=ancho, minwidth=40, stretch=estirar, anchor="w")
        self.tabla.tag_configure("par", background=TARJETA)
        self.tabla.tag_configure("impar", background="#F9FAFB")
        self.tabla.tag_configure("dudoso", background=DUDOSO, foreground=DUDOSO_TEXTO)
        self.tabla.tag_configure("no_coincide", foreground=ERROR_TEXTO)
        barra_v = ttk.Scrollbar(marco_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra_v.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra_v.pack(side="right", fill="y")
        self.tabla.bind("<<TreeviewSelect>>", self._mostrar_detalle)
        paneles.add(marco_tabla, weight=3)

        # Detalle
        marco_detalle = ttk.Frame(paneles, style="Tarjeta.TFrame", padding=(18, 14))
        ttk.Label(marco_detalle, text="DETALLE DEL CORREO", style="TarjetaTitulo.TLabel").pack(anchor="w")
        self.detalle = tk.Text(marco_detalle, wrap="word", relief="flat", borderwidth=0, highlightthickness=0,
                               background=TARJETA, foreground=TEXTO, font=(FUENTE, 10), padx=0, pady=8,
                               cursor="arrow", state="disabled")
        self.detalle.pack(fill="both", expand=True)
        self.detalle.tag_configure("asunto", font=(FUENTE, 13, "bold"), spacing3=4)
        self.detalle.tag_configure("dato", foreground=SECUNDARIO, font=(FUENTE, 9))
        self.detalle.tag_configure("seccion", font=(FUENTE, 9, "bold"), foreground=SECUNDARIO, spacing1=12)
        self.detalle.tag_configure("cuerpo", lmargin1=0, spacing1=6, spacing3=6)
        self.detalle.tag_configure("propuesta", font=(FUENTE, 11, "bold"))
        self.detalle.tag_configure("dudoso", foreground=DUDOSO_TEXTO, font=(FUENTE, 10, "bold"))
        self.detalle.tag_configure("repartir", foreground=OK_TEXTO, font=(FUENTE, 10, "bold"))
        self.detalle.tag_configure("motivo", lmargin1=8, lmargin2=20, spacing1=2)
        paneles.add(marco_detalle, weight=2)
        self._escribir_detalle([("Selecciona un correo de la tabla para ver por qué se propone lo que se propone.",
                                 "dato")])

    def _crear_barra_estado(self) -> None:
        self.estado = ttk.Label(self, text="Carga los correos y el listado de delegaciones.",
                                style="Secundario.TLabel", padding=(24, 0, 24, 12))
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
        self._actualizar_tarjetas()
        self._rellenar_tabla()
        self.estado.config(text=resumir(self.propuestas).texto())

    def _actualizar_tarjetas(self) -> None:
        r = resumir(self.propuestas)
        self.tarjetas["total"][0].config(text=str(r.total))
        self.tarjetas["total"][1].config(text="en el archivo de prueba")
        self.tarjetas["dudosos"][0].config(text=str(r.dudosos))
        self.tarjetas["dudosos"][1].config(text=f"{r.porcentaje_dudosos:.0%} del total · referencia 10–15 %")
        self.tarjetas["repartir"][0].config(text=str(r.total - r.dudosos))
        self.tarjetas["repartir"][1].config(text="con confianza suficiente")
        if r.con_respuesta:
            self.tarjetas["coinciden"][0].config(text=f"{r.aciertos}/{r.con_respuesta}")
            self.tarjetas["coinciden"][1].config(text="validación con los datos de prueba")
        else:
            self.tarjetas["coinciden"][0].config(text="—")
            self.tarjetas["coinciden"][1].config(text="los correos no traen respuesta")

    def _rellenar_tabla(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        visibles = filtrar(self.propuestas, self.busqueda.get(), self.filtro.get())
        for fila, indice in enumerate(visibles):
            p = self.propuestas[indice]
            etiquetas = ["par" if fila % 2 == 0 else "impar"]
            if p.dudoso:
                etiquetas.append("dudoso")
            if p.acierta() is False:
                etiquetas.append("no_coincide")
            self.tabla.insert("", "end", iid=str(indice), tags=etiquetas, values=(
                p.correo.id,
                p.correo.remitente,
                p.correo.asunto or "(sin asunto)",
                p.categoria.value if p.categoria else "—",
                p.destino.nombre if p.destino else "—",
                f"{p.confianza:.0%}",
                "●  Dudoso" if p.dudoso else "●  Para repartir",
            ))
        if self.propuestas:
            self.estado.config(text=f"Mostrando {len(visibles)} de {len(self.propuestas)} correos")

    def _mostrar_detalle(self, _evento=None) -> None:
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        p = self.propuestas[int(seleccion[0])]
        c = p.correo
        partes: list[tuple[str, str]] = [
            (f"{c.asunto or '(sin asunto)'}\n", "asunto"),
            (f"De {c.remitente}  ·  {c.fecha}\n", "dato"),
            (f"Adjuntos: {', '.join(c.adjuntos) or 'ninguno'}\n", "dato"),
            ("MENSAJE\n", "seccion"),
            (f"{c.cuerpo or '(sin texto)'}\n", "cuerpo"),
            ("PROPUESTA\n", "seccion"),
            (f"{p.categoria.value if p.categoria else 'Sin categoría'}  →  {p.destino or 'sin destino'}\n",
             "propuesta"),
            (f"{'Dudoso' if p.dudoso else 'Se podría repartir'}  ·  confianza {p.confianza:.0%}\n",
             "dudoso" if p.dudoso else "repartir"),
            ("POR QUÉ\n", "seccion"),
            *[(f"•  {m}\n", "motivo") for m in p.motivos],
        ]
        if c.esperado:
            e = c.esperado
            coincide = {True: "coincide", False: "no coincide", None: ""}[p.acierta()]
            partes += [
                ("RESPUESTA CORRECTA (DATOS DE PRUEBA)\n", "seccion"),
                (f"{e.categoria.value if e.categoria else '—'}  →  {e.destino or '—'}"
                 f"{'  (dudoso)' if e.dudoso else ''}  ·  {coincide}\n", "dato"),
            ]
        self._escribir_detalle(partes)

    def _escribir_detalle(self, partes: list[tuple[str, str]]) -> None:
        self.detalle.config(state="normal")
        self.detalle.delete("1.0", "end")
        for texto, etiqueta in partes:
            self.detalle.insert("end", texto, etiqueta)
        self.detalle.config(state="disabled")
