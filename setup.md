# AI-to-SQL Agent Setup Guide

This guide shows you how to get up and running with the **single-file** FastAPI tutorial (`tutorial_full.py`). In one file you’ll seed a dummy Postgres DB, define your models, wire up OpenAI, and launch the API.

---

## Prerequisites

- **Python 3.8+** (check with `python3 --version`)  
- **pip** (bundled with Python)  
- **PostgreSQL** database (local via Docker or cloud-hosted like Render, ElephantSQL, etc.)  
- **OpenAI API Key** (set up at https://platform.openai.com)

---

## 1. Clone & Enter Project

```bash
git clone <your-repo-url>
cd <your-repo-directory>
```

---

## 2. Create & Activate Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Your `.env`

Create a file named `.env` in the project root:

```dotenv
OPENAI_API_KEY=sk-…
DATABASE_URL=postgresql://user:password@host:port/database_name
```

> **Tip:**  
> - If you’re using Render or another cloud provider, copy the **full external** connection string.  
> - Add `.env` to your `.gitignore` to keep secrets safe.

---

## 5. Seed the Dummy Database

Use the provided `init_db.py` script to create the `customers` table and insert some sample data:

```bash
python init_db.py
```

You should see:

```
✅ Dummy 'customers' table created and seeded with sample data.
```

---

## 6. Run the API Server

Now launch the FastAPI app:

```bash
python tutorial_full.py
```

By default, Uvicorn will serve on **http://127.0.0.1:8000** with auto-reload.

---

## 7. Explore & Test

### a) Swagger UI

Open your browser to:

```
http://127.0.0.1:8000/docs
```

You can interactively try the `/generate-sql` or `/execute-sql` endpoints. Example:

```json
{
  "question": "How many customers with revenue over 1000?"
}
```

### b) cURL Example

From the terminal:

```bash
curl -X POST http://127.0.0.1:8000/generate-sql \
  -H "Content-Type: application/json" \
  -d '{"question":"How many customers with revenue over 1000?"}'
```

**Expected response**:

```json
{
  "sql": "SELECT COUNT(*) FROM customers WHERE revenue > 1000;"
}
```

---

## 8. Next Steps

- **Embed in your app**: call the endpoint from Python, JavaScript, or any HTTP client.  
- **Execute the SQL**: try `/execute-sql` to return live results from your DB.  
- **Add auth**: optionally protect the API with header tokens or JWT.  
- **Deploy**: containerize with Docker and host on Render, Heroku, etc.

You’re now ready to build AI-powered vertical agents with FastAPI!