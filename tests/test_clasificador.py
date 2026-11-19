"""Pruebas de los criterios de aceptación de R1 y R2a.

Se ejecutan con:  python -m pytest   (o  python -m unittest  si no tenéis pytest)
"""
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from carga import ErrorDeCarga, cargar_correos, cargar_delegaciones  # noqa: E402
from clasificador import ClasificadorPorReglas  # noqa: E402
from evaluacion import resumir  # noqa: E402
from modelo import Categoria, Correo, Destino, Remitente, TipoRemitente  # noqa: E402

Z08 = Destino("Z08 - Valencia Centro & Sur", es_delegacion=True)
REMITENTES = {
    "ana@ejemplo.es": Remitente("ana@ejemplo.es", TipoRemitente.TRABAJADOR, Z08),
    "rrhh@empresa.es": Remitente("rrhh@empresa.es", TipoRemitente.EMPRESA, Z08),
}


def correo(asunto="", cuerpo="", adjuntos=(), remitente="ana@ejemplo.es"):
    return Correo("1", "", remitente, asunto, cuerpo, list(adjuntos))


class TestR1ProponerCategoriaYDestino(unittest.TestCase):
    def setUp(self):
        self.clasificador = ClasificadorPorReglas(REMITENTES)

    def test_parte_de_baja_va_a_la_dt_del_remitente(self):
        p = self.clasificador.clasificar(correo("Parte de baja", "Adjunto el parte de baja", ["parte_baja.pdf"]))
        self.assertEqual(p.categoria, Categoria.BAJAS)
        self.assertEqual(p.destino, Z08)
        self.assertFalse(p.dudoso)

    def test_pago_directo_de_la_baja_es_prestacion_y_no_baja(self):
        p = self.clasificador.clasificar(correo("Pago directo de la baja", "Solicito el pago directo"))
        self.assertEqual(p.categoria, Categoria.PRESTACIONES)
        self.assertEqual(p.destino.nombre, "Dir. Prestaciones")

    def test_ingreso_hospitalario_va_a_direccion_medica(self):
        p = self.clasificador.clasificar(correo("Ingreso hospitalario", "Me han ingresado en el hospital"))
        self.assertEqual(p.categoria, Categoria.ASISTENCIA)
        self.assertEqual(p.destino.nombre, "Dir. Médica")

    def test_cita_normal_va_a_la_dt(self):
        p = self.clasificador.clasificar(correo("Cambiar cita de rehabilitación", "¿Me dais otra cita?"))
        self.assertEqual(p.categoria, Categoria.ASISTENCIA)
        self.assertEqual(p.destino, Z08)

    def test_requerimiento_judicial_va_a_juridica_aunque_el_remitente_no_este(self):
        p = self.clasificador.clasificar(
            correo("Requerimiento judicial", "Procedimiento 1/2026", ["oficio_juzgado.pdf"], "juzgado@x.es"))
        self.assertEqual(p.destino.nombre, "Dir. Jurídica")
        self.assertFalse(p.dudoso)

    def test_las_tildes_no_importan(self):
        con = self.clasificador.clasificar(correo("Reclamación", "Es inaceptable"))
        sin = self.clasificador.clasificar(correo("reclamacion", "es inaceptable"))
        self.assertEqual(con.categoria, sin.categoria)

    def test_siempre_hay_un_motivo(self):
        p = self.clasificador.clasificar(correo("Parte de baja", "Adjunto el parte de baja"))
        self.assertTrue(p.motivos)


class TestR2aDetectarDudosos(unittest.TestCase):
    def setUp(self):
        self.clasificador = ClasificadorPorReglas(REMITENTES)

    def test_remitente_desconocido_que_necesita_dt_es_dudoso(self):
        p = self.clasificador.clasificar(correo("Parte de baja", "Adjunto el parte de baja", remitente="otro@x.es"))
        self.assertTrue(p.dudoso)
        self.assertIsNone(p.destino)
        self.assertIn("Remitente no encontrado", p.texto_motivo)

    def test_correo_sin_texto_es_dudoso(self):
        p = self.clasificador.clasificar(correo("Adjunto documentación", "", ["IMG_0001.jpg"]))
        self.assertTrue(p.dudoso)
        self.assertIsNone(p.categoria)
        self.assertIn("Poca información", p.texto_motivo)

    def test_no_relevante_nunca_se_reparte_solo(self):
        p = self.clasificador.clasificar(correo("30 % de descuento", "Puedes darte de baja aquí"))
        self.assertEqual(p.categoria, Categoria.NO_RELEVANTE)
        self.assertTrue(p.dudoso)

    def test_texto_y_adjunto_que_no_coinciden_es_dudoso(self):
        p = self.clasificador.clasificar(correo("Pago de mi baja", "No he cobrado", ["parte_alta.pdf"]))
        self.assertTrue(p.dudoso)
        self.assertIn("el adjunto", p.texto_motivo)

    def test_umbral_configurable(self):
        # Confianza de este correo: 80 % (asistencia, con una pista pequeña de prestaciones).
        c = correo("Cita de rehabilitación", "pago")
        self.assertFalse(ClasificadorPorReglas(REMITENTES, umbral=0.5).clasificar(c).dudoso)
        self.assertTrue(ClasificadorPorReglas(REMITENTES, umbral=0.9).clasificar(c).dudoso)


class TestCargaYValidacion(unittest.TestCase):
    def test_carga_los_datos_de_ejemplo(self):
        remitentes = cargar_delegaciones(RAIZ / "datos" / "delegaciones.csv")
        correos = cargar_correos(RAIZ / "datos" / "correos_prueba.csv")
        self.assertGreaterEqual(len(correos), 10)
        self.assertIn("trabajador1@correo-ejemplo.es", remitentes)
        self.assertTrue(all(c.esperado is not None for c in correos))

    def test_falta_una_columna_da_un_error_claro(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "malo.csv"
            ruta.write_text("id,asunto\n1,Hola\n", encoding="utf-8")
            with self.assertRaises(ErrorDeCarga) as ctx:
                cargar_correos(ruta)
            self.assertIn("faltan las columnas", str(ctx.exception))

    def test_archivo_inexistente_da_un_error_claro(self):
        with self.assertRaises(ErrorDeCarga):
            cargar_correos(RAIZ / "datos" / "no_existe.csv")

    def test_resumen_de_validacion(self):
        remitentes = cargar_delegaciones(RAIZ / "datos" / "delegaciones.csv")
        correos = cargar_correos(RAIZ / "datos" / "correos_prueba.csv")
        resumen = resumir(ClasificadorPorReglas(remitentes).clasificar_todos(correos))
        self.assertEqual(resumen.total, len(correos))
        self.assertEqual(resumen.con_respuesta, len(correos))
        self.assertGreater(resumen.dudosos, 0)


if __name__ == "__main__":
    unittest.main()
