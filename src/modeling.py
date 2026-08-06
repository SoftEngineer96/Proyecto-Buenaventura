from __future__ import annotations

import os
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from project_paths import EXTERNAL, MODELS, REPORTS, SURFACE, TRUSTED

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")


TARGETS = ["cif_usd", "peso_neto_kg"]
LAGS = [1, 2, 3, 6, 12]
INTERNAL_LAG_COLUMNS = ["fob_usd", "flete_usd", "seguros_usd", "registros", "paises_origen", "capitulos"]


def candidate_models() -> dict:
    return {
        "Ridge": TransformedTargetRegressor(
            regressor=make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
            func=np.log1p,
            inverse_func=np.expm1,
        ),
        "HistGradientBoosting": TransformedTargetRegressor(
            regressor=HistGradientBoostingRegressor(
                max_depth=3, learning_rate=0.05, max_iter=300, random_state=42
            ),
            func=np.log1p,
            inverse_func=np.expm1,
        ),
    }


def load_inputs(append_next: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    series = pd.read_csv(TRUSTED / "serie_mensual_buenaventura.csv", parse_dates=["fecha"])
    series = series.sort_values("fecha").drop_duplicates("fecha").set_index("fecha").asfreq("MS")
    external = pd.read_csv(EXTERNAL / "variables_externas_mensuales.csv", parse_dates=["fecha"])
    external = external.set_index("fecha").sort_index()
    if append_next:
        next_date = series.index.max() + pd.offsets.MonthBegin(1)
        series = series.reindex(series.index.union(pd.DatetimeIndex([next_date])))
    return series, external


def build_feature_table(append_next: bool = False) -> pd.DataFrame:
    series, external = load_inputs(append_next=append_next)
    features = series[TARGETS].copy()
    for target in TARGETS:
        for lag in LAGS:
            features[f"{target}_lag_{lag}"] = series[target].shift(lag)
        features[f"{target}_media_3"] = series[target].shift(1).rolling(3).mean()
        features[f"{target}_media_12"] = series[target].shift(1).rolling(12).mean()
    for col in INTERNAL_LAG_COLUMNS:
        if col in series:
            features[f"{col}_lag_1"] = series[col].shift(1)
    features["tendencia"] = np.arange(len(features))
    features["mes_sin"] = np.sin(2 * np.pi * features.index.month / 12)
    features["mes_cos"] = np.cos(2 * np.pi * features.index.month / 12)
    external_numeric = external.select_dtypes(include="number").shift(1).add_suffix("_lag_1")
    features = features.join(external_numeric, how="left")
    if not append_next:
        features.to_csv(TRUSTED / "datos_limpios_ml.csv", index_label="fecha")
    return features


def metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    y = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    absolute = np.abs(y - pred)
    return {
        "MAE": float(mean_absolute_error(y, pred)),
        "RMSE": float(mean_squared_error(y, pred) ** 0.5),
        "MAPE_pct": float(np.mean(absolute / y) * 100),
        "WAPE_pct": float(absolute.sum() / np.abs(y).sum() * 100),
    }


def walk_forward(target: str, model_name: str, model, data: pd.DataFrame, test_months: int = 24):
    feature_cols = [c for c in data.columns if c not in TARGETS]
    model_data = data[[target] + feature_cols].dropna()
    test_dates = model_data.index[-test_months:]
    predictions = []
    for date in test_dates:
        train = model_data.loc[model_data.index < date]
        model.fit(train[feature_cols], train[target])
        prediction = max(float(model.predict(model_data.loc[[date], feature_cols])[0]), 0.0)
        predictions.append(prediction)
    actual = model_data.loc[test_dates, target]
    frame = pd.DataFrame({
        "fecha": test_dates, "target": target, "modelo": model_name,
        "real": actual.to_numpy(), "prediccion": predictions,
    })
    return metrics(actual, predictions), frame, feature_cols, model_data


def train_and_evaluate(test_months: int = 24) -> tuple[pd.DataFrame, pd.DataFrame]:
    for stale in MODELS.glob("*.joblib"):
        stale.unlink()
    data = build_feature_table(append_next=False)
    metric_rows, prediction_frames = [], []
    fitted_candidates = {}
    for target in TARGETS:
        valid = data[target].dropna()
        test_dates = valid.index[-test_months:]
        naive = valid.shift(12).reindex(test_dates)
        actual = valid.reindex(test_dates)
        metric_rows.append({"target": target, "modelo": "Naive_12", **metrics(actual, naive)})
        prediction_frames.append(pd.DataFrame({
            "fecha": test_dates, "target": target, "modelo": "Naive_12",
            "real": actual.to_numpy(), "prediccion": naive.to_numpy(),
        }))
        for name, estimator in candidate_models().items():
            score, predictions, feature_cols, model_data = walk_forward(
                target, name, estimator, data, test_months=test_months
            )
            metric_rows.append({"target": target, "modelo": name, **score})
            prediction_frames.append(predictions)
            fitted_candidates[(target, name)] = (estimator, feature_cols, model_data)

    metrics_frame = pd.DataFrame(metric_rows).sort_values(["target", "WAPE_pct"])
    predictions_frame = pd.concat(prediction_frames, ignore_index=True)
    metrics_frame.to_csv(REPORTS / "metricas_modelos.csv", index=False)
    predictions_frame.to_csv(SURFACE / "predicciones_validacion.csv", index=False)

    best = metrics_frame.loc[metrics_frame.groupby("target")["WAPE_pct"].idxmin()]
    next_features = build_feature_table(append_next=True)
    forecasts = []
    for _, row in best.iterrows():
        target, model_name = row["target"], row["modelo"]
        if model_name == "Naive_12":
            forecast_date = next_features.index.max()
            forecast = float(next_features.loc[forecast_date, f"{target}_lag_12"])
            feature_cols = []
            trained_through = data[target].dropna().index.max()
            joblib.dump({
                "model_name": "Naive_12", "features": [f"{target}_lag_12"], "target": target,
                "trained_through": str(trained_through.date()), "forecast_date": str(forecast_date.date()),
            }, MODELS / f"{target}_Naive_12.joblib")
        else:
            estimator, feature_cols, model_data = fitted_candidates[(target, model_name)]
            estimator.fit(model_data[feature_cols], model_data[target])
            forecast_date = next_features.index.max()
            row_features = next_features.loc[[forecast_date], feature_cols]
            if row_features.isna().any().any():
                missing = row_features.columns[row_features.isna().any()].tolist()
                raise ValueError(f"Features faltantes para inferencia: {missing}")
            forecast = max(float(estimator.predict(row_features)[0]), 0.0)
            trained_through = model_data.index.max()
            joblib.dump({
                "model": estimator, "model_name": model_name, "features": feature_cols, "target": target,
                "trained_through": str(trained_through.date()), "forecast_date": str(forecast_date.date()),
            }, MODELS / f"{target}_{model_name}.joblib")
        rmse = float(row["RMSE"])
        forecasts.append({
            "fecha_pronostico": forecast_date, "target": target, "modelo": model_name,
            "prediccion": forecast, "limite_inferior_80": max(forecast - 1.2816 * rmse, 0),
            "limite_superior_80": forecast + 1.2816 * rmse,
            "entrenado_hasta": trained_through,
        })
    forecast_frame = pd.DataFrame(forecasts)
    forecast_frame.to_csv(SURFACE / "proximo_pronostico.csv", index=False)
    return metrics_frame, forecast_frame


if __name__ == "__main__":
    metrics_frame, forecast_frame = train_and_evaluate(test_months=24)
    print(metrics_frame)
    print(forecast_frame)
