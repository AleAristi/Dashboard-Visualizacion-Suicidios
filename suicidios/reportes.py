"""
Lógica de datos de los reportes y del gráfico dinámico.

Todo lo que se muestra en pantalla (tabla HTML), se descarga (PDF / Excel) y
se grafica (gráfico dinámico) sale de las funciones de este módulo, de modo que
los resultados siempre coinciden entre sí para los mismos filtros.
"""
import pandas as pd

from .models import Suicidio

TASA = "suicides/100k pop"

# Columnas de la base de datos -> nombres de columna que usa el dataset original.
# Así las vistas siguen trabajando con los mismos nombres que en el Certamen 2,
# pero ahora los datos se leen desde la base de datos (SQLite), no desde el CSV.
COLUMNAS_BD = {
    "pais": "country",
    "anio": "year",
    "sexo": "sex",
    "grupo_etario": "age",
    "cantidad_suicidios": "suicides_no",
    "poblacion": "population",
    "tasa_por_100k": TASA,
    "pib_per_capita": "gdp_per_capita ($)",
}

# Opciones de los filtros del gráfico dinámico / reporte 4
SEXOS = [("todos", "Todos"), ("male", "Hombres"), ("female", "Mujeres")]
EDADES = [
    ("todos", "Todos"),
    ("5-14 years", "5-14 años"),
    ("15-24 years", "15-24 años"),
    ("25-34 years", "25-34 años"),
    ("35-54 years", "35-54 años"),
    ("55-74 years", "55-74 años"),
    ("75+ years", "75+ años"),
]
TOPS = [5, 10, 15, 20]


def get_dataframe():
    """Lee la tabla Suicidio de la base de datos y la entrega como DataFrame."""
    registros = Suicidio.objects.order_by().values_list(*COLUMNAS_BD.keys())
    return pd.DataFrame.from_records(registros, columns=list(COLUMNAS_BD.values()))


# ---------------------------------------------------------------------------
# Filtros del gráfico dinámico y del reporte 4
# ---------------------------------------------------------------------------
def _entero_valido(texto, validos, defecto):
    try:
        valor = int(texto)
    except (TypeError, ValueError):
        return defecto
    return valor if valor in validos else defecto


def leer_filtros(parametros, df):
    """Valida los parámetros GET; si alguno es inválido usa el valor por defecto."""
    if df.empty:
        anios = [0]
    else:
        anios = sorted(int(a) for a in df["year"].unique())
    sexo = parametros.get("sexo", "todos")
    if sexo not in dict(SEXOS):
        sexo = "todos"
    edad = parametros.get("edad", "todos")
    if edad not in dict(EDADES):
        edad = "todos"
    return {
        "sexo": sexo,
        "edad": edad,
        "desde": _entero_valido(parametros.get("desde"), anios, anios[0]),
        "hasta": _entero_valido(parametros.get("hasta"), anios, anios[-1]),
        "top": _entero_valido(parametros.get("top"), TOPS, 10),
    }


def opciones_filtros(df):
    anios = [] if df.empty else sorted(int(a) for a in df["year"].unique())
    return {"sexos": SEXOS, "edades": EDADES, "anios": anios, "tops": TOPS}


def filtros_como_texto(filtros):
    """Filtros vigentes en formato legible (se usa en pantalla, PDF y Excel)."""
    return [
        ("Sexo", dict(SEXOS)[filtros["sexo"]]),
        ("Grupo etario", dict(EDADES)[filtros["edad"]]),
        ("Período", f"{filtros['desde']} a {filtros['hasta']}"),
        ("Cantidad de países", str(filtros["top"])),
    ]


def ranking_paises(df, filtros):
    """
    Ranking de países por tasa promedio de suicidios según los filtros.
    Es la ÚNICA fuente de datos del gráfico dinámico y del reporte 4.
    Devuelve columnas: pais, total, tasa.
    """
    datos = df
    if filtros["sexo"] != "todos":
        datos = datos[datos["sex"] == filtros["sexo"]]
    if filtros["edad"] != "todos":
        datos = datos[datos["age"] == filtros["edad"]]
    datos = datos[(datos["year"] >= filtros["desde"]) & (datos["year"] <= filtros["hasta"])]
    if datos.empty:
        return pd.DataFrame(columns=["pais", "total", "tasa"])
    ranking = (
        datos.groupby("country")
        .agg(total=("suicides_no", "sum"), tasa=(TASA, "mean"))
        .reset_index()
        .rename(columns={"country": "pais"})
        .sort_values(["tasa", "pais"], ascending=[False, True])
        .head(filtros["top"])
        .reset_index(drop=True)
    )
    ranking["tasa"] = ranking["tasa"].round(2)
    return ranking


def mensaje_sin_datos(filtros):
    if filtros["desde"] > filtros["hasta"]:
        return "El año inicial no puede ser mayor que el año final. Corrige el período seleccionado."
    return "No hay datos para la selección actual. Prueba con otros filtros."


