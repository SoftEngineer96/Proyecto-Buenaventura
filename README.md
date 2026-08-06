# Proyecto de importaciones registradas por la Aduana de Buenaventura

## Alcance

El proyecto analiza las importaciones registradas por la aduana 35 de Buenaventura y construye pronósticos mensuales separados para valor CIF en dólares y peso neto en kilogramos.

La base de modelado cubre enero de 2012 a mayo de 2026. El EDA de 52 preguntas conserva el corte histórico 2012-2024 para mantener trazabilidad con el informe Word validado.

## Estructura

- `src`: notebooks y módulos del pipeline.
- `data/raw`: 18 paquetes DANE, archivos DIAN y manifiesto con SHA-256.
- `data/landing`: registros de Buenaventura consolidados y comprimidos.
- `data/trusted`: series validadas, agregados y tabla de características.
- `data/external`: TRM oficial y ONI de NOAA.
- `data/surface`: predicciones y archivos pequeños para consumo.
- `reportes`: EDA, figuras, métricas y validación visual.
- `modelos`: un modelo vigente por objetivo.
- `tests`: pruebas automatizadas de datos, fuga e inferencia.

## Orden de ejecución

1. `00_descargas.ipynb`: comprueba o descarga fuentes.
2. `01_consolidar.ipynb`: filtra ADUA=35 y construye las capas landing/trusted.
3. `02_limpieza.ipynb`: actualiza TRM/ONI y crea variables rezagadas.
4. `03_EDA.ipynb`: reproduce el EDA histórico de 52 preguntas.
5. `04_modelo.ipynb`: ejecuta backtest expansivo, reentrena y pronostica.

Para ejecutar todo desde `src`:

```powershell
python ejecutar_notebooks.py
```

Para validar:

```powershell
python -m pytest ../tests -q
```

## Google Colab

Suba la carpeta a `MyDrive/Proyecto_Buenaventura_Final`. Los notebooks montan Drive y usan esa ubicación. Los datos pesados no deben subirse a Git o Bitbucket; deben mantenerse en Drive o almacenamiento local.

## Modelado

- Validación: ventana expansiva de un paso sobre los últimos 24 meses.
- Comparadores: Naive estacional, Ridge y HistGradientBoosting.
- Métrica principal: WAPE; también se calculan MAE, RMSE y MAPE.
- Variables: rezagos, medias móviles, calendario, tendencia, TRM y ONI, siempre desplazados al pasado.
- Inferencia: un mes adelante, con intervalo aproximado del 80 %.
- Reentrenamiento: el ganador se ajusta nuevamente con todos los meses disponibles.

Los resultados quedan en `reportes/metricas_modelos.csv`, `data/surface/proximo_pronostico.csv` y `modelos`.

## Instalación manual

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

No se despliega automáticamente una API o aplicación web. Esas carpetas corresponden a la siguiente fase del producto de datos.
