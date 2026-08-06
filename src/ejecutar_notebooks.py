from __future__ import annotations

import os
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT.parent / ".runtime"
RUNTIME.mkdir(exist_ok=True)
os.environ.setdefault("IPYTHONDIR", str(RUNTIME / "ipython"))
os.environ.setdefault("JUPYTER_CONFIG_DIR", str(RUNTIME / "jupyter_config"))
os.environ.setdefault("JUPYTER_DATA_DIR", str(RUNTIME / "jupyter_data"))
os.environ.setdefault("JUPYTER_RUNTIME_DIR", str(RUNTIME / "jupyter_runtime"))


def execute(path: Path) -> None:
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    client.execute()
    nbformat.write(notebook, path)
    print(f"OK {path.name}")


if __name__ == "__main__":
    names = sys.argv[1:] or [
        "00_descargas.ipynb",
        "01_consolidar.ipynb",
        "02_limpieza.ipynb",
        "03_EDA.ipynb",
        "04_modelo.ipynb",
    ]
    for name in names:
        execute(ROOT / name)
