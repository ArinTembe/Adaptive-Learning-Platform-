"""
main.py — FastAPI backend for the Adaptive Learning Platform (MySQL 8.0)
Run: uvicorn main:app --reload
"""

import math
import os
from contextlib import contextmanager

import pymysql
import pymysql.cursors
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Adaptive Learning Platform")

# ── DB config ─────────────────────────────────────────────────
DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    database=os.getenv("DB_NAME", "adaptive_learning"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "Fantom@40"),   # ← your MySQL password
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)


@contextmanager
def get_db():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetchall(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def fetchone(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def execute(conn, sql, params=None):
    """Execute INSERT/UPDATE, return lastrowid."""
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.lastrowid


# ── Static files ──────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(os.path.join(static_dir, "dashboard.html"))


# ============================================================
# API ENDPOINTS
# ============================================================

# ── 1. List students ──────────────────────────────────────────
@app.get("/api/students")
def list_students():
    with get_db() as conn:
        rows = fetchall(conn, "SELECT student_id, name, email FROM students ORDER BY name")
    return list(rows)


# ── 2. GET /api/next-question/<student_id> ────────────────────
# Recommendation logic (replaces the PostgreSQL stored function):
#   Step 1 — find weakest topic (lowest mastery_score)
#   Step 2 — map mastery → target difficulty: ceil(mastery * 5 + 1), clamp 1-5
#   Step 3 — return least-attempted question at that difficulty in that topic
@app.get("/api/next-question/{student_id}")
def next_question(student_id: int):
    with get_db() as conn:
        student = fetchone(conn,
            "SELECT student_id, name FROM students WHERE student_id = %s",
            (student_id,))
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Step 1: weakest topic
        weak = fetchone(conn, """
            SELECT topic_id, mastery_score FROM mastery
            WHERE student_id = %s
            ORDER BY mastery_score ASC
            LIMIT 1
        """, (student_id,))

        if weak:
            topic_id = weak["topic_id"]
            mastery  = float(weak["mastery_score"])
        else:
            # No attempts yet → random topic
            rand_topic = fetchone(conn,
                "SELECT topic_id FROM topics ORDER BY RAND() LIMIT 1")
            topic_id = rand_topic["topic_id"]
            mastery  = 0.0

        # Step 2: mastery → difficulty
        target_diff = min(5, max(1, math.ceil(mastery * 5 + 1)))

        # Step 3: least-attempted question at target difficulty
        row = fetchone(conn, """
            SELECT
                q.question_id,
                q.topic_id,
                t.name       AS topic_name,
                q.difficulty,
                q.question_text
            FROM questions q
            JOIN topics t ON t.topic_id = q.topic_id
            WHERE q.topic_id  = %s
              AND q.difficulty = %s
            ORDER BY (
                SELECT COUNT(*) FROM attempts a
                WHERE  a.student_id  = %s
                  AND  a.question_id = q.question_id
            ) ASC, RAND()
            LIMIT 1
        """, (topic_id, target_diff, student_id))

    if not row:
        raise HTTPException(status_code=404, detail="No question available")
    return dict(row)


# ── 3. POST /api/attempt ──────────────────────────────────────
class AttemptIn(BaseModel):
    student_id:   int
    question_id:  int
    score:        float          # 0.0 – 1.0
    time_taken_s: int | None = None


@app.post("/api/attempt", status_code=201)
def submit_attempt(body: AttemptIn):
    if not 0.0 <= body.score <= 1.0:
        raise HTTPException(status_code=422, detail="score must be 0–1")

    with get_db() as conn:
        # Insert attempt — this fires trg_update_mastery automatically
        attempt_id = execute(conn, """
            INSERT INTO attempts(student_id, question_id, score, time_taken_s)
            VALUES (%s, %s, %s, %s)
        """, (body.student_id, body.question_id,
              round(body.score, 3), body.time_taken_s))

        # Fetch timestamp of the new attempt
        attempt = fetchone(conn,
            "SELECT attempted_at FROM attempts WHERE attempt_id = %s",
            (attempt_id,))

        # Fetch updated mastery for the topic just practiced
        mastery = fetchone(conn, """
            SELECT m.mastery_score, t.name AS topic_name
            FROM   mastery    m
            JOIN   questions  q ON q.topic_id   = m.topic_id
            JOIN   topics     t ON t.topic_id   = m.topic_id
            WHERE  m.student_id  = %s
              AND  q.question_id = %s
            LIMIT 1
        """, (body.student_id, body.question_id))

    return {
        "attempt_id":    attempt_id,
        "attempted_at":  str(attempt["attempted_at"]),
        "mastery_score": float(mastery["mastery_score"]) if mastery else None,
        "topic_name":    mastery["topic_name"] if mastery else None,
    }


# ── 4. GET /api/dashboard ─────────────────────────────────────
@app.get("/api/dashboard")
def dashboard():
    with get_db() as conn:
        stats   = fetchall(conn,
            "SELECT * FROM v_student_topic_stats ORDER BY student_name, topic_name")
        mastery = fetchall(conn,
            "SELECT * FROM v_mastery_overview ORDER BY student_name, mastery_score")
        recent  = fetchall(conn,
            "SELECT * FROM v_recent_attempts LIMIT 50")

    def fix(rows):
        result = []
        for r in rows:
            d = dict(r)
            for k, v in d.items():
                # Convert Decimal → float, datetime → str for JSON serialisation
                if hasattr(v, '__float__'):
                    d[k] = float(v)
                elif hasattr(v, 'isoformat'):
                    d[k] = str(v)
            result.append(d)
        return result

    return {
        "stats":   fix(stats),
        "mastery": fix(mastery),
        "recent":  fix(recent),
    }


# ── 5. GET /api/student/<id>/mastery ─────────────────────────
@app.get("/api/student/{student_id}/mastery")
def student_mastery(student_id: int):
    with get_db() as conn:
        student = fetchone(conn,
            "SELECT name FROM students WHERE student_id = %s", (student_id,))
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        rows = fetchall(conn, """
            SELECT t.name AS topic, m.mastery_score, m.last_updated
            FROM   mastery m
            JOIN   topics  t ON t.topic_id = m.topic_id
            WHERE  m.student_id = %s
            ORDER  BY m.mastery_score ASC
        """, (student_id,))

    return {
        "student": dict(student),
        "mastery": [
            {
                "topic":         r["topic"],
                "mastery_score": float(r["mastery_score"]),
                "last_updated":  str(r["last_updated"]),
            }
            for r in rows
        ],
    }
