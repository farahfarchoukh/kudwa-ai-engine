# kudwa-ai-engine

# Kudwa AI‑Powered Financial Engine

A tiny but production‑ready FastAPI service that:

* **Ingests** two disparate JSON financial data‑sets (QuickBooks‑style & Rootfi‑style)  
* **Normalises** them into a single `financial_records` table (SQLite)  
* **Answers** natural‑language questions via an LLM (OpenAI gpt‑3.5‑turbo) – the LLM writes ANSI‑SQL, the service runs it, then the LLM creates a concise narrative.  
* Provides a **conversation** endpoint that retains short‑term context.  
* (Optional) shows a **forecast** endpoint using Prophet.

## Quick start (local)

```bash
# 1 Clone & cd
git clone <repo‑url>
cd kudwa-ai-engine

# 2 Install dependencies
make install

# 3 Set your OpenAI key
cp .env.example .env
# edit .env and paste your key:
# OPENAI_API_KEY=sk-...

# 4 Load the sample data (once)
uvicorn app.main:app --reload  # in another terminal, or just run make run
# POST /datasets/qb   with body {"file_path": "./data/data_set_1.json"}
# POST /datasets/rootfi with body {"file_path": "./data/data_set_2.json"}

# 5 Run the API
make run
