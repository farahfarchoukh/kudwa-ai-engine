# app/db_init.py
from sqlmodel import SQLModel, create_engine
from .models import FinancialRecord

engine = create_engine("sqlite:///./kudwa.db", echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