def _interpretacion(ranking, filtros):
    primero = ranking.iloc[0]
    texto = (
        f"Con los filtros aplicados, {primero['pais']} tiene la tasa promedio más alta "
        f"({primero['tasa']:.2f} suicidios por cada 100.000 habitantes)."
    )
    if len(ranking) > 1:
        ultimo = ranking.iloc[-1]
        proporcion = ultimo["tasa"] / primero["tasa"] * 100 if primero["tasa"] else 0
        texto += (
            f" En la posición {len(ranking)} aparece {ultimo['pais']} con {ultimo['tasa']:.2f}, "
            f"lo que equivale al {proporcion:.0f}% de la tasa del primer lugar. "
            "La columna de total de suicidios no sigue necesariamente el mismo orden, porque "
            "depende del tamaño de la población de cada país."
        )
    return texto


# ---------------------------------------------------------------------------
# Reportes. Cada función devuelve un diccionario con la misma estructura.
# ---------------------------------------------------------------------------
def reporte1(parametros):
    df = get_dataframe()
    s_pais = (
        df.groupby("country")[TASA].mean().sort_values(ascending=False).head(10).reset_index()
    )
    s_pais[TASA] = s_pais[TASA].round(2)
    return {
        "slug": "reporte_top10_paises",
        "titulo": "Top 10 Países con mayor tasa de suicidios",
        "descripcion": "Esta tabla presenta los 10 países con la mayor tasa promedio de suicidios por cada 100.000 habitantes entre 1985 y 2016.",
        "columnas": ["País", "Tasa Promedio (por 100k)"],
        "filas": [[r["country"], float(r[TASA])] for r in s_pais.to_dict("records")],
    }


def reporte2(parametros):
    df = get_dataframe()
    s_edad = df.groupby("age")[TASA].mean().sort_values(ascending=False).reset_index()
    s_edad[TASA] = s_edad[TASA].round(2)
    return {
        "slug": "reporte_grupo_etario",
        "titulo": "Tasa promedio por Grupo Etario",
        "descripcion": "El listado muestra cómo varía el promedio de suicidios por cada 100.000 habitantes dependiendo del rango de edad. Se observa mayor incidencia en grupos de mayor edad.",
        "columnas": ["Grupo Etario", "Tasa Promedio (por 100k)"],
        "filas": [[r["age"], float(r[TASA])] for r in s_edad.to_dict("records")],
    }


def reporte3(parametros):
    df = get_dataframe()
    s_sex = df.groupby("sex")[TASA].mean().sort_values(ascending=False).reset_index()
    s_sex[TASA] = s_sex[TASA].round(2)
    s_sex["sex"] = s_sex["sex"].map({"male": "Hombres", "female": "Mujeres"})
    return {
        "slug": "reporte_sexo",
        "titulo": "Tasa promedio por Sexo",
        "descripcion": "Esta tabla evidencia la marcada diferencia en la tasa de suicidios según el sexo biológico, siendo la tasa promedio masculina notoriamente más alta.",
        "columnas": ["Sexo", "Tasa Promedio (por 100k)"],
        "filas": [[r["sex"], float(r[TASA])] for r in s_sex.to_dict("records")],
    }


def reporte4(parametros):
    """Nuevo reporte: los mismos datos del gráfico dinámico, en formato tabla."""
    df = get_dataframe()
    filtros = leer_filtros(parametros, df)
    ranking = ranking_paises(df, filtros)
    reporte = {
        "slug": "reporte_ranking_paises",
        "titulo": "Ranking de países por tasa de suicidios (con filtros)",
        "descripcion": (
            "Esta tabla contiene los mismos datos que se representan en el gráfico dinámico "
            "«Ranking de países»: los países con mayor tasa promedio de suicidios, según el sexo, "
            "el grupo etario, el período y la cantidad de países elegidos."
        ),
        "origen": (
            "Los datos provienen de la tabla Suicidio de la base de datos del proyecto, cargada desde "
            "el dataset master.csv (Suicide Rates Overview 1985 to 2016). Variables utilizadas: país, "
            "año, sexo, grupo etario, cantidad de suicidios y tasa de suicidios por 100.000 habitantes. "
            "Cálculos: primero se filtran los registros por sexo, grupo etario y rango de años; luego se "
            "agrupan por país, se suma la cantidad de suicidios (Total de suicidios) y se promedia la tasa "
            "por 100k (Tasa promedio); finalmente se ordenan de mayor a menor tasa y se muestran los N primeros."
        ),
        "columnas": ["N.º", "País", "Total de suicidios", "Tasa promedio (por 100k)"],
        "filas": [
            [i + 1, r["pais"], int(r["total"]), float(r["tasa"])]
            for i, r in ranking.iterrows()
        ],
        "filtros": filtros_como_texto(filtros),
        "filtros_valores": filtros,
        "opciones": opciones_filtros(df),
    }
    if ranking.empty:
        reporte["mensaje_vacio"] = mensaje_sin_datos(filtros)
    else:
        reporte["interpretacion"] = _interpretacion(ranking, filtros)
    return reporte


REPORTES = {1: reporte1, 2: reporte2, 3: reporte3, 4: reporte4}
