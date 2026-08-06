# Auditoría del código — verificación de los hallazgos H2 y H3

**Fecha:** 5 de agosto de 2026
**Método:** lectura directa de `src/modeling.py`, `tests/test_project.py`, `reportes/metricas_modelos.csv` y `data/surface/proximo_pronostico.csv`.
**Limitación:** no se pudo ejecutar el pipeline. Todo lo de abajo proviene de leer el código y los archivos de resultados, no de correrlos.

---

## Resumen

Dos hallazgos de la auditoría anterior cambian de conclusión al ver el código.

| Hallazgo | Conclusión anterior | Conclusión tras leer el código |
|---|---|---|
| **H2 — Fuga temporal** | "Los resultados se publican sin la prueba anti-fuga; la mejora de 55 % es el patrón típico de una fuga" | **Refutado en lo esencial.** La construcción de variables y el walk-forward son correctos. No hay fuga contemporánea. |
| **H3 — Intervalos** | "Derivados del WAPE; cobertura real ≈ 69 %" | **Corregido.** Se derivan del RMSE del backtest, que es el estimador correcto. El método es defendible; lo que falta es medir la cobertura. |

Ambas correcciones van a favor del proyecto. Se documentan aquí para que no se defienda algo que ya está bien, ni se corrija algo que no está roto.

---

## H2 — Fuga temporal: qué encontré

### Lo que está bien

**1. Los rezagos están correctamente desplazados** (`modeling.py`, líneas 57-64).

```python
for lag in LAGS:                       # LAGS = [1, 2, 3, 6, 12]
    features[f"{target}_lag_{lag}"] = series[target].shift(lag)
```

Ningún rezago es menor que 1. No hay variable contemporánea del objetivo.

**2. Las medias móviles se desplazan ANTES de promediar** (líneas 60-61).

```python
features[f"{target}_media_3"]  = series[target].shift(1).rolling(3).mean()
features[f"{target}_media_12"] = series[target].shift(1).rolling(12).mean()
```

Este es el error más común en series de tiempo: hacer `.rolling(3).mean().shift(1)` en vez de `.shift(1).rolling(3)`. Aquí está en el orden correcto. La media incluye únicamente meses anteriores al que se predice.

**3. Las variables externas también van rezagadas** (línea 68).

```python
external_numeric = external.select_dtypes(include="number").shift(1).add_suffix("_lag_1")
```

TRM y ONI entran con un mes de rezago. Es incluso conservador: la TRM del Banco de la República está disponible en tiempo real.

**4. El walk-forward entrena estrictamente con el pasado** (líneas 92-95).

```python
for date in test_dates:
    train = model_data.loc[model_data.index < date]
    model.fit(train[feature_cols], train[target])
    prediction = model.predict(model_data.loc[[date], feature_cols])
```

El `<` estricto es correcto. Cada corte reentrena desde cero.

**5. El escalador se ajusta dentro de cada corte** (línea 29).

```python
make_pipeline(StandardScaler(), Ridge(alpha=10.0))
```

Al estar dentro del pipeline, `StandardScaler` se ajusta solo con los datos de entrenamiento de cada fold. Este es el segundo error más común y aquí también está bien resuelto.

**6. Ya existe una prueba automatizada contra fuga** (`tests/test_project.py`, línea 37).

```python
def test_model_table_has_no_contemporaneous_leakage():
    forbidden = {"fob_usd", "flete_usd", "seguros_usd", "registros", "paises_origen", "capitulos"}
    predictors = set(data) - {"fecha", "cif_usd", "peso_neto_kg"}
    assert not predictors.intersection(forbidden)
    assert all(c in {"tendencia","mes_sin","mes_cos"} or "_lag_" in c or "_media_" in c for c in predictors)
```

Verifica que ninguna variable contemporánea llegue a la tabla de modelado.

### Lo que sigue pendiente

Nada de lo anterior cubre la **fuga operacional**, que es distinta de la contemporánea: una variable puede estar correctamente rezagada un mes y aun así no haber estado publicada en la fecha real del pronóstico.

El caso concreto: el DANE publica las importaciones con un rezago de hasta 45 días después del mes de referencia. Si el modelo usa `cif_usd_lag_1` para predecir el mes M, necesita el dato del mes M-1, que puede no estar publicado todavía cuando llega el momento de predecir M.

**Esto no está verificado en ninguna parte del código.** Sigue siendo la P43 del EDA V4 y sigue siendo obligatoria.

### Entonces, ¿por qué la mejora es de 55 %?

No por fuga. Por la línea base.

`Naive_12` predice el mes M con el valor de M-12. Sobre una serie con un cambio de nivel documentado de +45,84 % entre subperiodos, esa referencia está condenada a fallar. Mientras tanto, el modelo dispone de `lag_1`, `lag_2`, `lag_3`, `lag_6`, `lag_12`, `media_3` y `media_12`.

Comparar un modelo que ve el mes pasado contra una referencia que solo ve el año pasado, en una serie con persistencia de 0,871 en el rezago 1, no es una comparación exigente.

> **Acción prioritaria:** añadir `Naive_1` (el valor del mes anterior) y `drift`. Es el cambio de mayor valor diagnóstico de todo el proyecto y son unas pocas líneas. Si la mejora sobre `Naive_1` sigue siendo grande, el resultado queda blindado. Si se reduce mucho, es mejor saberlo antes de la sustentación que durante.

---

## H3 — Intervalos: qué encontré

### El método real

`modeling.py`, líneas 162-167:

```python
rmse = float(row["RMSE"])
"limite_inferior_80": max(forecast - 1.2816 * rmse, 0),
"limite_superior_80": forecast + 1.2816 * rmse,
```

