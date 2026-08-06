from pathlib import Path
import json
import sys

import joblib
import nbformat
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_raw_sources_and_manifest():
    assert len(list((ROOT / "data/raw/dane").glob("Impo_*.zip"))) == 18
    manifest = json.loads((ROOT / "data/raw/MANIFIESTO_DATOS.json").read_text(encoding="utf-8"))
    assert len(manifest["files"]) == 20
    assert all(not item["path"].startswith(("C:", "/")) for item in manifest["files"])
    assert all(len(item["sha256"]) == 64 for item in manifest["files"])


def test_monthly_series_is_complete():
    series = pd.read_csv(ROOT / "data/trusted/serie_mensual_buenaventura.csv", parse_dates=["fecha"])
    expected = pd.date_range("2012-01-01", "2026-05-01", freq="MS")
    assert list(series["fecha"]) == list(expected)
    assert series[["cif_usd", "peso_neto_kg"]].notna().all().all()
    assert (series[["cif_usd", "peso_neto_kg"]] >= 0).all().all()


def test_external_features_have_history():
    external = pd.read_csv(ROOT / "data/external/variables_externas_mensuales.csv", parse_dates=["fecha"])
    selected = external.loc[external["fecha"].between("2012-01-01", "2026-05-01")]
    assert selected["trm_cop_usd"].notna().all()
    assert selected["oni_anomalia"].notna().all()


def test_model_table_has_no_contemporaneous_leakage():
    data = pd.read_csv(ROOT / "data/trusted/datos_limpios_ml.csv")
    forbidden = {"fob_usd", "flete_usd", "seguros_usd", "registros", "paises_origen", "capitulos"}
    predictors = set(data) - {"fecha", "cif_usd", "peso_neto_kg"}
    assert not predictors.intersection(forbidden)
    assert all(c in {"tendencia", "mes_sin", "mes_cos"} or "_lag_" in c or "_media_" in c for c in predictors)


def test_walk_forward_outputs_and_models():
    metrics = pd.read_csv(ROOT / "reportes/metricas_modelos.csv")
    assert len(metrics) == 6
    assert set(metrics["modelo"]) == {"Naive_12", "Ridge", "HistGradientBoosting"}
    assert metrics[["MAE", "RMSE", "MAPE_pct", "WAPE_pct"]].notna().all().all()
    packages = list((ROOT / "modelos").glob("*.joblib"))
    assert len(packages) == 2
    assert {joblib.load(path)["target"] for path in packages} == {"cif_usd", "peso_neto_kg"}


def test_forecast_is_one_month_ahead_and_unique():
    series = pd.read_csv(ROOT / "data/trusted/serie_mensual_buenaventura.csv", parse_dates=["fecha"])
    forecast = pd.read_csv(ROOT / "data/surface/proximo_pronostico.csv", parse_dates=["fecha_pronostico"])
    assert len(forecast) == 2
    assert not forecast["target"].duplicated().any()
    assert forecast["fecha_pronostico"].nunique() == 1
    assert forecast["fecha_pronostico"].iloc[0] == series["fecha"].max() + pd.offsets.MonthBegin(1)
    assert (forecast["prediccion"] >= 0).all()


def test_notebooks_are_executed_without_errors():
    for path in sorted((ROOT / "src").glob("0[0-4]_*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        assert code_cells
        assert all(cell.execution_count is not None for cell in code_cells)
        assert not [
            output for cell in code_cells for output in cell.get("outputs", [])
            if output.get("output_type") == "error"
        ]
