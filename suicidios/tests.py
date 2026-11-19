from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from .models import Suicidio
from .reportes import get_dataframe, leer_filtros, ranking_paises


def contenido(respuesta):
    """FileResponse es de streaming: se lee con streaming_content."""
    return b"".join(respuesta.streaming_content)


def crear(pais, anio, sexo, edad, suicidios, tasa):
    return Suicidio(
        pais=pais, anio=anio, sexo=sexo, grupo_etario=edad,
        cantidad_suicidios=suicidios, poblacion=100000, tasa_por_100k=tasa,
        pais_anio=f"{pais}{anio}", idh_anual=None, pib_anual=1000, pib_per_capita=500,
        generacion="X",
    )


class BaseDatos(TestCase):
    @classmethod
    def setUpTestData(cls):
        Suicidio.objects.bulk_create([
            crear("Chile", 2000, "male", "15-24 years", 50, 20.0),
            crear("Chile", 2000, "female", "15-24 years", 10, 4.0),
            crear("Chile", 2005, "male", "75+ years", 30, 30.0),
            crear("Peru", 2000, "male", "15-24 years", 5, 2.0),
            crear("Peru", 2005, "female", "75+ years", 3, 1.0),
            crear("Brasil", 2005, "male", "15-24 years", 80, 8.0),
        ])


class GraficoYReporteDinamicoTests(BaseDatos):
    def test_grafico4_responde_con_imagen_y_explicacion(self):
        r = self.client.get(reverse("grafico4"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "data:image/png;base64,")
        self.assertContains(r, "¿Qué representa este gráfico?")
        self.assertContains(r, "Eje horizontal")

    def test_grafico4_sin_datos_muestra_mensaje(self):
        r = self.client.get(reverse("grafico4"), {"desde": 2005, "hasta": 2000})
        self.assertContains(r, "El año inicial no puede ser mayor")
        self.assertNotContains(r, "data:image/png")

    def test_filtro_cambia_el_resultado(self):
        df = get_dataframe()
        todos = ranking_paises(df, leer_filtros({}, df))
        mujeres = ranking_paises(df, leer_filtros({"sexo": "female"}, df))
        self.assertEqual(todos.iloc[0]["pais"], "Chile")
        self.assertEqual(list(mujeres["pais"]), ["Chile", "Peru"])

    def test_parametros_invalidos_usan_valores_por_defecto(self):
        r = self.client.get(reverse("grafico4"), {"sexo": "xx", "top": "999", "desde": "abc"})
        self.assertEqual(r.status_code, 200)

    def test_reporte4_coincide_con_el_grafico(self):
        params = {"sexo": "male", "edad": "15-24 years", "desde": 2000, "hasta": 2005, "top": 5}
        df = get_dataframe()
        esperado = ranking_paises(df, leer_filtros(params, df))
        r = self.client.get(reverse("listado4"), params)
        filas = r.context["filas"]
        self.assertEqual([f[1] for f in filas], list(esperado["pais"]))
        self.assertEqual([f[3] for f in filas], list(esperado["tasa"]))
        self.assertContains(r, "Interpretación")
        self.assertContains(r, "Origen de los datos")

    def test_reporte4_sin_datos(self):
        r = self.client.get(reverse("listado4"), {"desde": 2005, "hasta": 2000})
        self.assertContains(r, "El año inicial no puede ser mayor")


class DescargasTests(BaseDatos):
    def test_cada_reporte_tiene_los_botones_exactos(self):
        for n in (1, 2, 3, 4):
            r = self.client.get(reverse(f"listado{n}"))
            self.assertContains(r, "Descarga en PDF")
            self.assertContains(r, "Descarga en Excel")
            self.assertContains(r, reverse("listado_pdf", args=[n]))
            self.assertContains(r, reverse("listado_excel", args=[n]))

    def test_pdf_valido_en_los_cuatro_reportes(self):
        for n in (1, 2, 3, 4):
            r = self.client.get(reverse("listado_pdf", args=[n]))
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r["Content-Type"], "application/pdf")
            self.assertIn("attachment", r["Content-Disposition"])
            self.assertTrue(contenido(r).startswith(b"%PDF"))

    def test_excel_valido_en_los_cuatro_reportes(self):
        for n in (1, 2, 3, 4):
            r = self.client.get(reverse("listado_excel", args=[n]))
            self.assertEqual(r.status_code, 200)
            hoja = load_workbook(BytesIO(contenido(r)))["Datos"]
            self.assertGreaterEqual(hoja.max_row, 2)

    def test_excel_respeta_filtros_y_numeros_son_numeros(self):
        params = {"sexo": "female", "desde": 2000, "hasta": 2005, "top": 5}
        pantalla = self.client.get(reverse("listado4"), params).context["filas"]
        r = self.client.get(reverse("listado_excel", args=[4]), params)
        hoja = load_workbook(BytesIO(contenido(r)))["Datos"]
        self.assertEqual([c.value for c in hoja[1]],
                         ["N.º", "País", "Total de suicidios", "Tasa promedio (por 100k)"])
        filas = [[c.value for c in fila] for fila in hoja.iter_rows(min_row=2)]
        self.assertEqual(filas, pantalla)
        for fila in filas:
            self.assertIsInstance(fila[0], int)
            self.assertIsInstance(fila[2], int)
            self.assertIsInstance(fila[3], (int, float))  # numérico, no texto

    def test_pdf_refleja_filtros(self):
        try:
            from pypdf import PdfReader
        except ImportError:
            self.skipTest("pypdf no instalado (solo se usa para esta verificación)")
        r = self.client.get(reverse("listado_pdf", args=[4]), {"sexo": "female", "top": 5})
        texto = "".join(p.extract_text() for p in PdfReader(BytesIO(contenido(r))).pages)
        self.assertIn("Ranking de países", texto)
        self.assertIn("Mujeres", texto)
        self.assertIn("Tasa promedio (por 100k)", texto)

    def test_reporte_inexistente_da_404(self):
        self.assertEqual(self.client.get("/suicidios/listado9/pdf/").status_code, 404)

    def test_exportar_reporte4_sin_datos_no_falla(self):
        params = {"desde": 2005, "hasta": 2000}
        self.assertEqual(self.client.get(reverse("listado_pdf", args=[4]), params).status_code, 200)
        self.assertEqual(self.client.get(reverse("listado_excel", args=[4]), params).status_code, 200)


