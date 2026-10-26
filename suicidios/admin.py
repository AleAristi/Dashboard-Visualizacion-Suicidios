from django.contrib import admin
from .models import Suicidio


# Registrar el modelo y personalizar su listado administrativo
@admin.register(Suicidio)
class SuicidioAdmin(admin.ModelAdmin):
    # Columnas que se mostrarán en el listado
    list_display = ("pais", "anio", "sexo", "grupo_etario", "cantidad_suicidios", "tasa_por_100k")
    # Campos que Django utilizará en el cuadro de búsqueda
    search_fields = ("pais", "pais_anio")
    # Filtros disponibles en el costado derecho
    list_filter = ("sexo", "grupo_etario", "generacion", "anio")
