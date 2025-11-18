# app/ingestion.py
import json, logging
from pathlib import Path
from datetime import datetime
from typing import List
from .models import FinancialRecord

log = logging.getLogger(__name__)

def _parse_date(s: str) -> date:
    # QuickBooks uses "YYYY-MM-DD", Rootfi may use ISO with timezone
    return datetime.fromisoformat(s.split("T")[0]).date()

def _load_qb(path: Path, ds_id: str) -> List[FinancialRecord]:
    with open(path) as f:
        data = json.load(f)
    recs = []
    for row in data:
        # Example QB row: {"date":"2024-01-01","revenue":12345,"expenses":4567}
        start = _parse_date(row["date"])
        recs.append(
            FinancialRecord(
                dataset_id=ds_id,
                period_start=start,
                period_end=start,
                metric="revenue",
                amount=float(row.get("revenue", 0)),
                currency=row.get("currency", "USD"),
                raw_source_id=row.get("id"),
            )
        )
        recs.append(
            FinancialRecord(
                dataset_id=ds_id,
                period_start=start,
                period_end=start,
                metric="expense",
                amount=float(row.get("expenses", 0)),
                currency=row.get("currency", "USD"),
                raw_source_id=row.get("id"),
            )
        )
    return recs

def _load_rootfi(path: Path, ds_id: str) -> List[FinancialRecord]:
    with open(path) as f:
        data = json.load(f)
    recs = []
    for row in data:
        # Example Rootfi row: {"period":"Q1-2024","type":"profit","value":4321}
        start, end = rootfi_period_to_dates(row["period"])
        recs.append(
            FinancialRecord(
                dataset_id=ds_id,
                period_start=start,
                period_end=end,
                metric=row["type"].lower(),
                amount=float(row["value"]),
                currency=row.get("currency", "USD"),
                category=row.get("category"),
                sub_category=row.get("sub_category"),
                raw_source_id=row.get("uid"),
            )
        )
    return recs

def load_dataset(ds_id: str, path: Path) -> List[FinancialRecord]:
    """
    Dispatch based on filename prefix:
      - qb_*.json   → QuickBooks parser
      - rootfi_*.json → Rootfi parser
    """
    if "qb" in path.name.lower():
        return _load_qb(path, ds_id)
    if "rootfi" in path.lower():
        return _load_rootfi(path, ds_id)
    raise ValueError(f"Unsupported dataset format: {path.name}")