El intervalo es **± 1,2816 × RMSE del backtest**. Verificación aritmética con los archivos:

| Objetivo | RMSE | 1,2816 × RMSE | Límite inferior calculado | Límite inferior en el archivo |
|---|---|---|---|---|
| CIF | 151.264.087 | 193.860.053 | 1.877.015.257 | 1.877.015.256 |
| Peso neto | 131.902.513 | 169.046.660 | 1.004.557.487 | 1.004.557.887 |

Coincide. El intervalo se construye desde el RMSE, no desde el WAPE.

**Corrección explícita:** la auditoría anterior afirmó que el intervalo se derivaba del WAPE y estimó una cobertura real cercana al 69 %. Esa estimación partía de inferir la desviación típica a partir del error absoluto medio suponiendo normalidad. El código usa el RMSE, que es el estimador directo de la desviación típica. La afirmación anterior era incorrecta.

Un chequeo adicional de consistencia: para errores normales, RMSE/MAE debería valer √(π/2) ≈ 1,253. En los datos: 151,26/124,18 = **1,218** para CIF y 131,90/112,12 = **1,176** para peso neto. Cerca de lo normal y ligeramente por debajo, lo que sugiere colas algo más ligeras que la normal. El supuesto de normalidad es razonable.

### Lo que sí sigue mal

**1. Nadie ha medido la cobertura empírica.**
Existen las 24 predicciones del backtest en `data/surface/predicciones_validacion.csv`. Contar cuántas de esas 24 caen dentro de su propio intervalo de 80 % es un cálculo de tres líneas y no está hecho. Sin ese número, "80 %" es una etiqueta, no un hecho medido. Es la P51 del EDA V4.

**2. El RMSE viene del mismo periodo que eligió al modelo.**
En la línea 134:

```python
best = metrics_frame.loc[metrics_frame.groupby("target")["WAPE_pct"].idxmin()]
```

El mejor modelo se escoge minimizando el WAPE sobre los mismos 24 meses cuyo RMSE luego define el intervalo. La selección y la evaluación comparten datos, así que tanto el error reportado como el ancho del intervalo son optimistas. Con solo tres candidatos el sesgo es pequeño, pero existe y hay que declararlo.

**3. El intervalo tiene ancho fijo.**
Se usa el mismo ± 193.860.053 sin importar el nivel de la serie. Si la variabilidad crece con el nivel —lo esperable tras un salto de +45,84 %— el intervalo queda ancho al principio de la serie y estrecho al final. Esta es exactamente la **P23** que se repuso en el EDA V4, y es la razón por la que debe ejecutarse antes de la fase de modelado.

**4. El RMSE se estima con 24 puntos.**
Su propio error de estimación ronda el 15 %. Ampliar a 36 y 48 cortes es la P48.

---

## Otros hallazgos del código

| # | Observación | Ubicación | Severidad |
|---|---|---|---|
| C1 | No existen `Naive_1` ni `drift`; tampoco MASE | `modeling.py` línea 116 | Alta |
| C2 | `test_months=24` está fijo; no hay sensibilidad a 36 ni 48 | `modeling.py` línea 87 | Media |
| C3 | No se calcula sesgo (error con signo) ni porcentaje de cortes ganados | `metrics()`, línea 75 | Media |
| C4 | `MAPE` divide por `y` sin valor absoluto; falla si algún valor es 0 o negativo | `modeling.py` línea 82 | Baja |
| C5 | La línea base usa `data[target].dropna()` y los modelos `data[...].dropna()` completo. Si faltara TRM u ONI en meses recientes, las ventanas de prueba no coincidirían y la comparación sería inválida | líneas 89 y 113 | Media — **verificar** |
| C6 | No existe la variable CIF por kilogramo | `build_feature_table()` | Alta |
| C7 | No hay análisis de ablación de grupos de variables | — | Media |
| C8 | La prueba de fuga cubre lo contemporáneo, no la disponibilidad real de publicación | `test_project.py` línea 37 | Alta |

### Sobre C5

Vale la pena comprobarlo explícitamente porque invalidaría la comparación entera y es invisible a simple vista:

```python
import pandas as pd
data = pd.read_csv("data/trusted/datos_limpios_ml.csv", parse_dates=["fecha"]).set_index("fecha")
target = "cif_usd"
feature_cols = [c for c in data.columns if c not in ["cif_usd", "peso_neto_kg"]]

ventana_modelo = data[[target] + feature_cols].dropna().index[-24:]
ventana_naive  = data[target].dropna().index[-24:]

print("Modelo:", ventana_modelo.min().date(), "a", ventana_modelo.max().date())
print("Naive :", ventana_naive.min().date(),  "a", ventana_naive.max().date())
print("Coinciden:", list(ventana_modelo) == list(ventana_naive))
```

Si imprime `False`, el WAPE del modelo y el de la línea base se calcularon sobre meses distintos y no son comparables.

---

## Qué ejecutar primero

En orden de valor por esfuerzo:

1. **Cobertura empírica de los intervalos.** Ya tienes las 24 predicciones guardadas. Tres líneas de código y cierra la P51.
2. **Comprobación C5.** El fragmento de arriba. Descarta un problema que invalidaría toda la tabla de resultados.
3. **`Naive_1` y `drift` con MASE.** Unas pocas líneas y responde la pregunta más incómoda que puede hacer el jurado.
4. **CIF por kilogramo.** Una división, y separa precio de cantidad.
5. **P23, variabilidad frente al nivel.** Decide si el intervalo debe ser proporcional en vez de fijo.
6. **Calendario de disponibilidad (P43).** El único punto de fuga que sigue realmente abierto.
