from __future__ import annotations

import joblib
import pandas as pd

from modeling import build_feature_table
from project_paths import MODELS, SURFACE


def predict_next_month() -> pd.DataFrame:
    features = build_feature_table(append_next=True)
    date = features.index.max()
    rows = []
    for path in sorted(MODELS.glob("*.joblib")):
        package = joblib.load(path)
        row = features.loc[[date], package["features"]]
        if row.isna().any().any():
            raise ValueError(f"Faltan variables para {path.name}")
        if package.get("model_name") == "Naive_12":
            prediction = float(row.iloc[0, 0])
        else:
            prediction = max(float(package["model"].predict(row)[0]), 0.0)
        rows.append({"fecha_pronostico": date, "target": package["target"], "prediccion": prediction})
    result = pd.DataFrame(rows)
    if set(result["target"]) != {"cif_usd", "peso_neto_kg"} or result["target"].duplicated().any():
        raise RuntimeError("Debe existir exactamente un modelo vigente por objetivo")
    result.to_csv(SURFACE / "proximo_pronostico_inferencia.csv", index=False)
    return result


if __name__ == "__main__":
    print(predict_next_month())
