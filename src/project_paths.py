from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    configured = os.environ.get("PROYECTO_BUENAVENTURA_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
    else:
        root = Path(__file__).resolve().parents[1]
    if not (root / "data").exists():
        raise FileNotFoundError(f"No se encontró la carpeta data en {root}")
    return root


ROOT = project_root()
RAW_DANE = ROOT / "data" / "raw" / "dane"
RAW_DIAN = ROOT / "data" / "raw" / "dian"
LANDING = ROOT / "data" / "landing"
TRUSTED = ROOT / "data" / "trusted"
SURFACE = ROOT / "data" / "surface"
EXTERNAL = ROOT / "data" / "external"
REPORTS = ROOT / "reportes"
FIGURES = REPORTS / "figuras"
MODELS = ROOT / "modelos"

for folder in [RAW_DANE, RAW_DIAN, LANDING, TRUSTED, SURFACE, EXTERNAL, REPORTS, FIGURES, MODELS]:
    folder.mkdir(parents=True, exist_ok=True)
