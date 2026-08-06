from __future__ import annotations

import hashlib
import json

from project_paths import RAW_DANE, RAW_DIAN, ROOT


def sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest() -> dict:
    files = sorted(RAW_DANE.glob("*.zip")) + sorted(RAW_DIAN.glob("*"))
    manifest = {
        "base": "data/raw",
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files if path.is_file()
        ],
        "sources": {
            "DANE_2012_2024": "https://microdatos.dane.gov.co/index.php/catalog/473/get-microdata",
            "DANE_2025_2026": "https://microdatos.dane.gov.co/index.php/catalog/856/get-microdata",
            "DIAN": "https://www.dian.gov.co/dian/cifras/Paginas/Consultor-de-Importaciones-y-Exportaciones-para-Seccionales.aspx",
        },
    }
    destination = ROOT / "data" / "raw" / "MANIFIESTO_DATOS.json"
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(f"Archivos registrados: {len(build_manifest()['files'])}")
