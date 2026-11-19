# Dashboard de Visualización de Suicidios (Django)

Proyecto semestral en Django que analiza las tasas de suicidio a nivel mundial (1985–2016) a partir del
dataset *Suicide Rates Overview* (`master.csv`), almacenado en una base de datos SQLite.


## Integrantes

- Alejandro Aristizabal
- Jose Cervellino
- Sergio Paredes
- Vicente Perez
- Nicolas Vega

## Video
Demostracion: https://drive.google.com/file/d/178eOnSgW4yTLrCaJ-ZWIe5Z2BiLMtYC_/view

## Funcionalidades

| Sección | Ruta | Descripción |
|---------|------|-------------|
| Gráfico de barras | `/suicidios/grafico1/` | Tasa promedio por grupo etario |
| Gráfico de líneas | `/suicidios/grafico2/` | Evolución anual de la tasa mundial |
| Gráfico de dispersión | `/suicidios/grafico3/` | PIB per cápita vs. tasa por país |
| **Gráfico dinámico (nuevo)** | `/suicidios/grafico4/` | Ranking de países; filtros: sexo, grupo etario, año desde/hasta y cantidad de países |
| Reporte 1 | `/suicidios/listado1/` | Top 10 países con mayor tasa |
| Reporte 2 | `/suicidios/listado2/` | Tasa por grupo etario |
| Reporte 3 | `/suicidios/listado3/` | Tasa por sexo |
| **Reporte 4 (nuevo)** | `/suicidios/listado4/` | Datos del gráfico dinámico en tabla, con origen de los datos, filtros, cálculos e interpretación |

Cada uno de los 4 reportes termina con los botones **Descarga en PDF** y **Descarga en Excel**
(`/suicidios/listadoN/pdf/` y `/suicidios/listadoN/excel/`). Un controlador JavaScript compartido
(`descargas.js`) solicita el archivo, muestra "Preparando…" y abre una ventana de aviso al iniciar la descarga.
Ambas descargas respetan los filtros vigentes, porque los filtros viajan en la URL del botón.

## Estructura del código relevante

```
suicidios/
├── reportes.py        # Lectura desde la BD, filtros y datos de los 4 reportes (fuente única de datos)
├── views.py           # Vistas de gráficos, reportes y descargas (listado_pdf con ReportLab,
│                      #   listado_excel con openpyxl, ambas entregadas con FileResponse)
├── urls.py            # Rutas
├── static/suicidios/
│   └── descargas.js              # Controlador compartido de los botones de descarga
└── templates/suicidios/
    ├── base.html, menu.html          # Estructura y navegación
    ├── listado.html                  # Plantilla común de reportes (tabla + botones de descarga)
    ├── aviso_descarga.html           # Botones PDF/Excel, estado y ventana de aviso
    ├── grafico.html                  # Gráficos 1 a 3
    ├── grafico_dinamico.html         # Gráfico 4 con filtros
    └── _filtros.html                 # Formulario de filtros compartido por gráfico 4 y reporte 4
```

El gráfico dinámico y el reporte 4 usan la misma función (`ranking_paises`), por lo que sus resultados
siempre coinciden para los mismos filtros. Las vistas leen desde la **base de datos SQLite**
(tabla `Suicidio`), no desde el CSV.

## Instalación y ejecución local

Requiere Python 3.10 o superior.

```bash
git clone https://github.com/AleAristi/Dashboard-Visualizacion-Suicidios.git
cd Dashboard-Visualizacion-Suicidios
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Abrir http://127.0.0.1:8000/suicidios/

`db.sqlite3` ya incluye los 27.820 registros. Si la tabla estuviera vacía o se quisiera recargar desde
`master.csv`: `python manage.py cargar_datos`.

Pruebas automáticas: `python manage.py test suicidios`

### Dependencias (`requirements.txt`)

Django, pandas, matplotlib (gráficos), **reportlab** (PDF), **openpyxl** (Excel),
**whitenoise** (archivos estáticos con `DEBUG=False`) y **gunicorn** (servidor para producción).

## Variables de entorno

Valores por defecto pensados para desarrollo local; en el servidor se configuran por variables de entorno.

| Variable | Por defecto | Uso en AWS |
|----------|-------------|------------|
| `DJANGO_DEBUG` | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | _(vacío)_ | IP pública y/o DNS de la instancia, separados por coma |
| `DJANGO_SECRET_KEY` | clave de desarrollo | una clave propia larga y secreta |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | _(vacío)_ | `http://<IP>:8000` (solo si se usa el login de `/admin/`) |
| `DJANGO_DB_PATH` | `db.sqlite3` en la raíz | opcional: otra ruta del archivo SQLite |

