from __future__ import annotations

import gzip
import io
import json
import re
import shutil
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from project_paths import LANDING, RAW_DANE, SURFACE, TRUSTED


FILES = {
    "Impo_2012.zip": (473, 9028), "Impo_2013.zip": (473, 9029),
    "Impo_2014.zip": (473, 9030), "Impo_2015.zip": (473, 9031),
    "Impo_2016.zip": (473, 9032), "Impo_2017.zip": (473, 10346),
    "Impo_2018.zip": (473, 10347), "Impo_2019.zip": (473, 12602),
    "Impo_2020.zip": (473, 20042), "Impo_2021_1.zip": (473, 20838),
    "Impo_2021_2.zip": (473, 20986), "Impo_2022_1.zip": (473, 22185),
    "Impo_2022_2.zip": (473, 22306), "Impo_2023.zip": (473, 23290),
    "Impo_2024.zip": (473, 24390), "Impo_2025_1.zip": (856, 24417),
    "Impo_2025_2.zip": (856, 24464), "Impo_2026.zip": (856, 24738),
}

KEEP = [
    "FECH", "ADUA", "PAISGEN", "PAISPRO", "PAISCOM", "DEPTODES", "VIATRANS",
    "REGIMEN", "PBK", "PNK", "CANU", "NABAN", "VAFODO", "FLETE", "VACID",
    "VACIP", "VADUA", "BASEIVA", "TOTALIVAYO", "SEGUROS", "TIPOIM", "PORARA", "DEREL",
]
NUMERIC = [c for c in KEEP if c != "REGIMEN"]
MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def valid_zip(path: Path, full_crc: bool = False) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None if full_crc else bool(archive.infolist())
    except (FileNotFoundError, zipfile.BadZipFile):
        return False


def download_sources() -> None:
    for name, (catalog, file_id) in FILES.items():
        target = RAW_DANE / name
        if valid_zip(target):
            print(f"OK existente: {name}")
            continue
        partial = target.with_suffix(".zip.part")
        partial.unlink(missing_ok=True)
        url = f"https://microdatos.dane.gov.co/index.php/catalog/{catalog}/download/{file_id}"
        print(f"Descargando: {name}")
        with urllib.request.urlopen(url, timeout=300) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output, length=8 * 1024 * 1024)
        partial.replace(target)
        if not valid_zip(target, full_crc=True):
            raise RuntimeError(f"ZIP inválido: {target}")


def month_from_name(name: str) -> int | None:
    low = name.lower()
    return next((number for label, number in MONTHS.items() if label in low), None)


def iter_csv_streams(archive: zipfile.ZipFile):
    for info in archive.infolist():
        low = info.filename.lower()
        if low.endswith(".csv"):
            yield info.filename, archive.open(info)
        elif low.endswith(".zip"):
            nested_bytes = archive.read(info)
            with zipfile.ZipFile(io.BytesIO(nested_bytes)) as nested:
                for nested_info in nested.infolist():
                    if nested_info.filename.lower().endswith(".csv"):
                        yield f"{info.filename}!{nested_info.filename}", io.BytesIO(nested.read(nested_info))


def normalize_columns(columns) -> list[str]:
    return [re.sub(r"[^A-Z0-9]", "", str(c).upper()) for c in columns]


def normalize_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    for col in [c for c in NUMERIC if c in frame]:
        raw = frame[col].astype("string").str.strip()
        localized = raw.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        frame[col] = pd.to_numeric(raw.where(~raw.str.contains(",", na=False), localized), errors="coerce")
    return frame


