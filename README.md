# Web Scraping con Python para Datos Laborales de Fuentes Estatales

Extracción automatizada de datos de empleo formal del **Ministerio de Trabajo y Promoción del Empleo (MTPE)** del Perú, a través de su tablero interactivo Power BI publicado en el Observatorio de la Formalización Laboral.

---

## Descripción del Proyecto

El MTPE publica estadísticas de empleo formal (Planilla Electrónica) en un tablero Power BI embebido en su sitio web. Este proyecto automatiza la extracción de esos datos mediante web scraping con **Playwright**, navegando el reporte, seleccionando filtros (departamentos y años) y extrayendo la tabla de resultados para guardarla como archivo `CSV` y `XLSX`.

**Fuente de datos:**
> https://www2.trabajo.gob.pe/estadisticas/observatorio-de-la-formalizacion-laboral/

---

## Estructura del Proyecto

```
Web-Scraping-Datos-Laborales/
│
├── scraper_mtpe.py          # Script principal de scraping
├── scraper_mtpe_backup.py   # Versión de respaldo del scraper
│
├── analyze_all.py           # Análisis general de capturas JSON de la API Power BI
├── analyze_captures.py      # Análisis del modelo de datos de la API Power BI
├── analyze_deep.py          # Análisis profundo de capturas específicas (timestamps y fechas)
│
├── check_debug.py           # Verificación de capturas de debug
├── debug_years.py           # Debug de selección de años en el slicer
├── parse_test.py            # Pruebas de parseo de datos extraídos
│
├── empleo_formal_mtpe(3).csv  # Ejemplo de datos exportados
├── requirements.txt           # Dependencias del proyecto
└── README.md
```

---

## Requisitos Previos

- Python 3.10 o superior
- Google Chromium (instalado automáticamente por Playwright)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU-USUARIO/Web-Scraping-Datos-Laborales.git
cd Web-Scraping-Datos-Laborales
```

### 2. Crear y activar el entorno virtual

```bash
# Crear el entorno virtual
python -m venv venv

# Activar en Windows
.\venv\Scripts\activate

# Activar en Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar el navegador de Playwright

```bash
playwright install chromium
```

---

## Uso

### Ejecutar el scraper principal

```bash
python scraper_mtpe.py
```

El script realizará los siguientes pasos de forma automática:

1. **Carga la página del MTPE** y detecta el iframe con el reporte Power BI.
2. **Navega a la pestaña "EVOLUCIÓN"** del tablero interactivo.
3. **Selecciona el departamento** configurado (por defecto: `Loreto`).
4. **Selecciona todos los años disponibles** (2016–2025) en el slicer de timeline.
5. **Abre la vista de tabla** mediante clic derecho → "Mostrar como tabla".
6. **Extrae todas las filas** con scroll automático sobre la tabla de Power BI.
7. **Guarda los resultados** en archivos `CSV` y `XLSX` con numeración incremental.

---

## Configuración

Dentro de `scraper_mtpe.py` puedes modificar los siguientes parámetros:

```python
# Departamentos a procesar (puedes agregar más)
DEPARTAMENTOS = ["Loreto"]

# Años a seleccionar en el slicer
ANIOS = ["2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]

# Directorio donde se guardarán los archivos CSV/XLSX
BASE_DIR = r"D:\tu\ruta\destino"

# Nombre base del archivo de salida
BASE_NAME = "empleo_formal_mtpe"
```

---

## Formato de Salida

Los datos se exportan con las siguientes columnas:

| Columna               | Descripción                              |
|-----------------------|------------------------------------------|
| `anio`                | Año del registro                         |
| `mes`                 | Número del mes (1–12)                    |
| `mes_nombre`          | Nombre abreviado del mes (Ene, Feb, ...) |
| `region`              | Departamento / Región                    |
| `actividad_economica` | Categoría económica (por defecto: Total) |
| `empleo`              | Número de trabajadores formales          |

**Ejemplo:**

| anio | mes | mes_nombre | region | actividad_economica | empleo    |
|------|-----|------------|--------|----------------------|-----------|
| 2016 | 1   | Ene        | Loreto | Total                | 36641     |
| 2016 | 2   | Feb        | Loreto | Total                | 37200     |

Los archivos se numeran automáticamente para no sobreescribir resultados anteriores:
```
empleo_formal_mtpe.csv
empleo_formal_mtpe(1).csv
empleo_formal_mtpe(2).csv
...
```

---

## Scripts de Análisis y Debug

Estos scripts auxiliares fueron usados durante el desarrollo para entender la estructura interna de la API de Power BI:

| Script                | Propósito                                                              |
|-----------------------|------------------------------------------------------------------------|
| `analyze_all.py`      | Escanea archivos JSON capturados buscando datos de empleo por mes/año  |
| `analyze_captures.py` | Inspecciona el modelo de datos de Power BI (tablas, columnas, medidas) |
| `analyze_deep.py`     | Decodifica timestamps Unix y fechas de capturas específicas            |
| `debug_years.py`      | Diagnostica la selección de años en el slicer de Power BI              |
| `parse_test.py`       | Prueba el parseo de valores numéricos con formato de miles             |
| `check_debug.py`      | Revisa las capturas de pantalla y logs de debug generados              |

---

## Dependencias Principales

| Librería                  | Uso                                              |
|---------------------------|--------------------------------------------------|
| `playwright`              | Automatización del navegador (scraping dinámico) |
| `pandas`                  | Procesamiento y exportación de datos             |
| `openpyxl`                | Exportación a formato Excel (.xlsx)              |
| `requests`                | Peticiones HTTP auxiliares                       |

---

## Notas Técnicas

- El reporte Power BI usa **iframes sandbox**, por lo que se requiere iterar sobre `page.frames` para localizar los elementos del slicer.
- La tabla de datos usa un **scrollbar custom de Power BI** (clase `.scroll-bar-part-bar`), que se arrastra programáticamente para cargar todas las filas.
- Los valores numéricos usan **punto como separador de miles** (ej: `3.770.677`), lo cual se convierte correctamente a entero.
- El navegador se ejecuta en modo **headful** (`headless=False`) para evitar bloqueos del reporte embebido.

---

## Licencia

Este proyecto es de uso educativo y de investigación. Los datos extraídos son de carácter público y están disponibles en el Portal del MTPE.
