# Guia de estudio: proyecto de Buenaventura

## Explicacion en 30 segundos

El proyecto estima, con un mes de anticipacion, el valor CIF y el peso neto mensual de las importaciones registradas por la aduana de Buenaventura. Usa registros DANE desde enero de 2012 hasta mayo de 2026, los agrega por mes e incorpora TRM y ONI de forma rezagada. La validacion walk-forward simula 24 pronosticos reales sin usar informacion futura.

## Cifras que debes recordar

- 6.703.355 registros de Buenaventura.
- 173 meses continuos, enero de 2012 a mayo de 2026.
- CIF: Ridge, WAPE 7,34 %.
- Peso neto: HGB, WAPE 9,51 %.
- Pronostico junio de 2026: USD 2.070.875.309,85 de CIF y 1.173.604.146,69 kg.

## Flujo

1. `00_descargas.ipynb`: obtiene y registra fuentes.
2. `01_consolidar.ipynb`: homologa y filtra ADUA = 35.
3. `02_limpieza.ipynb`: valida y crea la serie mensual.
4. `03_EDA.ipynb`: desarrolla 52 preguntas estadisticas.
5. `04_modelo.ipynb`: crea rezagos, valida, reentrena y pronostica.

## Idea central del modelado

Para pronosticar junio de 2026 solo se usa informacion disponible hasta mayo. Usar FOB, CIF, peso o TRM completa de junio seria fuga de informacion. La division de entrenamiento y prueba es cronologica y la validacion avanza un mes por vez.

## Resultados

Ridge fue seleccionado para CIF porque obtuvo WAPE de 7,34 %, frente a 16,49 % del modelo naive. HGB fue seleccionado para peso neto con WAPE de 9,51 %, frente a 13,66 % del naive. Los modelos finales se reentrenaron con toda la historia hasta mayo de 2026.

## Limitaciones

El EDA documental conserva el corte 2012-2024, mientras el modelo final esta actualizado a mayo de 2026. El pronostico tiene horizonte de un mes, los intervalos son aproximados y las variables externas aportan asociacion predictiva, no evidencia causal. La API y la aplicacion web quedan como fase posterior.

Consulta el tutorial Word en `reportes/Tutorial_Proyecto_Buenaventura.docx` para la explicacion completa, el guion de sustentacion y la autoevaluacion.
