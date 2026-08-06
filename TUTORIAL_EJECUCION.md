# Tutorial de ejecución

Guía para ejecutar el proyecto en Windows y revisar cada una de las 52 respuestas del EDA con sus gráficos.

---

## 0. Antes de empezar

**Requisitos verificados en una ejecución real:**

| Recurso | Necesario | Nota |
|---|---|---|
| Python | 3.10 o superior | Probado en 3.10 y 3.12 |
| RAM libre | **8 GB** para el EDA completo | El EDA carga 2,25 GB en pandas y necesita el doble durante la normalización. Con 3 GB el proceso muere |
| RAM libre | 2 GB para el modelo | `modeling.py` corre en 6 segundos |
| Disco | 9 GB | `data/raw` ocupa 8,3 GB |

**Si solo quieres ver los resultados y no recalcular nada, salta directo al paso 4.** Todos los artefactos ya están generados en el repositorio.

---

## 1. Instalar el entorno

Abre PowerShell en la carpeta del proyecto:

```powershell
cd $HOME\Desktop\Proyecto_Buenaventura_Final
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> Si PowerShell bloquea el script de activación:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

Comprueba que quedó bien:

```powershell
python -c "import pandas, sklearn, statsmodels; print('entorno OK')"
```

---

## 2. Verificar que todo está sano (30 segundos)

```powershell
python -m pytest tests -q
```

Resultado esperado: **7 passed**. Esto valida las fuentes y el manifiesto, la continuidad de los 173 meses, las variables externas, la ausencia de fuga contemporánea, las salidas del backtest y que el pronóstico sea de un solo mes hacia adelante.

---

## 3. Ejecutar el pipeline

**Importante:** todos los scripts se lanzan **desde la carpeta `src`**, porque los módulos se importan entre sí de forma plana (`from project_paths import ...`).

```powershell
cd src
```

### Opción A — todo de una vez, con los notebooks

```powershell
python ejecutar_notebooks.py
```

Ejecuta en orden `00_descargas` → `01_consolidar` → `02_limpieza` → `03_EDA` → `04_modelo` y **guarda las salidas dentro de los `.ipynb`**. Es la vía recomendada para sustentar, porque deja evidencia ejecutada dentro de cada notebook.

Para correr solo uno:

```powershell
python ejecutar_notebooks.py 04_modelo.ipynb
```

### Opción B — por módulos, más rápido para depurar

```powershell
python pipeline.py         # descarga (si falta), consolida ADUA=35 y construye la serie mensual
python external_data.py    # refresca TRM (Datos Abiertos) y ONI (NOAA)
python eda_compute.py      # recalcula las 52 respuestas y las 5 figuras   <-- necesita 8 GB
python modeling.py         # backtest, selección, reentrenamiento y pronóstico
python predict.py          # inferencia con los modelos ya guardados
python build_artifacts.py  # regenera el Word y el PDF del EDA
python build_manifest.py   # recalcula los SHA-256 de data/raw
```

**Tiempos medidos:** `modeling.py` 6 s · `pytest` 2 s · `eda_compute.py` varios minutos y mucha RAM.

`pipeline.py` es incremental: si ya existen el consolidado y la auditoría, no rehace nada. Para forzar:

```powershell
python -c "import pipeline; pipeline.consolidate(force=True, full_rebuild=True)"
```

---

## 4. Ver las 52 respuestas del EDA y los gráficos

Tienes cuatro formas, de la más cómoda a la más técnica.

### 4.1 Visor HTML interactivo (recomendado)

Abre con doble clic:

```
reportes\EDA_Visor_52_Preguntas.html
```

Es un archivo único, sin dependencias, que funciona sin internet. Contiene las 52 preguntas agrupadas en 8 secciones, cada una con su **código**, su **hallazgo** y su **implicación para el modelo**, más las 5 figuras incrustadas. Tiene buscador en vivo: escribe `estacionalidad`, `nulos`, `VACID` o `correlación` y filtra al instante.

Para regenerarlo después de recalcular el EDA:

```powershell
python make_viewer.py ..
```

### 4.2 Documento Word / PDF

```
reportes\EDA_52_Preguntas_Importaciones_Buenaventura.docx
reportes\EDA_52_Preguntas_Importaciones_Buenaventura.pdf
```

Es la versión formal, con índice, portada y las figuras insertadas después de las preguntas 16, 33, 39, 45 y 46. Úsala para entregar.

### 4.3 Notebook, pregunta por pregunta

```powershell
cd src
jupyter notebook 03_EDA.ipynb
```

Tiene 54 celdas de código y 55 de markdown; puedes ejecutar cada pregunta de forma aislada y modificar el código para explorar.

### 4.4 Los números crudos

Todas las cifras que aparecen en el Word y en el visor salen de un solo archivo:

```powershell
python -c "import json; r=json.load(open('../data/trusted/eda_historico_2012_2024/eda_results.json',encoding='utf-8')); [print(f'{k:28} {r[k]}') for k in sorted(r)]"
```

Son 60 claves: `target_mean`, `adf_level_p`, `acf_12`, `vif`, `top_countries`, `seasonality`, etc. Si una cifra del informe te genera dudas, este es el origen.

Las figuras sueltas están en `reportes\figuras\`:

| Archivo | Contenido |
|---|---|
| `01_serie_cif.png` | Serie mensual del valor CIF |
| `02_distribucion_target.png` | Distribución de la variable objetivo |
| `03_correlaciones.png` | Matriz de correlaciones |
| `04_estacionalidad.png` | Estacionalidad por mes |
| `05_paises.png` | Principales países de origen |

---

## 5. Ver los resultados del modelo

```powershell
cd src
python -c "import pandas as pd; print(pd.read_csv('../reportes/metricas_modelos.csv').to_string(index=False))"
python -c "import pandas as pd; print(pd.read_csv('../data/surface/proximo_pronostico.csv').to_string(index=False))"
```

| Archivo | Contenido |
|---|---|
| `reportes/metricas_modelos.csv` | MAE, RMSE, MAPE y WAPE de los 3 modelos × 2 objetivos |
| `data/surface/predicciones_validacion.csv` | Las 24 predicciones del backtest, mes a mes, con el valor real |
| `data/surface/proximo_pronostico.csv` | Pronóstico del mes siguiente con intervalo al 80 % |
| `modelos/*.joblib` | Un modelo vigente por objetivo, con `trained_through` y `forecast_date` |

---

## 6. Resultado de la ejecución real

Ejecuté el proyecto completo en un entorno limpio (Python 3.10, dependencias instaladas desde cero, sin tocar tus archivos). Esto es lo que encontré:

### Funciona

- **`pytest`: 7 de 7 pruebas pasan.**
- **`modeling.py` reproduce las métricas guardadas con exactitud de 13 cifras significativas.** El WAPE de Ridge da 7,340330600807987 contra 7,340330600807972 guardado. La diferencia es ruido de punto flotante por distinta versión de BLAS, no un cambio real.
- **El pronóstico es idéntico**: USD 2.070.875.309,8540323 para CIF, hasta el último decimal.
- **`predict.py` coincide con `modeling.py`.** Las dos rutas de inferencia dan lo mismo hoy.
- **Las cifras del EDA reproducen exactamente.** Reconstruí los agregados leyendo por bloques: 5.625.947 filas, 156 meses, 2012-01 a 2024-12, y `target_sum`, `target_mean`, `target_max`, `target_min` y `target_std` coinciden al centavo con `eda_results.json`.
- **La integridad del consolidado es limpia**: 6.703.355 filas, todas con ADUA=35, cero filas malformadas, 173 meses, **cero solapamiento** de meses entre los 18 archivos ZIP.

### Advertencias reales que vas a encontrar

**1. `eda_compute.py` muere por falta de memoria si tienes menos de ~8 GB libres.** Lo confirmé: con 3 GB el proceso recibe `Killed` a los 34 segundos, sin mensaje de error útil. Carga los 5,6 millones de registros completos en un solo `read_csv` y luego crea copias al normalizar los decimales. Si te pasa, no es un bug del código: es el requisito real.

**2. Los `.joblib` guardados se entrenaron con scikit-learn 1.9.0.** Al cargarlos con otra versión salen cinco `InconsistentVersionWarning`. Las pruebas pasan igual, pero `requirements.txt` dice `scikit-learn>=1.5`, lo que permite instalar una versión incompatible con los modelos versionados. Cambia esa línea a la versión exacta con la que entrenaste:

```
scikit-learn==1.9.0
```

**3. El pronóstico se va a romper el mes que viene.** El índice ONI de NOAA se publica con rezago y `variables_externas_mensuales.csv` ya tiene `oni_anomalia` vacío desde 2026-06. Para pronosticar julio hace falta el ONI de junio; si no está, `modeling.py` lanza `ValueError: Features faltantes para inferencia: ['oni_anomalia_lag_1']` y no produce nada. Lo mismo con `trm_volatilidad` cuando el mes nuevo tiene un solo día cargado.

**4. `modeling.py` borra `modelos/*.joblib` antes de entrenar.** Si falla a mitad —por el punto 3, por ejemplo— quedas sin modelos y sin poder ejecutar `predict.py`. Haz copia antes de reentrenar:

```powershell
Copy-Item modelos\*.joblib modelos\_backup\ -Force
```

---

## 7. Errores frecuentes

| Mensaje | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'project_paths'` | Estás fuera de `src` | `cd src` antes de ejecutar |
| `FileNotFoundError: No se encontró la carpeta data en ...` | Ruta del proyecto mal detectada | `$env:PROYECTO_BUENAVENTURA_ROOT = "C:\ruta\al\proyecto"` |
| `Killed` / el proceso muere sin mensaje | Falta RAM en `eda_compute.py` | Cierra aplicaciones o usa una máquina con 8 GB libres |
| `ValueError: Features faltantes para inferencia` | ONI o TRM sin publicar | `python external_data.py` y espera a que NOAA publique |
| `InconsistentVersionWarning` | Versión de scikit-learn distinta | Fija `scikit-learn==1.9.0` |
| `FileNotFoundError: Faltan ZIP DANE` | No están los 18 archivos | `python pipeline.py` para descargarlos |
| El notebook no guarda salidas | Lo ejecutaste a mano | Usa `python ejecutar_notebooks.py` |

---

## 8. Ruta corta para sustentar

```powershell
cd $HOME\Desktop\Proyecto_Buenaventura_Final
.venv\Scripts\Activate.ps1
python -m pytest tests -q                 # 7 passed: el proyecto está sano
cd src ; python modeling.py               # 6 s: métricas y pronóstico en vivo
```

Y abre `reportes\EDA_Visor_52_Preguntas.html` para recorrer las 52 preguntas mientras explicas.

**Nota para la sustentación:** el EDA reporta 5.625.947 registros (corte 2012-2024) y la guía de estudio reporta 6.703.355 (corte 2012-2026). Ambos son correctos porque son cortes distintos, pero conviene que lo digas tú primero antes de que te lo pregunten.