## Despliegue en AWS (EC2 + SQLite)

**Cómo se entiende la "base de datos en AWS":** SQLite no es un servidor de base de datos sino un archivo
(`db.sqlite3`). Por eso no se usa RDS: la base vive en el disco de la instancia EC2, junto al código, y Django
la lee desde allí. Cualquier persona que entre al sitio desde un navegador externo consulta la base
alojada en AWS.

### 1. Crear la instancia EC2

1. En la consola de AWS ir a **EC2 → Launch instance**.
2. AMI: **Ubuntu Server 24.04 LTS**. Tipo: **t2.micro / t3.micro** (elegible para capa gratuita).
3. Crear un **par de claves** (`.pem`) y descargarlo.
4. En **Network settings → Security group**, permitir tráfico de entrada:
   - **SSH (22)** desde *My IP*.
   - **Custom TCP (8000)** desde `0.0.0.0/0`, para que el sitio sea visible desde cualquier navegador.
5. Lanzar la instancia y anotar su **IP pública** (y el DNS público).

> La IP pública cambia si la instancia se detiene y se vuelve a iniciar. Para que sea fija, asociar una
> **Elastic IP** (EC2 → Elastic IPs → Allocate → Associate).

### 2. Conectarse e instalar

```bash
chmod 400 clave.pem
ssh -i clave.pem ubuntu@<IP-PUBLICA>

sudo apt update
sudo apt install -y python3-venv python3-pip git
```

### 3. Obtener el proyecto

```bash
git clone https://github.com/AleAristi/Dashboard-Visualizacion-Suicidios.git
cd Dashboard-Visualizacion-Suicidios
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Base de datos

El archivo `db.sqlite3` viene en el repositorio con los datos cargados. Verificar:

```bash
python manage.py migrate
python manage.py shell -c "from suicidios.models import Suicidio; print(Suicidio.objects.count())"
# debe imprimir 27820. Si imprime 0:  python manage.py cargar_datos
```

### 5. Configuración de Django

Crear el archivo `.env` en la raíz del proyecto (no se sube a GitHub):

```
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<IP-PUBLICA>,<DNS-PUBLICO>
DJANGO_SECRET_KEY=<una-clave-larga-y-aleatoria>
DJANGO_CSRF_TRUSTED_ORIGINS=http://<IP-PUBLICA>:8000
```

Generar una clave: `python -c "import secrets; print(secrets.token_urlsafe(50))"`

Recopilar los archivos estáticos (necesario con `DEBUG=False`):

```bash
python manage.py collectstatic --noinput
```

### 6. Prueba rápida

```bash
set -a; source .env; set +a
gunicorn proyecto.wsgi:application --bind 0.0.0.0:8000
```

Desde un navegador **fuera de AWS** (por ejemplo, el computador o el celular) abrir
`http://<IP-PUBLICA>:8000/suicidios/`. Detener con `Ctrl+C`.

### 7. Dejarlo ejecutándose siempre (systemd)

```bash
sudo nano /etc/systemd/system/suicidios.service
```

```ini
[Unit]
Description=Dashboard Suicidios (gunicorn)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Dashboard-Visualizacion-Suicidios
EnvironmentFile=/home/ubuntu/Dashboard-Visualizacion-Suicidios/.env
ExecStart=/home/ubuntu/Dashboard-Visualizacion-Suicidios/venv/bin/gunicorn proyecto.wsgi:application --bind 0.0.0.0:8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now suicidios
sudo systemctl status suicidios
```

### 8. Comprobar las funcionalidades desde un navegador externo

Abrir `http://<IP-PUBLICA>:8000/suicidios/` y verificar:

- Gráfico dinámico (`/grafico4/`): cambiar filtros y presionar **Actualizar**.
- Reporte 4 (`/listado4/`): mismos datos que el gráfico.
- Botones **Descarga en PDF** y **Descarga en Excel** en los 4 reportes; abrir los archivos descargados.

### Actualizar el sitio después de cambios

```bash
cd ~/Dashboard-Visualizacion-Suicidios && git pull
source venv/bin/activate && pip install -r requirements.txt
python manage.py collectstatic --noinput
sudo systemctl restart suicidios
```


