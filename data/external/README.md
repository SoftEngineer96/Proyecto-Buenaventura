# Variables externas

- `variables_externas_mensuales.csv`: promedio y volatilidad mensual de la TRM, anomalía ONI y fase ENSO.
- `raw/trm_diaria.csv`: fuente diaria de la Superintendencia Financiera publicada en Datos Abiertos Colombia.
- `raw/oni.ascii.txt`: índice ONI publicado por NOAA Climate Prediction Center.

El modelo desplaza estas variables un mes antes de utilizarlas para evitar fuga temporal.
