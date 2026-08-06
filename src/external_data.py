from __future__ import annotations

import io
import urllib.request

import pandas as pd

from project_paths import EXTERNAL


TRM_URL = "https://www.datos.gov.co/resource/32sa-8pi3.csv?$limit=10000"
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
SEASON_MONTH = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
                "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def build_external(refresh: bool = True) -> pd.DataFrame:
    raw = EXTERNAL / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    trm_path, oni_path = raw / "trm_diaria.csv", raw / "oni.ascii.txt"
    if refresh or not trm_path.exists():
        trm_path.write_bytes(_download(TRM_URL))
    if refresh or not oni_path.exists():
        oni_path.write_bytes(_download(ONI_URL))

    trm = pd.read_csv(trm_path)
    trm["fecha"] = pd.to_datetime(trm["vigenciadesde"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    trm["valor"] = pd.to_numeric(trm["valor"], errors="coerce")
    trm_month = trm.groupby("fecha")["valor"].agg(trm_cop_usd="mean", trm_volatilidad="std")

    oni = pd.read_csv(oni_path, sep=r"\s+")
    oni["fecha"] = pd.to_datetime({"year": oni["YR"], "month": oni["SEAS"].map(SEASON_MONTH), "day": 1})
    oni_month = oni.set_index("fecha")[["ANOM"]].rename(columns={"ANOM": "oni_anomalia"})
    oni_month["enso_fase"] = pd.cut(
        oni_month["oni_anomalia"], bins=[-float("inf"), -0.5, 0.5, float("inf")],
        labels=["La Nina", "Neutral", "El Nino"], right=False,
    ).astype("string")

    combined = trm_month.join(oni_month, how="outer").sort_index().loc["2012-01-01":]
    combined.to_csv(EXTERNAL / "variables_externas_mensuales.csv", index_label="fecha")
    return combined


if __name__ == "__main__":
    print(build_external(refresh=True).tail(12))
