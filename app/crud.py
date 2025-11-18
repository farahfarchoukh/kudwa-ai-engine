# app/crud.py
from sqlmodel import Session, select
from .models import FinancialRecord
from typing import List
from sqlalchemy.exc import IntegrityError

def get_session():
    from sqlmodel import create_engine, Session
    engine = create_engine("sqlite:///./kudwa.db")
    with Session(engine) as session:
        yield session

def add_records(session: Session, records: List[FinancialRecord]) -> int:
    added = 0
    for rec in records:
        try:
            session.add(rec)
            session.commit()
            added += 1
        except IntegrityError:
            session.rollback()          # duplicate – ignore
    return added

def list_records(session: Session, **filters):
    stmt = select(FinancialRecord)
    for col, val in filters.items():
        stmt = stmt.where(getattr(FinancialRecord, col) == val)
    return session.exec(stmt).all

def run_raw_sql(session: Session, sql: str):
    result = session.exec(sql)
    return result.fetchall()

