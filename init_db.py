# Updated file
import os
import asyncio
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import (
    Table, Column, Integer, String, Numeric, Date, MetaData,
    create_engine
)
from databases import Database
from sqlalchemy import Table, Column, Integer, String


# ✅ Define shared metadata object first
metadata = MetaData()

# ✅ Now use metadata for both tables
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), unique=True, nullable=False),
    Column("hashed_password", String(255), nullable=False),
)

customers = Table(
    "customers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("revenue", Numeric(10, 2), nullable=False),
    Column("signup_date", Date, nullable=False),
)


# Load environment variables from .env file
load_dotenv()

# Load the DATABASE_URL environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set the DATABASE_URL environment variable before running this script.")

# --- Define metadata and the 'customers' table ---
metadata = MetaData()

customers = Table(
    "customers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("revenue", Numeric(10, 2), nullable=False),
    Column("signup_date", Date, nullable=False),
)

# --- Create SQLAlchemy engine and Databases client ---
engine = create_engine(DATABASE_URL)
database = Database(DATABASE_URL)

async def init_and_seed():
    # 1. Create the table
    metadata.create_all(engine)

    # 2. Connect and insert sample rows
    await database.connect()
    await database.execute_many(
        query=customers.insert(),
        values=[
            {"id": 1, "name": "Alice",   "revenue": 1200.00, "signup_date": date(2023, 5, 1)},
            {"id": 2, "name": "Bob",     "revenue":  950.50, "signup_date": date(2023, 6,15)},
            {"id": 3, "name": "Charlie", "revenue": 1100.25, "signup_date": date(2023, 7,22)},
            {"id": 4, "name": "Diana",   "revenue":  780.75, "signup_date": date(2023, 3,13)},
            {"id": 5, "name": "Eve",     "revenue": 1300.00, "signup_date": date(2023, 4, 9)},
        ]
    )
    await database.disconnect()
    print("✅ Dummy 'customers' table created and seeded with sample data.")

if __name__ == "__main__":
    asyncio.run(init_and_seed() )
