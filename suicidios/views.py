
from django.shortcuts import render
from django.conf import settings
import os
import pandas as pd
import base64
from io import BytesIO
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def get_dataframe():
    # Leer el dataset master.csv que se encuentra en la raíz del proyecto
    csv_path = os.path.join(settings.BASE_DIR, 'master.csv')
    df = pd.read_csv(csv_path)
    # Limpiar columnas
    df.columns = [c.strip() for c in df.columns]
    return df

def index(request):
    return render(request, "suicidios/index.html")

def listado1(request):
    df = get_dataframe()
    # 1. Top 10 paises con mayor tasa de suicidios promedio
    s_pais = df.groupby("country")["suicides/100k pop"].mean().sort_values(ascending=False).head(10).reset_index()
    # Redondear para mejor visualizacion
    s_pais["suicides/100k pop"] = s_pais["suicides/100k pop"].round(2)
    datos = s_pais.to_dict('records')
    
    contexto = {
        "titulo": "Top 10 Países con mayor tasa de suicidios",
        "descripcion": "Esta tabla presenta los 10 países con la mayor tasa promedio de suicidios por cada 100.000 habitantes entre 1985 y 2016.",
        "columnas": ["País", "Tasa Promedio (por 100k)"],
        "filas": [[d["country"], d["suicides/100k pop"]] for d in datos]
    }
    return render(request, "suicidios/listado.html", contexto)

def listado2(request):
    df = get_dataframe()
    # 2. Tasa de suicidios por grupo etario
    s_edad = df.groupby("age")["suicides/100k pop"].mean().sort_values(ascending=False).reset_index()
    s_edad["suicides/100k pop"] = s_edad["suicides/100k pop"].round(2)
    datos = s_edad.to_dict('records')
    
    contexto = {
        "titulo": "Tasa promedio por Grupo Etario",
        "descripcion": "El listado muestra cómo varía el promedio de suicidios por cada 100.000 habitantes dependiendo del rango de edad. Se observa mayor incidencia en grupos de mayor edad.",
        "columnas": ["Grupo Etario", "Tasa Promedio (por 100k)"],
        "filas": [[d["age"], d["suicides/100k pop"]] for d in datos]
    }
    return render(request, "suicidios/listado.html", contexto)

def listado3(request):
    df = get_dataframe()
    # 3. Tasa de suicidios por género
    s_sex = df.groupby("sex")["suicides/100k pop"].mean().sort_values(ascending=False).reset_index()
    s_sex["suicides/100k pop"] = s_sex["suicides/100k pop"].round(2)
    # Traducir a español
    traduccion = {"male": "Hombres", "female": "Mujeres"}
    s_sex["sex"] = s_sex["sex"].map(traduccion)
    datos = s_sex.to_dict('records')
    
    contexto = {
        "titulo": "Tasa promedio por Sexo",
        "descripcion": "Esta tabla evidencia la marcada diferencia en la tasa de suicidios según el sexo biológico, siendo la tasa promedio masculina notoriamente más alta.",
        "columnas": ["Sexo", "Tasa Promedio (por 100k)"],
        "filas": [[d["sex"], d["suicides/100k pop"]] for d in datos]
    }
    return render(request, "suicidios/listado.html", contexto)

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