class ReportesExistentesTests(BaseDatos):
    def test_reportes_y_graficos_originales_siguen_funcionando(self):
        for nombre in ("listado1", "listado2", "listado3", "grafico1", "grafico2", "grafico3"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)

    def test_menu_incluye_las_nuevas_opciones(self):
        r = self.client.get(reverse("index"))
        self.assertContains(r, reverse("grafico4"))
        self.assertContains(r, reverse("listado4"))


class ControladorDescargasTests(BaseDatos):
    def test_js_y_aviso_incluidos_en_cada_reporte(self):
        from django.contrib.staticfiles import finders
        self.assertIsNotNone(finders.find("suicidios/descargas.js"))
        for n in (1, 2, 3, 4):
            r = self.client.get(reverse(f"listado{n}"))
            self.assertContains(r, "suicidios/descargas.js")
            self.assertContains(r, 'id="aviso-descarga"')
            self.assertContains(r, 'data-tipo="application/pdf"')

    def test_boton_conserva_filtros_en_la_url(self):
        r = self.client.get(reverse("listado4"), {"sexo": "male", "top": 5})
        self.assertContains(r, "/suicidios/listado4/pdf/?sexo=male&amp;top=5")
        self.assertContains(r, "/suicidios/listado4/excel/?sexo=male&amp;top=5")

    def test_content_type_coincide_con_el_que_valida_el_js(self):
        self.assertEqual(self.client.get(reverse("listado_pdf", args=[1]))["Content-Type"], "application/pdf")
        self.assertEqual(
            self.client.get(reverse("listado_excel", args=[1]))["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
