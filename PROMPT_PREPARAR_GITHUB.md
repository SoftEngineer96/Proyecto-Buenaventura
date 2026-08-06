# Prompt para dejar el proyecto listo para GitHub

Copie todo el bloque siguiente y péguelo como mensaje. Está escrito para ejecutarse sin más contexto que la carpeta del proyecto.

---

````
Actúa como ingeniero de datos senior. Vas a preparar el proyecto que está en la carpeta
conectada para publicarlo en un repositorio público de GitHub, sin alterar la lógica del
pipeline ni los resultados.

## Contexto verificado del proyecto

Es un proyecto de ciencia de datos en Python que pronostica las importaciones mensuales
registradas por la aduana 35 de Buenaventura (valor CIF en dólares y peso neto en
kilogramos), a partir de microdatos públicos del DANE.

- Pesa 8,7 GB en disco, de los cuales 8,3 GB son ZIP originales del DANE en `data/raw`.
- Con el `.gitignore` actual se publicarían 65 archivos y 3,8 MB; quedan fuera 8,69 GB.
- Ningún archivo supera los 100 MB.
- Estructura: `src` (12 módulos y 5 notebooks), `tests`, `data` en capas
  raw/landing/trusted/surface, `modelos`, `reportes`, y las carpetas vacías `api` y `webapp`.
- La suite de pruebas es `tests/test_project.py` y actualmente pasa 7 de 7.
- No hay repositorio git inicializado.

## Tareas

### 1. Completar el `.gitignore`

Faltan patrones y uno de ellos es un riesgo real: el README instruye crear el entorno
virtual dentro del proyecto (`python -m venv .venv`, línea 59) y `.venv/` NO está
ignorado. Un entorno pesa unos 240 MB de binarios.

Añade, conservando todo lo que ya existe:

    .venv/
    venv/
    env/
    .env
    .env.*
    .vscode/
    .idea/
    .DS_Store
    Thumbs.db
    node_modules/
    *.egg-info/
    .pytest_cache/

No ignores `modelos/*.joblib` ni `data/trusted/*.csv.gz`: son pequeños y hacen el
repositorio reproducible. Deja un comentario en el archivo explicando esa decisión.

### 2. Limpiar las rutas locales de los notebooks

Los cinco notebooks de `src` tienen salidas guardadas que exponen la ruta personal del
autor. Son 7 ocurrencias de la cadena `C:\Users\juanc\Desktop\Proyecto_Buenaventura_Final`
repartidas así: 00_descargas (1), 01_consolidar (3), 02_limpieza (1), 03_EDA (1),
04_modelo (1).

Reemplaza esa ruta por `<RUTA_DEL_PROYECTO>` únicamente dentro de los `outputs` de las
celdas. NO toques el código fuente de las celdas, NO borres las salidas y NO alteres los
`execution_count`: la prueba `test_notebooks_are_executed_without_errors` verifica que
todas las celdas tengan `execution_count` y ninguna salida de tipo `error`.

Hazlo con un script en Python usando `nbformat` o edición del JSON, no a mano.

### 3. Añadir licencia

Crea un archivo `LICENSE` con la licencia MIT, titular "Juan Manuel Tejada Fajardo y
Jesús Alejandro Guerrero", año 2026. Sin licencia, GitHub interpreta "todos los derechos
reservados" y nadie puede reutilizar el trabajo legalmente, lo que contradice un proyecto
construido sobre datos abiertos.

### 4. Reescribir el `README.md` para GitHub

El README actual es una nota interna: da instrucciones solo en PowerShell, habla de subir
la carpeta a Google Drive y dice textualmente que los datos "no deben subirse a Git o
Bitbucket". Reescríbelo pensando en alguien que llega al repositorio sin conocer el
proyecto. Debe incluir, en este orden:

1. Título y una descripción de dos o tres líneas.
2. Badges de Python y licencia.
3. **Resultados**, arriba y visibles: tabla con el WAPE de los tres modelos por cada
   objetivo, y el pronóstico vigente. Usa las cifras reales de
   `reportes/metricas_modelos.csv` y `data/surface/proximo_pronostico.csv`; léelos, no los
   inventes.
4. **Cómo obtener los datos.** Los 8,3 GB no están en el repositorio. Explica que
   `data/raw/MANIFIESTO_DATOS.json` contiene la huella SHA-256 de los 20 archivos de
   origen, de modo que cualquiera puede descargarlos del DANE y verificar que tiene
   exactamente los mismos. Incluye el comando para regenerarlos y el de verificación.
   Este es un punto fuerte del proyecto que hoy no está contado en ninguna parte.
5. **Instalación y ejecución**, con comandos para Linux/macOS *y* para Windows.
6. **Estructura del repositorio**, en árbol comentado.
7. **Metodología**, en un párrafo: validación walk-forward de 24 pasos, comparación contra
   naive estacional, WAPE como métrica principal, todas las variables desplazadas al menos
   un mes.
