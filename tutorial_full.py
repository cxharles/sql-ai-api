# tutorial_full.py
# -------------------
# Beginner Tutorial: FastAPI AI-to-SQL Agent (Vertical AI)
# One-file demonstration: AI prompt handling, FastAPI setup, OpenAI integration.
# Style aligned with DataCamp's FastAPI course structure.

import os
import sys
from dotenv import load_dotenv
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from databases import Database
from sqlalchemy import create_engine, MetaData
from openai import OpenAI
import uvicorn

# --------------------
# Section 1: Setup & Config
# --------------------
# Load environment variables and connect to OpenAI and Postgres

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
if not OPENAI_API_KEY or not DATABASE_URL:
    print("Missing OPENAI_API_KEY or DATABASE_URL in env.")
    sys.exit(1)

openai_client = OpenAI()
db = Database(DATABASE_URL)
metadata = MetaData()
engine = create_engine(DATABASE_URL)

# --------------------
# Section 2: Data Models
# --------------------
# These Pydantic models define what the API expects and returns

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    sql: str
    warning: Optional[str] = ""

class ExecuteResponse(BaseModel):
    sql: str
    rows: list

# --------------------
# Section 3: FastAPI App Lifecycle
# --------------------
# FastAPI lifecycle events for connecting/disconnecting from the database

app = FastAPI(title="AI-to-SQL Agent")

@app.on_event("startup")
async def on_start():
    await db.connect()

@app.on_event("shutdown")
async def on_stop():
    await db.disconnect()

# --------------------
# Section 4: Helpers
# --------------------
# Utility functions for schema detection and prompt generation

async def detect_table(question: str) -> str:
    rows = await db.fetch_all("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
    """)
    candidates = [r["table_name"] for r in rows if r["table_name"].lower() in question.lower()]
    if len(candidates) == 1:
        return candidates[0]
    raise HTTPException(400, detail=f"Could not detect table. Matches: {candidates}")

async def get_schema_for_question(question: str) -> dict:
    table = await detect_table(question)
    cols = await db.fetch_all("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = :table ORDER BY ordinal_position
    """, values={"table": table})
    return {"table_name": table, "columns": [r["column_name"] for r in cols]}

def generate_sql(question: str, schema: dict) -> str:
    prompt = f"""
    You are a helpful assistant that generates SQL queries.
    Given the table `{schema['table_name']}` and its columns:
    {', '.join(schema['columns'])}
    and the user's question:
    {question}
    Produce ONLY the SQL query, no explanation.
    """
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip().replace("```sql", "").replace("```", "").strip()

# --------------------
# Section 5: API Endpoints
# --------------------
# These endpoints generate and optionally execute SQL from natural language

@app.post("/generate-sql", response_model=QueryResponse)
async def generate_sql_route(payload: QueryRequest):
    try:
        schema = await get_schema_for_question(payload.question)
        sql = generate_sql(payload.question, schema)
        return QueryResponse(sql=sql)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute-sql", response_model=ExecuteResponse)
async def execute_sql_route(payload: QueryRequest):
    try:
        schema = await get_schema_for_question(payload.question)
        sql = generate_sql(payload.question, schema)
        if not sql.strip().lower().startswith("select"):
            raise HTTPException(status_code=400, detail="Only SELECT statements are allowed")
        rows = await db.fetch_all(query=sql)
        return ExecuteResponse(sql=sql, rows=[dict(r) for r in rows])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# --------------------
# Section 6: Run the App
# --------------------
# Use uvicorn to launch the server. Use --reload for dev mode.

if __name__ == "__main__":
    uvicorn.run("tutorial_full:app", host="127.0.0.1", port=8000, reload=True)
