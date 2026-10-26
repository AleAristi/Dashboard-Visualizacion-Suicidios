import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from suicidios.models import Suicidio


class Command(BaseCommand):
    help = "Carga master.csv en la tabla Suicidio (reemplaza los registros existentes)."

    def handle(self, *args, **options):
        df = pd.read_csv(settings.BASE_DIR / "master.csv", encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        registros = [
            Suicidio(
                pais=r["country"],
                anio=int(r["year"]),
                sexo=r["sex"],
                grupo_etario=r["age"].strip(),
                cantidad_suicidios=int(r["suicides_no"]),
                poblacion=int(r["population"]),
                tasa_por_100k=float(r["suicides/100k pop"]),
                pais_anio=r["country-year"],
                idh_anual=None if pd.isna(r["HDI for year"]) else float(r["HDI for year"]),
                pib_anual=int(str(r["gdp_for_year ($)"]).replace(",", "")),
                pib_per_capita=int(r["gdp_per_capita ($)"]),
                generacion=r["generation"],
            )
            for _, r in df.iterrows()
        ]
        Suicidio.objects.all().delete()
        Suicidio.objects.bulk_create(registros, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"{len(registros)} registros cargados."))
