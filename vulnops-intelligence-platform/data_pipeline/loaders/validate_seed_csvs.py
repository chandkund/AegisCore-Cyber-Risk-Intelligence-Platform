"""Validate `database/seeds/*.csv` rows against Pydantic contracts (no DB)."""

from __future__ import annotations

from pathlib import Path

from data_pipeline.ingestion.csv_io import read_csv_rows
from data_pipeline.validation.models import AssetCsvRow, CveCsvRow, FindingCsvRow

REPO = Path(__file__).resolve().parents[2]
SEEDS = REPO / "database" / "seeds"


def validate_all() -> list[str]:
    errors: list[str] = []
    try:
        read_csv_rows(SEEDS / "cve_records.csv", CveCsvRow)
    except Exception as e:  # noqa: BLE001 — aggregate validation messages
        errors.append(f"cve_records.csv: {e}")
    try:
        read_csv_rows(SEEDS / "assets.csv", AssetCsvRow)
    except Exception as e:
        errors.append(f"assets.csv: {e}")
    try:
        read_csv_rows(SEEDS / "vulnerability_findings.csv", FindingCsvRow)
    except Exception as e:
        errors.append(f"vulnerability_findings.csv: {e}")
    return errors


def main() -> None:
    errs = validate_all()
    if errs:
        print("Validation failed:")
        for e in errs:
            print(" -", e)
        raise SystemExit(1)
    print("OK: cve_records.csv, assets.csv, vulnerability_findings.csv")


if __name__ == "__main__":
    main()
