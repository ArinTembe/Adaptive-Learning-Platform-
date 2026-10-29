# Adaptive Learning Platform — Setup Guide

## Prerequisites
- PostgreSQL 14+ installed and running
- Python 3.11+
- pgAdmin (optional but recommended)

## Step 1 — Create the database

Open pgAdmin or psql and run:

```sql
CREATE DATABASE adaptive_learning;
```

## Step 2 — Run the schema

In pgAdmin, open `schema.sql` and execute it against `adaptive_learning`, **or** run:

```bash
psql -U postgres -d adaptive_learning -f schema.sql
```

## Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

## Step 4 — Edit DB credentials (if needed)

Open `seed.py` and `main.py`. Change the `DB` / `DB_CONFIG` dictionaries if your
PostgreSQL password or port differs from the defaults (`postgres` / `5432`).

Alternatively, set environment variables before running:

```powershell
$env:DB_PASSWORD = "yourpassword"
$env:DB_NAME     = "adaptive_learning"
```

## Step 5 — Seed the database

```bash
python seed.py
```

Expected output:
```
Inserted 5 topics
Inserted 75 questions
Inserted 15 students
Inserted ~550 attempts
✅ Seed complete!
```

## Step 6 — Start the API server

```bash
uvicorn main:app --reload
```

Then open: http://localhost:8000

- **Student view**: http://localhost:8000/
- **Teacher dashboard**: http://localhost:8000/dashboard
- **Auto API docs**: http://localhost:8000/docs

## Project Structure

```
dbms-project/
├── schema.sql          ← All DDL: tables, indexes, views, trigger, function
├── seed.py             ← Generates realistic test data with Faker
├── main.py             ← FastAPI backend (raw SQL via psycopg2)
├── requirements.txt
├── static/
│   ├── index.html      ← Student: pick student → get question → answer
│   └── dashboard.html  ← Teacher: mastery heatmap, stats, recent attempts
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/students` | List all students |
| GET | `/api/next-question/{student_id}` | Recommend next question (calls `fn_recommend_question`) |
| POST | `/api/attempt` | Submit answer, triggers mastery update |
| GET | `/api/dashboard` | All views data for teacher dashboard |
| GET | `/api/student/{id}/mastery` | Per-student mastery by topic |

## Key SQL Design Decisions

### Mastery Trigger (`trg_update_mastery`)
Fires `AFTER INSERT ON attempts`. Recalculates mastery using a **weighted average**
where the 5 most recent attempts count double — this makes mastery responsive to
recent improvement while not ignoring history. Scales by `avg_difficulty / 5` so
high-difficulty correct answers boost mastery more.

### Recommendation Function (`fn_recommend_question`)
1. Finds the student's **weakest topic** (lowest mastery score)
2. Maps mastery → difficulty: `target_diff = CEIL(mastery × 5 + 1)` (clamped 1–5)
3. Returns the **least-attempted** question at that difficulty — avoids repeating questions

### Views
- `v_student_topic_stats` — aggregated attempts/scores per student+topic (teacher)
- `v_mastery_overview` — mastery table joined with names (heatmap source)
- `v_recent_attempts` — ordered attempt log with student/topic names

### No ORM
All SQL is written explicitly in `main.py` using `psycopg2` — makes the queries
visible and auditable. `ON CONFLICT (student_id, topic_id) DO UPDATE` (UPSERT)
is used in the trigger to avoid separate INSERT/UPDATE logic.
