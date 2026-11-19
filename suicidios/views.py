
import base64
from io import BytesIO
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from xml.sax.saxutils import escape

from django.http import FileResponse, Http404
from django.shortcuts import render
from django.urls import reverse

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from .reportes import REPORTES, TASA, get_dataframe, leer_filtros, mensaje_sin_datos, opciones_filtros, ranking_paises, filtros_como_texto

def index(request):
    return render(request, "suicidios/index.html")

def _contexto_reporte(request, numero):
    """Arma el contexto del reporte N, con las URLs de descarga (conservando los filtros)."""
    if numero not in REPORTES:
        raise Http404("Reporte no encontrado")
    reporte = REPORTES[numero](request.GET)
    consulta = request.GET.urlencode()
    sufijo = f"?{consulta}" if consulta else ""
    reporte["numero"] = numero
    reporte["url_pdf"] = reverse("listado_pdf", args=[numero]) + sufijo
    reporte["url_excel"] = reverse("listado_excel", args=[numero]) + sufijo
    return reporte


def listado1(request):
    return render(request, "suicidios/listado.html", _contexto_reporte(request, 1))


def listado2(request):
    return render(request, "suicidios/listado.html", _contexto_reporte(request, 2))


def listado3(request):
    return render(request, "suicidios/listado.html", _contexto_reporte(request, 3))


def listado4(request):
    return render(request, "suicidios/listado.html", _contexto_reporte(request, 4))


def _texto(valor):
    """Texto de una celda para el PDF: 2 decimales en floats y separador de miles en enteros."""
    if isinstance(valor, float):
        return f"{valor:.2f}"
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    return str(valor)


