from django.db import models


# Modelo persistente: cada fila corresponde a un registro del dataset master.csv
# (un país, un año, un sexo y un grupo etario).
class Suicidio(models.Model):
    pais = models.CharField("País", max_length=100)
    anio = models.PositiveSmallIntegerField("Año")
    sexo = models.CharField(max_length=10)
    grupo_etario = models.CharField("Grupo etario", max_length=20)
    cantidad_suicidios = models.PositiveIntegerField("Cantidad de suicidios")
    poblacion = models.PositiveIntegerField("Población")
    tasa_por_100k = models.FloatField("Suicidios por 100k hab.")
    pais_anio = models.CharField("País-año", max_length=140)
    # null=True/blank=True: el IDH no está disponible para todos los años
    idh_anual = models.FloatField("IDH del año", null=True, blank=True)
    pib_anual = models.BigIntegerField("PIB anual (USD)")
    pib_per_capita = models.PositiveIntegerField("PIB per cápita (USD)")
    generacion = models.CharField("Generación", max_length=30)

    class Meta:
        verbose_name = "suicidio"
        verbose_name_plural = "suicidios"
        ordering = ["pais", "anio", "sexo", "grupo_etario"]
        # Impide registrar dos veces la misma combinación
        constraints = [
            models.UniqueConstraint(
                fields=["pais", "anio", "sexo", "grupo_etario"],
                name="suicidio_unico_pais_anio_sexo_edad",
            )
        ]

    # Texto utilizado para representar al objeto en Django Admin
    def __str__(self):
        return f"{self.pais} {self.anio} - {self.sexo} - {self.grupo_etario}"
