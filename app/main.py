# app/main.py
import os
from fastapi import FastAPI, HTTPException, Depends, Body, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from sqlmodel import SQLModel
from .models import FinancialRecord
from .crud import get_session, list_records, run_raw_sql, add_records
from .ingestion import load_dataset
from .llm import NLQueryEngine
from .utils import logger

app = FastAPI(
    title="Kudwa Financial AI Engine",
    description="Unified financial data store with natural‑language query support.",
    version="0.1.0",
)

# ------------------------------------------------------------------ #
# DB dependency
# ------------------------------------------------------------------ #
@app.on_event("startup")
def on_startup():
    from .db_init import create_db_and_tables
    create_db_and_tables()
    logger.info("🗄️  Database tables created / verified.")

# ------------------------------------------------------------------ #
# Health / ping
# ------------------------------------------------------------------ #
@app.get("/health")
def health():
    return {"status": "ok"}

# ------------------------------------------------------------------ #
# Dataset upload (simple endpoint – you can also pre‑load via script)
# ------------------------------------------------------------------ #
@app.post("/datasets/{ds_id}")
def upload_dataset(
    ds_id: str,
    file_path: str = Body(..., embed=True, description="Absolute path on server, e.g. /data/data_set_1.json"),
    session: Session = Depends(get_session),
):
    """
    Load a JSON financial data‑set, normalise, and persist.
    """
    path = os.path.abspath(file_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        records = load_dataset(ds_id, Path(path))
        added = add_records(session, records)
        return {"added": added, "total": len(records)}
    except Exception as exc:
        logger.exception("Dataset load failed")
        raise HTTPException(status_code=500, detail=str(exc))

# ------------------------------------------------------------------ #
# Raw CRUD on the unified fact table (filterable)
# ------------------------------------------------------------------ #
@app.get("/financials")
def get_financials(
    metric: str | None = None,
    start: str | None = None,
    end: str | None = None,
    category: str | None = None,
    session: Session = Depends(get_session),
):
    """
    Returns the canonical financial table; all params are optional.
    """
    stmt = select(FinancialRecord)
    if metric:
        stmt = stmt.where(FinancialRecord.metric == metric)
    if category:
        stmt = stmt.where(FinancialRecord.category == category)
    if start:
        stmt = stmt.where(FinancialRecord.period_start >= start)
    if end:
        stmt = stmt.where(FinancialRecord.period_end <= end)
    results = session.exec(stmt).all()
    return results

# ------------------------------------------------------------------ #
# Natural‑Language Query – single‑turn
# ------------------------------------------------------------------ #
@app.post("/nl-query")
async def nl_query(
    question: str = Body(..., embed=True),
    session: Session = Depends(get_session),
    request: Request = None,
):
    """
    Turn a free‑form question into a SQL query, run it, and generate a concise answer.
    """
    engine = NLQueryEngine(os.getenv("OPENAI_API_KEY"))
    sql, narrative = await engine.answer(question, session)
    return {"question": question, "sql": sql, "answer": narrative}

# ------------------------------------------------------------------ #
# Conversational NL‑Query – context maintained in‑memory (simple)
# ------------------------------------------------------------------ #
conversation_history = []

@app.post("/nl-converse")
async def nl_converse(
    question: str = Body(..., embed=True),
    session: Session = Depends(get_session),
):
    """
    Adds the user question to the short‑term memory and returns an answer.
    Conversation state lives only for the process lifetime.
    """
    # Build a running prompt
    past = "\n".join([f"User: {q}\nAI: {a}" for q, a in conversation_history[-5:]])
    engine = NLQueryEngine(os.getenv("OPENAI_API_KEY"))
    sql, answer = await engine.answer(question, session, extra_context=past)

    # Store for next turn
    conversation_history.append((question, answer))
    return {"question": question, "sql": sql, "answer": answer}

# ------------------------------------------------------------------ #
# Optional analytics – forecast demo (uses Prophet, can be swapped)
# ------------------------------------------------------------------ #
@app.get("/analytics/forecast")
def forecast(
    metric: str,
    periods: int = 12,
    session: Session = Depends(get_session),
):
    """
    Very light‑weight Prophet forecast.
    """
    from prophet import Prophet
    import pandas as pd

    stmt = select(FinancialRecord).where(FinancialRecord.metric == metric)
    rows = session.exec(stmt).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No data for metric")

    df = pd.DataFrame(
        {
            "ds": [r.period_start for r in rows],
            "y": [r.amount for r in rows],
        }
    )
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m.fit(df)
    future = m.make_future_dataframe(periods=periods, freq="M")
    forecast = m.predict(future)
    result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods).to_dict(orient="records")
    return {"metric": metric, "forecast": result}