8. **Requisitos de hardware.** El EDA carga 2.249 MB en pandas y necesita cerca de 8 GB de
   RAM libre; con menos, el proceso muere sin mensaje. El modelado corre en 6 segundos.
9. **Limitaciones**, honestas y en lista: horizonte de un mes; intervalos aproximados; las
   variables externas aportan asociación y no causalidad; el registro aduanero no describe
   la operación portuaria; no hay API ni aplicación web desplegada.
10. **Fuentes de datos** con enlaces, y **licencia**.

Escríbelo en español, en prosa clara, sin emojis.

### 5. Corregir la incoherencia de plataforma

Busca todas las menciones a Bitbucket en los archivos versionables y actualízalas a
GitHub, o reformúlalas de manera neutra ("control de versiones"). Hay al menos una en el
README, línea 43.

### 6. Fijar la versión de scikit-learn

`requirements.txt` dice `scikit-learn>=1.5`, pero los modelos serializados en `modelos/`
se entrenaron con 1.9.0 y cargarlos con otra versión emite `InconsistentVersionWarning`.
Cámbialo a `scikit-learn==1.9.0`. Añade también `pillow>=10.0`, que `src/render_pdf_qa.py`
importa y no está declarado.

### 7. Inicializar el repositorio

Ejecuta `git init`, configura la rama principal como `main`, y haz un primer commit con
todo lo que el `.gitignore` permita. Mensaje del commit:

    Proyecto de pronóstico de importaciones - Aduana de Buenaventura

NO ejecutes `git remote add` ni `git push`: eso lo hará el usuario.

## Restricciones

- No modifiques la lógica de `src/pipeline.py`, `src/modeling.py`, `src/eda_compute.py`
  ni `src/predict.py`.
- No toques nada dentro de `data/`, salvo lo que indique el `.gitignore`.
- No borres las carpetas `api/` y `webapp/`; solo menciona en el README que corresponden a
  una fase posterior.

## Verificación obligatoria antes de terminar

Ejecuta y reporta el resultado de cada punto:

1. `python -m pytest tests -q` debe seguir dando 7 passed.
2. `git status --short` y `git ls-files | wc -l` para confirmar qué quedó versionado.
3. Peso total de lo versionado: debe rondar los 3,8 MB y ningún archivo debe superar
   100 MB.
4. Búsqueda de credenciales: `grep -rInE "(api[_-]?key|secret|token|password|bearer)"`
   sobre los archivos versionados. Debe salir vacío.
5. Búsqueda de rutas personales: no debe quedar ninguna ocurrencia de `C:\Users` ni de
   `juanc` en los archivos versionados.
6. Confirmar que `.venv` está efectivamente ignorado, creando una carpeta de prueba y
   comprobando que `git status` no la reporta.

Si alguna verificación falla, corrígela antes de continuar.

## Entregable final

Cuando termines todo, crea el archivo `REPORTE_PREPARACION_GITHUB.md` en la raíz del
proyecto. Debe ser un informe de lo que efectivamente hiciste, no una copia de estas
instrucciones. Incluye:

- **Resumen**: dos o tres frases sobre el estado en que quedó el proyecto.
- **Tabla de cambios**: una fila por archivo modificado o creado, con qué se hizo y por qué.
- **Antes y después**: número de archivos versionados, peso total, ocurrencias de rutas
  personales, y estado de la suite de pruebas.
- **Resultados de las seis verificaciones**, con la salida real de cada comando.
- **Decisiones tomadas**: por qué se conservaron los `.joblib` y los agregados de
  `data/trusted` en el repositorio, y por qué los 8,3 GB de `data/raw` quedan fuera.
- **Lo que queda pendiente**: cualquier cosa que no pudiste resolver, y los siguientes
  pasos para el usuario (crear el repositorio en GitHub, añadir el remoto, hacer push).

Escríbelo en español, con fecha, en prosa clara. Que sirva como registro de qué se cambió
y como guía para el paso siguiente.
````

---

## Notas de uso

- El prompt asume que la carpeta del proyecto está conectada y es la carpeta de trabajo.
- Todas las cifras que contiene fueron verificadas sobre el estado real del proyecto: los 3,8 MB versionables, los 8,69 GB excluidos, las 7 ocurrencias de rutas personales y su reparto por notebook, la línea 59 del README y la 43 de la mención a Bitbucket.
- El paso 7 se detiene antes del `push` a propósito: crear el repositorio remoto y decidir si es público o privado es una decisión suya.
- Si prefiere licencia Creative Commons en lugar de MIT —razonable para un trabajo académico—, cambie el punto 3 por `CC BY 4.0`.