def consolidate(force: bool = False, full_rebuild: bool = False) -> Path:
    output = LANDING / "impo_buenaventura_2012_2026.csv.gz"
    audit_path = TRUSTED / "audit_sources_2012_2026.csv"
    if output.exists() and audit_path.exists() and not force:
        print(f"Consolidado existente: {output.name}")
        return output

    missing = [name for name in FILES if not valid_zip(RAW_DANE / name)]
    if missing:
        raise FileNotFoundError(f"Faltan ZIP DANE: {missing}")

    historical = LANDING / "impo_buenaventura_2012_2024.csv.gz"
    historical_audit = TRUSTED / "audit_sources.csv"
    use_snapshot = historical.exists() and historical_audit.exists() and not full_rebuild
    archives_to_process = [name for name in FILES if name.startswith(("Impo_2025", "Impo_2026"))] if use_snapshot else list(FILES)

    temporary = output.with_suffix(".csv.gz.tmp")
    incremental = output.with_suffix(".incremental.gz.tmp")
    temporary.unlink(missing_ok=True)
    incremental.unlink(missing_ok=True)
    audit: list[dict] = []
    wrote_header = use_snapshot
    sink_path = incremental if use_snapshot else temporary
    with gzip.open(sink_path, "wt", encoding="utf-8", newline="") as sink:
        for archive_name in archives_to_process:
            with zipfile.ZipFile(RAW_DANE / archive_name) as archive:
                for source_name, stream in iter_csv_streams(archive):
                    source_month = month_from_name(source_name)
                    if archive_name == "Impo_2022_2.zip" and source_month == 6:
                        audit.append({"archive": archive_name, "source": source_name, "status": "omitido_solapamiento_junio_2022"})
                        continue
                    first_line = stream.readline()
                    separator = ";" if first_line.count(b";") > first_line.count(b",") else ","
                    stream.seek(0)
                    header = pd.read_csv(stream, nrows=0, encoding="latin-1", sep=separator)
                    stream.seek(0)
                    mapping = dict(zip(header.columns, normalize_columns(header.columns)))
                    selected = [c for c in header.columns if mapping[c] in KEEP]
                    if "ADUA" not in mapping.values() or "FECH" not in mapping.values():
                        audit.append({"archive": archive_name, "source": source_name, "status": "omitido_sin_adua_fecha"})
                        continue
                    total_rows = kept_rows = 0
                    for chunk in pd.read_csv(stream, usecols=selected, chunksize=150_000, encoding="latin-1", sep=separator, low_memory=False):
                        chunk = normalize_numeric(chunk.rename(columns=mapping))
                        total_rows += len(chunk)
                        part = chunk.loc[chunk["ADUA"].eq(35)].copy()
                        if part.empty:
                            continue
                        part["SOURCE_ARCHIVE"] = archive_name
                        part["SOURCE_FILE"] = source_name
                        part["SOURCE_MONTH"] = source_month
                        kept_rows += len(part)
                        part.to_csv(sink, index=False, header=not wrote_header)
                        wrote_header = True
                    audit.append({
                        "archive": archive_name, "source": source_name, "status": "procesado",
                        "rows_total": total_rows, "rows_buenaventura": kept_rows,
                    })
                    print(f"{archive_name} | {source_name}: {kept_rows:,}/{total_rows:,}")
    if use_snapshot:
        with temporary.open("wb") as destination, historical.open("rb") as old, incremental.open("rb") as new:
            shutil.copyfileobj(old, destination, length=8 * 1024 * 1024)
            shutil.copyfileobj(new, destination, length=8 * 1024 * 1024)
        incremental.unlink(missing_ok=True)
        previous_audit = pd.read_csv(historical_audit)
        audit_frame = pd.concat([previous_audit, pd.DataFrame(audit)], ignore_index=True, sort=False)
    else:
        audit_frame = pd.DataFrame(audit)
    temporary.replace(output)
    audit_frame.to_csv(audit_path, index=False)
    summary = {
        "rows_buenaventura": int(audit_frame["rows_buenaventura"].fillna(0).sum()),
        "source_files": int(audit_frame["source"].nunique()),
        "period_start": "2012-01", "period_end": "2026-05",
        "landing_file": output.name,
    }
    (TRUSTED / "extraction_summary_2012_2026.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _parse_dates(chunk: pd.DataFrame) -> pd.DataFrame:
    fech = pd.to_numeric(chunk["FECH"], errors="coerce").round().astype("Int64")
    year = 2000 + fech // 100
    month = fech % 100
    valid = year.between(2012, 2026) & month.between(1, 12)
    chunk["fecha"] = pd.to_datetime({"year": year.where(valid), "month": month.where(valid), "day": 1}, errors="coerce")
    chunk["capitulo"] = (pd.to_numeric(chunk["NABAN"], errors="coerce") // 100_000_000).astype("Int64")
    return chunk


def build_trusted(force: bool = False) -> Path:
    source = LANDING / "impo_buenaventura_2012_2026.csv.gz"
    output = TRUSTED / "serie_mensual_buenaventura.csv"
    if output.exists() and not force and pd.to_datetime(pd.read_csv(output, usecols=["fecha"])["fecha"]).max() >= pd.Timestamp("2026-05-01"):
        print(f"Serie actualizada existente: {output.name}")
        return output
    if not source.exists():
        raise FileNotFoundError(source)

    monthly_parts, country_parts, chapter_parts = [], [], []
    for chunk in pd.read_csv(source, chunksize=200_000, low_memory=False):
        chunk = _parse_dates(normalize_numeric(chunk))
        monthly_parts.append(chunk.groupby("fecha", observed=True).agg(
            cif_usd=("VACID", "sum"), fob_usd=("VAFODO", "sum"), peso_neto_kg=("PNK", "sum"),
            flete_usd=("FLETE", "sum"), seguros_usd=("SEGUROS", "sum"), registros=("FECH", "size")))
        country_parts.append(chunk.groupby(["fecha", "PAISGEN"], observed=True).agg(
            cif_usd=("VACID", "sum"), peso_neto_kg=("PNK", "sum"), registros=("FECH", "size")).reset_index())
        chapter_parts.append(chunk.groupby(["fecha", "capitulo"], observed=True).agg(
            cif_usd=("VACID", "sum"), peso_neto_kg=("PNK", "sum"), registros=("FECH", "size")).reset_index())

    monthly = pd.concat(monthly_parts).groupby(level=0).sum().sort_index().asfreq("MS")
    # Distintos mensuales se calculan desde los agregados ya reducidos.
    countries = pd.concat(country_parts).groupby(["fecha", "PAISGEN"], as_index=False).sum(numeric_only=True)
    chapters = pd.concat(chapter_parts).groupby(["fecha", "capitulo"], as_index=False).sum(numeric_only=True)
    monthly["paises_origen"] = countries.groupby("fecha")["PAISGEN"].nunique()
    monthly["capitulos"] = chapters.groupby("fecha")["capitulo"].nunique()
    monthly["precio_implicito_usd_kg"] = monthly["cif_usd"] / monthly["peso_neto_kg"].replace(0, np.nan)
    if monthly[["cif_usd", "peso_neto_kg"]].isna().any().any():
        raise ValueError("La serie mensual contiene periodos faltantes")
    monthly.to_csv(output, index_label="fecha")
    countries.to_csv(TRUSTED / "pais_mes_buenaventura.csv.gz", index=False, compression="gzip")
    chapters.to_csv(TRUSTED / "capitulo_mes_buenaventura.csv.gz", index=False, compression="gzip")
    monthly.reset_index().to_csv(SURFACE / "serie_mensual_buenaventura.csv", index=False)
    return output


if __name__ == "__main__":
    download_sources()
    consolidate(force=False)
    build_trusted(force=False)
