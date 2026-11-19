
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    # Reportes (listados de datos)
    path("listado1/", views.listado1, name="listado1"),
    path("listado2/", views.listado2, name="listado2"),
    path("listado3/", views.listado3, name="listado3"),
    path("listado4/", views.listado4, name="listado4"),
    # Descargas de cada reporte (respetan los filtros enviados en la URL)
    path("listado<int:numero>/pdf/", views.listado_pdf, name="listado_pdf"),
    path("listado<int:numero>/excel/", views.listado_excel, name="listado_excel"),
    # Gráficos
    path("grafico1/", views.grafico1, name="grafico1"),
    path("grafico2/", views.grafico2, name="grafico2"),
    path("grafico3/", views.grafico3, name="grafico3"),
    path("grafico4/", views.grafico4, name="grafico4"),
]
