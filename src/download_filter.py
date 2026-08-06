"""Compatibilidad con el nombre usado por la plantilla original."""

from pipeline import build_trusted, consolidate, download_sources


if __name__ == "__main__":
    download_sources()
    consolidate(force=True)
    build_trusted(force=True)