def listado_pdf(request, numero):
    """Descarga en PDF del reporte N (respeta los filtros recibidos en la URL)."""
    reporte = _contexto_reporte(request, numero)
    columnas = reporte["columnas"]
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=24, leftMargin=24,
        topMargin=24, bottomMargin=24, title=reporte["titulo"],
    )
    estilos = getSampleStyleSheet()
    celda = ParagraphStyle("Celda", fontName="Helvetica", fontSize=9,
                           leading=12, wordWrap="CJK")
    encabezado = ParagraphStyle("Encabezado", parent=celda, fontName="Helvetica-Bold")

    # Tabla: encabezados + una fila por registro
    filas = [[Paragraph(escape(texto), encabezado) for texto in columnas]]
    for fila in reporte["filas"]:
        filas.append([Paragraph(escape(_texto(valor)), celda) for valor in fila])
    if not reporte["filas"]:
        mensaje = reporte.get("mensaje_vacio", "No hay registros disponibles.")
        filas.append([Paragraph(escape(mensaje), celda)] + [""] * (len(columnas) - 1))

    # Ancho de cada columna proporcional a su contenido (la hoja A4 tiene 547 pt útiles)
    largos = [
        max([len(col) // 2, 6] + [len(_texto(f[i])) for f in reporte["filas"]])
        for i, col in enumerate(columnas)
    ]
    anchos = [547 * largo / sum(largos) for largo in largos]
    tabla = LongTable(filas, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    formato = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE6F1")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if not reporte["filas"]:
        formato.append(("SPAN", (0, 1), (-1, 1)))
    tabla.setStyle(TableStyle(formato))

    # Mismo contenido explicativo que se ve en pantalla
    normal = estilos["Normal"]
    seccion = estilos["Heading3"]
    elementos = [Paragraph(escape(reporte["titulo"]), estilos["Title"])]
    if reporte.get("filtros"):
        elementos.append(Paragraph("Filtros aplicados", seccion))
        for nombre, valor in reporte["filtros"]:
            elementos.append(Paragraph(f"<b>{escape(nombre)}:</b> {escape(str(valor))}", normal))
    elementos.append(Paragraph("Descripción", seccion))
    elementos.append(Paragraph(escape(reporte["descripcion"]), normal))
    if reporte.get("origen"):
        elementos.append(Paragraph("Origen de los datos y cálculos", seccion))
        elementos.append(Paragraph(escape(reporte["origen"]), normal))
    elementos += [Spacer(1, 12), tabla]
    if reporte.get("interpretacion"):
        elementos.append(Paragraph("Interpretación", seccion))
        elementos.append(Paragraph(escape(reporte["interpretacion"]), normal))

    documento.build(elementos)
    buffer.seek(0)
    return FileResponse(
        buffer, as_attachment=True, filename=f"{reporte['slug']}.pdf",
        content_type="application/pdf",
    )


def listado_excel(request, numero):
    """Descarga en Excel (.xlsx) del reporte N (respeta los filtros recibidos en la URL)."""
    reporte = _contexto_reporte(request, numero)
    columnas = reporte["columnas"]

    libro = Workbook()  # Crear el archivo Excel en memoria.
    hoja = libro.active
    hoja.title = "Datos"
    hoja.append(columnas)
    for fila in reporte["filas"]:
        hoja.append(fila)
    for fila in hoja.iter_rows(min_row=2):
        for celda in fila:
            if isinstance(celda.value, str):
                celda.data_type = "s"  # Conservar los textos como datos, no fórmulas.
            elif isinstance(celda.value, float):
                celda.number_format = "0.00"
            elif isinstance(celda.value, int):
                celda.number_format = "#,##0"

    borde = Side(style="thin", color="D9D9D9")
    for fila in hoja:
        for celda in fila:
            celda.border = Border(left=borde, right=borde, top=borde, bottom=borde)
            celda.alignment = Alignment(vertical="top", wrap_text=True)
    for celda in hoja[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F4E78")

    for numero_col, nombre in enumerate(columnas, start=1):
        mayor = max([len(nombre)] + [len(_texto(f[numero_col - 1])) for f in reporte["filas"]])
        hoja.column_dimensions[get_column_letter(numero_col)].width = min(max(mayor + 4, 12), 45)
    hoja.freeze_panes = "A2"  # Mantener visible el encabezado al desplazarse.
    hoja.auto_filter.ref = hoja.dimensions

    # Segunda hoja: la explicación que se muestra en pantalla
    info = libro.create_sheet("Explicación")
    info.column_dimensions["A"].width = 28
    info.column_dimensions["B"].width = 110
    info.append(["Reporte", reporte["titulo"]])
    for nombre, valor in reporte.get("filtros", []):
        info.append([f"Filtro - {nombre}", str(valor)])
    info.append(["Descripción", reporte["descripcion"]])
    if reporte.get("origen"):
        info.append(["Origen de los datos", reporte["origen"]])
    if reporte.get("interpretacion"):
        info.append(["Interpretación", reporte["interpretacion"]])
    if not reporte["filas"] and reporte.get("mensaje_vacio"):
        info.append(["Aviso", reporte["mensaje_vacio"]])
    for fila in info.iter_rows():
        fila[0].font = Font(bold=True)
        for celda in fila:
            celda.alignment = Alignment(vertical="top", wrap_text=True)
            if isinstance(celda.value, str):
                celda.data_type = "s"

    buffer = BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return FileResponse(
        buffer, as_attachment=True, filename=f"{reporte['slug']}.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def grafico1(request):
    df = get_dataframe()
    # Gráfico de barras: Suicidios por rango etario
    s_edad = df.groupby("age")["suicides/100k pop"].mean().sort_values(ascending=False)
    
    figura, eje = plt.subplots(figsize=(8, 4.5))
    barras = eje.bar(s_edad.index, s_edad.values, color="#A23B72")
    eje.set_title("Tasa promedio de suicidios por grupo etario")
    eje.set_xlabel("Grupo etario")
    eje.set_ylabel("Suicidios por cada 100k hab.")
    plt.xticks(rotation=15)
    eje.grid(axis="y", alpha=0.3)
    eje.bar_label(barras, fmt="%.1f", padding=3)
    figura.tight_layout()

    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()

    contexto = {
        "grafico": grafico,
        "titulo": "Gráfico de Barras: Suicidios por Rango Etario",
        "descripcion": "El gráfico de barras ilustra cómo la tasa de suicidios aumenta junto con la edad, siendo el grupo de 75+ años el de mayor riesgo."
    }
    return render(request, "suicidios/grafico.html", contexto)

def grafico2(request):
    df = get_dataframe()
    # Gráfico de líneas: Evolución temporal
    evolucion = df.groupby("year")["suicides/100k pop"].mean()
    
    figura, eje = plt.subplots(figsize=(8, 4.5))
    eje.plot(evolucion.index, evolucion.values, marker="o", color="#2E86AB", linewidth=2)
    eje.set_title("Evolución de la tasa promedio de suicidios (1985-2016)")
    eje.set_xlabel("Año")
    eje.set_ylabel("Suicidios por cada 100k hab.")
    eje.grid(True, alpha=0.3)
    figura.tight_layout()
    
    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()
    
    contexto = {
        "grafico": grafico,
        "titulo": "Gráfico de Líneas: Evolución Histórica Mundial",
        "descripcion": "Este gráfico de líneas exhibe el alza en las tasas mundiales durante la década de los 90 y su posterior descenso progresivo hacia 2016."
    }
    return render(request, "suicidios/grafico.html", contexto)

def grafico3(request):
    df = get_dataframe()
    # Gráfico de dispersión: PIB vs Tasa de suicidios
    promedio_pais = df.groupby("country")[["gdp_per_capita ($)", "suicides/100k pop"]].mean()
    
    figura, eje = plt.subplots(figsize=(8, 4.5))
    eje.scatter(promedio_pais["gdp_per_capita ($)"], promedio_pais["suicides/100k pop"], color="#F18F01", alpha=0.7, s=50)
    eje.set_title("PIB per cápita vs. Tasa de suicidios")
    eje.set_xlabel("PIB per cápita promedio (USD)")
    eje.set_ylabel("Suicidios por cada 100k hab.")
    eje.grid(True, alpha=0.3)
    figura.tight_layout()

    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()
    
    contexto = {
        "grafico": grafico,
        "titulo": "Gráfico de Dispersión: PIB vs Suicidios",
        "descripcion": "El diagrama de dispersión compara el nivel de ingresos de cada país con su tasa de suicidios. No se percibe una correlación lineal fuerte y clara."
    }
    return render(request, "suicidios/grafico.html", contexto)


def grafico4(request):
    """Gráfico dinámico: ranking de países según sexo, grupo etario, período y cantidad de países."""
    df = get_dataframe()
    filtros = leer_filtros(request.GET, df)
    ranking = ranking_paises(df, filtros)  # misma función que usa el reporte 4

    consulta = request.GET.urlencode()
    contexto = {
        "titulo": "Gráfico Dinámico: Ranking de países por tasa de suicidios",
        "descripcion": (
            "Muestra los países con mayor tasa promedio de suicidios por cada 100.000 habitantes. "
            "Usa los filtros para cambiar el sexo, el grupo etario, el período y la cantidad de países; "
            "el gráfico se actualiza al presionar «Actualizar»."
        ),
        "variables": [
            ("Eje horizontal (X)", "Tasa promedio de suicidios por cada 100.000 habitantes."),
            ("Eje vertical (Y)", "País, ordenado de mayor a menor tasa."),
        ],
        "filtros": filtros,
        "filtros_texto": filtros_como_texto(filtros),
        "opciones": opciones_filtros(df),
        "url_reporte": reverse("listado4") + (f"?{consulta}" if consulta else ""),
    }

    if ranking.empty:
        contexto["mensaje_vacio"] = mensaje_sin_datos(filtros)
        return render(request, "suicidios/grafico_dinamico.html", contexto)

    figura, eje = plt.subplots(figsize=(8, max(3, 0.45 * len(ranking) + 1.5)))
    barras = eje.barh(ranking["pais"], ranking["tasa"], color="#2A9D8F")
    eje.invert_yaxis()  # el país con mayor tasa queda arriba
    eje.set_title(f"Top {len(ranking)} países por tasa promedio de suicidios ({filtros['desde']}-{filtros['hasta']})")
    eje.set_xlabel("Suicidios por cada 100k hab. (promedio)")
    eje.set_ylabel("País")
    eje.grid(axis="x", alpha=0.3)
    eje.bar_label(barras, fmt="%.1f", padding=3)
    eje.margins(x=0.1)
    figura.tight_layout()

    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    contexto["grafico"] = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()
    return render(request, "suicidios/grafico_dinamico.html", contexto)
