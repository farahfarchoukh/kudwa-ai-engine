import json, logging
from pathlib import Path
from datetime import datetime, date
from typing import List

from .models import FinancialRecord

log = logging.getLogger(__name__)

def _parse_date(s: str) -> date:
    """Accept “2024‑01‑01” or “2024‑01‑01T00:00:00Z”."""
    return datetime.fromisoformat(s.split("T")[0]).date()


def rootfi_period_to_dates(period: str) -> tuple[date, date]:
    """
    Very small helper that understands a handful of Rootfi period strings.
    For the take‑home data we only see:
      - “Q1‑2024”, “Q2‑2024”, …
      - “2024‑02‑01/2024‑02‑28”

    It returns (start, end) dates.
    """
    if period.startswith("Q"):
        q, yr = period[1], period.split("-")[1]
        q = int(q)
        months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}[q]
        start = date(int(yr), months[0], 1)
        # end is the last day of the last month in the quarter
        end_month = months[1]
        # simple last‑day‑of‑month calculation
        if end_month in (1, 3, 5, 7, 8, 10, 12):
            day = 31
        elif end_month == 2:
            day = 29 if (int(yr) % 4 == 0 and (int(yr) % 100 != 0 or int(yr) % 400 == 0)) else 28
        else:
            day = 30
        end = date(int(yr), end_month, day)
        return start, end
    # fallback – split on slash
    if "/" in period:
        s, e = period.split("/")
        return _parse_date(s), _parse_date(e)
    # unknown format – just treat as a single day
    d = _parse_date(period)
    return d, d


def _load_qb(path: Path, ds_id: str) -> List[FinancialRecord]:
    """QuickBooks‑style – each row has a single date."""
    with open(path) as f:
        data = json.load(f)

    recs = []
    for row in data:
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
    """Rootfi‑style – period can be a quarter or a date range."""
    with open(path) as f:
        data = json.load(f)

    recs = []
    for row in data:
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
    Dispatch based on filename – the test data uses “qb_…” and “rootfi_…”.
    """
    if "qb" in path.name.lower():
        return _load_qb(path, ds_id)
    if "rootfi" in path.name.lower():
        return _load_rootfi(path, ds_id)

    raise ValueError(f"Unsupported dataset format: {path.name}")


