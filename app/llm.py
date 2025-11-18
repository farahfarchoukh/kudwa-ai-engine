# app/llm.py
import json, logging, re
from typing import Optional, Tuple
from sqlmodel import Session
import openai

# --------------------------------------------------------------------------- #
# Prompt engineering – keep these at module level so they are easy to tweak.
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = """
You are a financial analyst assistant. The user will ask questions about a company's
financial data that lives in a relational table called `financial_records`. The
schema is:

id INTEGER PK,
dataset_id TEXT,
period_start DATE,
period_end DATE,
metric TEXT,
amount REAL,
currency TEXT,
category TEXT,
sub_category TEXT

Write a **single** ANSI‑SQL query that returns the exact rows needed to answer the
question. Do NOT use any column that does not exist. Do NOT add LIMIT unless the
question explicitly asks for it. Return ONLY the SQL statement, wrapped in
triple backticks. If the request cannot be satisfied with the data, answer with
a short explanation (still wrapped in triple backticks) like:
```sql
SELECT NULL;
and then explain in plain language below. """

USER_PROMPT_TEMPLATE = """User question: {question}

{extra_context} """

ANSWER_PROMPT = """Based on the result of the previous SQL query, write a concise (1‑2 sentences) natural‑language answer. Include the most important numbers and, if helpful, mention the rows that contributed to the answer.

If you need to perform additional calculations (e.g. percentages), you may do them in your answer – do NOT issue a second SQL query.

Answer: """

Anything that looks like sql … or just … will be captured.
SQL_REGEX = r"(?:sql)?\s*(.*?)\s*"

class NLQueryEngine: """Encapsulates the two‑step NL‑to‑SQL → answer flow."""

def __init__(self, api_key: str):
    openai.api_key = api_key
    self.logger = logging.getLogger("NLQueryEngine")

# --------------------------------------------------------------------- #
# Small wrapper so we can swap to async later if we want.
# --------------------------------------------------------------------- #
async def _call_llm(self, messages):
    """Call OpenAI ChatCompletion synchronously (fast for the demo)."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=messages,
        temperature=0.0,
    )
    return response["choices"][0]["message"]["content"]

async def answer(
    self,
    question: str,
    db_session: Session,
    extra_context: Optional[str] = None,
) -> Tuple[str, str]:
    """
    1️  Build the prompt and ask the model for a SQL statement.
    2️  Extract the SQL with a regex.
    3️  Run the SQL against the SQLite DB.
    4️  Feed the result set back to the model and ask for a short narrative.
    Returns: (sql_text, narrative_answer)
    """
    # --------------------------------------------------- 1️⃣ Build prompt
    user_msg = USER_PROMPT_TEMPLATE.format(
        question=question, extra_context=extra_context or ""
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]
    sql_response = await self._call_llm(messages)
    self.logger.debug("LLM raw SQL response: %s", sql_response)

    # --------------------------------------------------- 2️⃣ Extract SQL
    match = re.search(SQL_REGEX, sql_response, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("LLM did not return a SQL block.")
    sql = match.group(1).strip()
    self.logger.info("Generated SQL: %s", sql)

    # --------------------------------------------------- 3️⃣ Run SQL
    try:
        rows = db_session.exec(sql).fetchall()
        # Transform rows → list[dict] for the next prompt
        col_names = rows[0].keys() if rows else []
        data_for_prompt = json.dumps(
            [dict(zip(col_names, r)) for r in rows], indent=2
        )
    except Exception as exc:
        self.logger.exception("SQL execution failed")
        raise ValueError(f"Generated SQL raised an error: {exc}")

    # --------------------------------------------------- 4️⃣ Narrative
    answer_msg = (
        ANSWER_PROMPT
        + "\n\nResult set:\n```json\n"
        + data_for_prompt
        + "\n```"
    )
    answer = await self._call_llm(
        [
            {"role": "system", "content": "You are a concise financial analyst."},
            {"role": "user", "content": answer_msg},
        ]
    )
    answer = answer.strip()
    return sql, answer
