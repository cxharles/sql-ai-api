#####
import os
import sys
import openai
import uvicorn
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from databases import Database
from sqlalchemy import Table, Column, Integer, String, MetaData, create_engine
from passlib.context import CryptContext
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# --------------------
# Environment Setup
# --------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not OPENAI_API_KEY or not DATABASE_URL:
    print("❌ Missing OPENAI_API_KEY or DATABASE_URL in env.")
    sys.exit(1)

openai.api_key = OPENAI_API_KEY

# --------------------
# Database Setup
# --------------------
db = Database(DATABASE_URL)
metadata = MetaData()
engine = create_engine(DATABASE_URL)

# Users table
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), unique=True, nullable=False),
    Column("hashed_password", String(255), nullable=False),
)

# --------------------
# Auth Helpers
# --------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password):
    return pwd_context.hash(password)

# --------------------
# FastAPI App
# --------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(title="AI-to-SQL Agent", lifespan=lifespan)

# --------------------
# Pydantic Models
# --------------------
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    sql: str
    warning: Optional[str] = ""

class ExecuteResponse(BaseModel):
    sql: str
    rows: list

# --------------------
# Login Endpoint
# --------------------
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    query = users.select().where(users.c.username == form_data.username)
    user = await db.fetch_one(query)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": "Login successful", "username": user["username"]}

# --------------------
# SQL Generation Helpers
# --------------------
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
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip().replace("```sql", "").replace("```", "").strip()

# --------------------
# SQL Endpoints
# --------------------
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
# App Runner
# --------------------
if __name__ == "__main__":
    uvicorn.run("tutorial_full:app", host="127.0.0.1", port=8000, reload=True)