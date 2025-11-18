# app/models.py
from sqlmodel import SQLModel, Field
from datetime import date
from typing import Optional

class FinancialRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dataset_id: str = Field(index=True, description="e.g. qb or rootfi")
    period_start: date
    period_end: date
    metric: str = Field(index=True)            # revenue, expense, profit, cash_flow, …
    amount: float
    currency: str = Field(default="USD")
    category: Optional[str] = Field(default=None)   # expense category, revenue segment, …
    sub_category: Optional[str] = Field(default=None)

    # source‑specific fields kept for debugging
    raw_source_id: Optional[str] = None

