from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.stattools import adfuller, acf


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "data" / "landing"
PROCESSED = ROOT / "data" / "trusted" / "eda_historico_2012_2024"
FIGURES = ROOT / "reportes" / "figuras"
PROCESSED.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(LANDING / "impo_buenaventura_2012_2024.csv.gz", low_memory=False)
numeric_cols = [
    "FECH", "ADUA", "PAISGEN", "PAISPRO", "PAISCOM", "DEPTODES", "VIATRANS",
    "PBK", "PNK", "CANU", "NABAN", "VAFODO", "FLETE", "VACID", "VACIP",
    "VADUA", "BASEIVA", "TOTALIVAYO", "SEGUROS", "TIPOIM", "PORARA", "DEREL",
]
for col in numeric_cols:
    if col in df:
        raw = df[col].astype("string").str.strip()
        localized = raw.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        normalized = raw.where(~raw.str.contains(",", na=False), localized)
        df[col] = pd.to_numeric(normalized, errors="coerce")

fech = df["FECH"].round().astype("Int64")
year = 2000 + (fech // 100)
month = fech % 100
valid_date = year.between(2012, 2024) & month.between(1, 12)
df["fecha"] = pd.to_datetime(
    {"year": year.where(valid_date), "month": month.where(valid_date), "day": 1},
    errors="coerce",
)
df["capitulo"] = (df["NABAN"] // 100_000_000).astype("Int64")

monthly = (
    df.groupby("fecha", observed=True)
    .agg(
        cif_usd=("VACID", "sum"),
        fob_usd=("VAFODO", "sum"),
        peso_neto_kg=("PNK", "sum"),
        flete_usd=("FLETE", "sum"),
        seguros_usd=("SEGUROS", "sum"),
        registros=("FECH", "size"),
        paises_origen=("PAISGEN", "nunique"),
        capitulos=("capitulo", "nunique"),
    )
    .sort_index()
    .asfreq("MS")
)
monthly["precio_implicito_usd_kg"] = monthly["cif_usd"] / monthly["peso_neto_kg"].replace(0, np.nan)
monthly["mes"] = monthly.index.month
monthly["anio"] = monthly.index.year

country_month = (
    df.groupby(["fecha", "PAISGEN"], observed=True)
    .agg(cif_usd=("VACID", "sum"), peso_neto_kg=("PNK", "sum"), registros=("FECH", "size"))
    .reset_index()
)
chapter_month = (
    df.groupby(["fecha", "capitulo"], observed=True)
    .agg(cif_usd=("VACID", "sum"), peso_neto_kg=("PNK", "sum"), registros=("FECH", "size"))
    .reset_index()
)

def pct(x: float) -> float:
    return round(float(x) * 100, 3)

def money(x: float) -> float:
    return round(float(x), 2)

def smape(y, pred):
    den = np.abs(y) + np.abs(pred)
    return float(np.mean(np.where(den == 0, 0, 2 * np.abs(pred - y) / den)) * 100)

def wape(y, pred):
    return float(np.abs(y - pred).sum() / np.abs(y).sum() * 100)

business_cols = [c for c in df.columns if not c.startswith("SOURCE_") and c != "fecha"]
duplicates = int(df.duplicated(subset=business_cols).sum())
null_pct = (df.isna().mean() * 100).sort_values(ascending=False)
rows_with_null = int(df.isna().any(axis=1).sum())
constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
cardinality = df.nunique(dropna=True).sort_values(ascending=False)

missing_drift = {}
for col in df.columns:
    rates = df[col].isna().groupby(df["fecha"].dt.year).mean()
    if rates.max() > 0:
        missing_drift[col] = float(rates.max() - rates.min())

invalid_numeric = {}
for col in numeric_cols:
    invalid_numeric[col] = int(pd.to_numeric(df[col], errors="coerce").isna().sum() - df[col].isna().sum())

value_cols = ["PBK", "PNK", "CANU", "VAFODO", "FLETE", "VACID", "VACIP", "VADUA", "BASEIVA", "TOTALIVAYO", "SEGUROS", "DEREL"]
negative_counts = {c: int((df[c] < 0).sum()) for c in value_cols}
impossible_dates = int(df["fecha"].isna().sum())

target = monthly["cif_usd"]
q1, q3 = target.quantile([0.25, 0.75])
iqr = q3 - q1
target_iqr_outliers = monthly.index[(target < q1 - 1.5 * iqr) | (target > q3 + 1.5 * iqr)]
target_z = np.abs(stats.zscore(target, nan_policy="omit"))
target_z_outliers = monthly.index[target_z > 3]
adf_level = adfuller(target.dropna(), autolag="AIC")
adf_logdiff = adfuller(np.log1p(target).diff().dropna(), autolag="AIC")
acf_vals = acf(target, nlags=12, fft=True)

raw_desc = df[value_cols].describe(percentiles=[0.25, 0.5, 0.75]).T
raw_shape = pd.DataFrame({
    "skew": df[value_cols].skew(numeric_only=True),
    "kurtosis": df[value_cols].kurtosis(numeric_only=True),
})
iqr_counts = {}
for c in value_cols:
    s = df[c].dropna()
    a, b = s.quantile([0.25, 0.75])
    d = b - a
    iqr_counts[c] = int(((s < a - 1.5 * d) | (s > b + 1.5 * d)).sum())
zero_pct = {c: pct(df[c].fillna(0).eq(0).mean()) for c in value_cols}

monthly_numeric = monthly.select_dtypes("number").drop(columns=["mes", "anio"])
corr = monthly_numeric.corr(method="spearman")

lagged = pd.DataFrame(index=monthly.index)
for lag in [1, 2, 3, 6, 12]:
    lagged[f"cif_lag_{lag}"] = target.shift(lag)
    lagged[f"peso_lag_{lag}"] = monthly["peso_neto_kg"].shift(lag)
for window in [3, 6, 12]:
    lagged[f"cif_media_{window}"] = target.shift(1).rolling(window).mean()
lagged["mes_sin"] = np.sin(2 * np.pi * monthly.index.month / 12)
lagged["mes_cos"] = np.cos(2 * np.pi * monthly.index.month / 12)
lagged["tendencia"] = np.arange(len(lagged))
lagged["target"] = target
model_df = lagged.dropna()

vif_features = ["cif_lag_1", "cif_lag_3", "cif_lag_6", "cif_lag_12", "cif_media_3", "cif_media_6", "cif_media_12"]
vif_x = model_df[vif_features].astype(float)
vif = {c: float(variance_inflation_factor(vif_x.values, i)) for i, c in enumerate(vif_features)}

country_totals = df.groupby("PAISGEN", observed=True)["VACID"].sum().sort_values(ascending=False)
chapter_totals = df.groupby("capitulo", observed=True)["VACID"].sum().sort_values(ascending=False)
country_counts = df["PAISGEN"].value_counts(dropna=False)
chapter_counts = df["capitulo"].value_counts(dropna=False)
rare_country_share = pct(country_counts[country_counts < 100].sum() / len(df))

season = monthly.groupby("mes")["cif_usd"].agg(["mean", "median", "std"])
season["indice_media"] = season["mean"] / target.mean()
trend_slope, trend_intercept, trend_r, trend_p, _ = stats.linregress(np.arange(len(target)), target)

train_period = target.loc[:"2021-12-01"]
recent_period = target.loc["2022-01-01":]
ks_stat, ks_p = stats.ks_2samp(train_period, recent_period)
median_shift = (recent_period.median() / train_period.median() - 1) * 100

features = [c for c in model_df.columns if c != "target"]
test_start = pd.Timestamp("2023-01-01")
train_mask = model_df.index < test_start
X_train, X_test = model_df.loc[train_mask, features].astype(float), model_df.loc[~train_mask, features].astype(float)
y_train, y_test = model_df.loc[train_mask, "target"].astype(float), model_df.loc[~train_mask, "target"].astype(float)

predictions = {
    "Naive estacional (t-12)": X_test["cif_lag_12"].to_numpy(),
}
models = {
    "Ridge": make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
    "Random Forest": RandomForestRegressor(n_estimators=400, min_samples_leaf=3, random_state=42, n_jobs=-1),
    "HistGradientBoosting": HistGradientBoostingRegressor(max_iter=300, max_leaf_nodes=15, learning_rate=0.05, l2_regularization=1.0, random_state=42),
}
for name, model in models.items():
    model.fit(X_train, np.log1p(y_train))
    predictions[name] = np.expm1(model.predict(X_test)).clip(min=0)

backtest = {}
for name, pred in predictions.items():
    backtest[name] = {
        "MAE": money(mean_absolute_error(y_test, pred)),
        "RMSE": money(mean_squared_error(y_test, pred) ** 0.5),
        "sMAPE_pct": round(smape(y_test.to_numpy(), np.asarray(pred)), 3),
        "WAPE_pct": round(wape(y_test.to_numpy(), np.asarray(pred)), 3),
    }

result = {
    "rows": int(len(df)),
    "columns": int(df.shape[1]),
    "memory_mb": round(float(df.memory_usage(deep=True).sum() / 1024**2), 2),
    "dtypes": {f"tipo_{i+1}_{k}": int(v) for i, (k, v) in enumerate(df.dtypes.astype(str).value_counts().items())},
    "date_min": str(monthly.index.min().date()),
    "date_max": str(monthly.index.max().date()),
    "months": int(len(monthly)),
    "missing_months": int(monthly.index.to_series().diff().dt.days.gt(32).sum()),
    "duplicates": duplicates,
    "duplicates_pct": pct(duplicates / len(df)),
    "null_pct": {k: round(float(v), 4) for k, v in null_pct.items() if v > 0},
    "rows_with_null": rows_with_null,
    "rows_with_null_pct": pct(rows_with_null / len(df)),
    "missing_drift": {k: round(v * 100, 3) for k, v in sorted(missing_drift.items(), key=lambda x: x[1], reverse=True)},
    "constant_cols": constant_cols,
    "cardinality_top": {k: int(v) for k, v in cardinality.head(10).items()},
    "invalid_numeric": invalid_numeric,
    "negative_counts": negative_counts,
    "impossible_dates": impossible_dates,
    "target_sum": money(target.sum()),
    "target_mean": money(target.mean()),
    "target_median": money(target.median()),
    "target_std": money(target.std()),
    "target_min": money(target.min()),
    "target_max": money(target.max()),
    "target_skew": round(float(target.skew()), 4),
    "target_kurtosis": round(float(target.kurtosis()), 4),
    "target_iqr_outlier_months": [str(x.date()) for x in target_iqr_outliers],
    "target_z_outlier_months": [str(x.date()) for x in target_z_outliers],
    "target_nulls": int(target.isna().sum()),
    "log_skew": round(float(np.log1p(target).skew()), 4),
    "acf_1": round(float(acf_vals[1]), 4),
    "acf_12": round(float(acf_vals[12]), 4),
    "adf_level_p": round(float(adf_level[1]), 6),
    "adf_logdiff_p": round(float(adf_logdiff[1]), 6),
    "raw_desc": json.loads(raw_desc.round(3).to_json()),
    "raw_shape": json.loads(raw_shape.round(4).to_json()),
    "iqr_counts": iqr_counts,
    "zero_pct": zero_pct,
    "scale_ratio": round(float(raw_desc["mean"].replace(0, np.nan).max() / raw_desc["mean"].replace(0, np.nan).min()), 2),
    "monthly_corr_target": {k: round(float(v), 4) for k, v in corr["cif_usd"].sort_values(ascending=False).items()},
    "lag_corr": {c: round(float(model_df[c].corr(model_df["target"], method="spearman")), 4) for c in features},
    "vif": {k: round(v, 3) for k, v in vif.items()},
    "countries": int(df["PAISGEN"].nunique()),
    "chapters": int(df["capitulo"].nunique()),
    "transport_modes": int(df["VIATRANS"].nunique()),
    "rare_country_share_pct": rare_country_share,
    "top_countries": {str(k): money(v) for k, v in country_totals.head(10).items()},
    "top5_country_share_pct": pct(country_totals.head(5).sum() / country_totals.sum()),
    "top_chapters": {str(k): money(v) for k, v in chapter_totals.head(10).items()},
    "top5_chapter_share_pct": pct(chapter_totals.head(5).sum() / chapter_totals.sum()),
    "seasonality": json.loads(season.round(4).to_json()),
    "trend_slope_monthly": money(trend_slope),
    "trend_r2": round(float(trend_r**2), 4),
    "trend_p": round(float(trend_p), 6),
    "drift_ks": round(float(ks_stat), 4),
    "drift_ks_p": round(float(ks_p), 6),
    "median_shift_pct": round(float(median_shift), 3),
    "backtest_period": [str(y_test.index.min().date()), str(y_test.index.max().date())],
    "backtest": backtest,
}

(PROCESSED / "eda_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
monthly.to_csv(PROCESSED / "serie_mensual_buenaventura.csv")
country_month.to_csv(PROCESSED / "pais_mes_buenaventura.csv.gz", index=False, compression="gzip")
chapter_month.to_csv(PROCESSED / "capitulo_mes_buenaventura.csv.gz", index=False, compression="gzip")

sns.set_theme(style="whitegrid", font="Arial")
plt.rcParams.update({"axes.edgecolor": "#222222", "text.color": "#111111", "axes.labelcolor": "#111111", "xtick.color": "#222222", "ytick.color": "#222222"})

fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(monthly.index, monthly["cif_usd"] / 1e6, color="#111111", linewidth=1.5)
ax.set(title="Valor CIF mensual registrado en Buenaventura", xlabel="Fecha", ylabel="Millones de US$")
fig.tight_layout(); fig.savefig(FIGURES / "01_serie_cif.png", dpi=180); plt.close(fig)

fig, ax = plt.subplots(figsize=(7.5, 4.5))
sns.histplot(np.log1p(monthly["cif_usd"]), bins=18, color="#666666", edgecolor="#111111", ax=ax)
ax.set(title="Distribución logarítmica del valor CIF mensual", xlabel="log(1 + CIF mensual)", ylabel="Frecuencia")
fig.tight_layout(); fig.savefig(FIGURES / "02_distribucion_target.png", dpi=180); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 5.5))
sns.heatmap(corr, cmap="Greys", center=0, annot=True, fmt=".2f", cbar=False, ax=ax)
ax.set_title("Correlaciones de Spearman en la serie mensual")
fig.tight_layout(); fig.savefig(FIGURES / "03_correlaciones.png", dpi=180); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.5))
season["indice_media"].plot(kind="bar", color="#777777", edgecolor="#111111", ax=ax)
ax.axhline(1, color="#111111", linewidth=1)
ax.set(title="Índice estacional mensual del valor CIF", xlabel="Mes", ylabel="Media mensual / media global")
fig.tight_layout(); fig.savefig(FIGURES / "04_estacionalidad.png", dpi=180); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.5))
(country_totals.head(10).sort_values() / 1e9).plot(kind="barh", color="#777777", edgecolor="#111111", ax=ax)
ax.set(title="Diez países de origen con mayor valor CIF acumulado", xlabel="Miles de millones de US$", ylabel="Código de país")
fig.tight_layout(); fig.savefig(FIGURES / "05_paises.png", dpi=180); plt.close(fig)

print(json.dumps({"rows": result["rows"], "months": result["months"], "backtest": result["backtest"]}, ensure_ascii=False, indent=2))
