"""
seed.py — Generate realistic seed data for the Adaptive Learning Platform
Run: python seed.py
Requires: PyMySQL, faker  (pip install PyMySQL faker)
"""

import random
import pymysql
from faker import Faker
from datetime import datetime, timedelta

# ── DB connection ─────────────────────────────────────────────
DB = dict(
    host="localhost",
    port=3306,
    database="adaptive_learning",
    user="root",
    password="Fantom@40",       # ← change to your MySQL root password
    charset="utf8mb4",
)

fake = Faker()
random.seed(42)

# ── Domain data ───────────────────────────────────────────────
TOPICS = [
    ("Algebra",     "Linear equations, quadratics, polynomials"),
    ("Geometry",    "Shapes, area, volume, coordinate geometry"),
    ("Probability", "Basic probability, Bayes theorem, distributions"),
    ("Statistics",  "Mean, median, variance, hypothesis testing"),
    ("Calculus",    "Limits, differentiation, integration basics"),
]

QUESTION_TEMPLATES = {
    "Algebra": [
        ("Solve for x: 2x + 3 = 7",                        "x = 2",             1),
        ("Expand: (x+2)(x-3)",                              "x^2 - x - 6",       2),
        ("Find roots of x^2 - 5x + 6 = 0",                 "x=2, x=3",          2),
        ("Solve: 3x^2 - 12 = 0",                            "x = +/-2",          3),
        ("If f(x)=2x^2-3x+1, find f(2)",                   "3",                 3),
        ("Factor: x^3 - 8",                                 "(x-2)(x^2+2x+4)",   4),
        ("Solve: x^2 + 4x + 5 = 0 (complex roots)",        "x = -2 +/- i",      4),
        ("Find the inverse of f(x) = 3x - 6",              "f^-1(x) = (x+6)/3", 3),
        ("Solve system: 2x + y = 5, x - y = 1",            "x=2, y=1",          2),
        ("Simplify: (x^2 - 9) / (x + 3)",                  "x - 3",             3),
        ("Binomial expansion of (a+b)^4, find 3rd term",   "6a^2 b^2",          5),
        ("Solve: |2x - 3| = 7",                             "x=5 or x=-2",       4),
        ("Find sum of roots: 4x^2 - 8x + 3 = 0",          "2",                 3),
        ("Solve for x: log base 2 of x = 5",               "x = 32",            4),
        ("Solve: e^(2x) = 7",                               "x = ln(7)/2",       5),
    ],
    "Geometry": [
        ("Area of circle with radius 5",                    "78.54",             1),
        ("Perimeter of rectangle 4x7",                      "22",                1),
        ("Pythagorean theorem: a=3, b=4, find c",          "5",                 2),
        ("Volume of sphere radius 3",                       "113.1",             2),
        ("Find diagonal of square with side 6",            "6 root 2",          2),
        ("Area of triangle with base 10, height 4",        "20",                1),
        ("Interior angle sum of heptagon",                  "900 degrees",       3),
        ("Distance between (1,2) and (4,6)",               "5",                 2),
        ("Equation of line through (0,3) slope 2",         "y = 2x + 3",        2),
        ("Find circumference: diameter=14",                 "43.98",             1),
        ("Area of trapezoid: b1=8, b2=12, h=5",           "50",                3),
        ("Midpoint of segment (2,4) to (8,10)",            "(5,7)",             2),
        ("Angle in semicircle subtended by diameter",      "90 degrees",        3),
        ("Surface area of cylinder r=4, h=10",             "351.86",            4),
        ("Volume of cone r=3, h=9",                        "84.82",             4),
    ],
    "Probability": [
        ("P(head on fair coin)",                            "0.5",               1),
        ("P(rolling a 6 on fair die)",                     "1/6",               1),
        ("P(red card from standard deck)",                  "0.5",               1),
        ("P(A union B): P(A)=0.3, P(B)=0.4, P(A^B)=0.1", "0.6",               2),
        ("P(two heads, two fair coins)",                    "0.25",              2),
        ("Expected value: {1:0.2, 2:0.5, 3:0.3}",         "2.1",               3),
        ("P(at least one 6, two dice)",                    "11/36",             3),
        ("Bayes: P(B|A)=0.8, P(A)=0.3, P(B)=0.4",        "P(A|B)=0.6",        4),
        ("Binomial P(X=3), n=5, p=0.4",                   "0.2304",            4),
        ("Variance of X: E[X]=3, E[X^2]=13",              "4",                 3),
        ("P(both aces, no replacement, 52-card deck)",     "1/221",             4),
        ("Normal dist: P(Z < 1.96)",                       "0.975",             3),
        ("Geometric dist: P(first success on 3rd try), p=0.3", "0.147",        4),
        ("Poisson P(X=2), lambda=3",                       "0.224",             4),
        ("Conditional P(A|B) if A,B independent, P(A)=0.5","0.5",              2),
    ],
    "Statistics": [
        ("Mean of {4,7,2,9,3}",                            "5",                 1),
        ("Median of {1,3,5,7,9}",                          "5",                 1),
        ("Mode of {2,3,3,4,5,3}",                          "3",                 1),
        ("Range of {12,4,7,19,3}",                         "16",                1),
        ("Variance of {2,4,4,4,5,5,7,9}",                 "4",                 3),
        ("Standard deviation of {2,4,4,4,5,5,7,9}",       "2",                 3),
        ("z-score: x=75, mean=70, sd=5",                   "1",                 2),
        ("IQR of {1,2,5,6,7,9,12,15,18,19,27}",           "13",                3),
        ("Type I error definition",                         "Rejecting a true null hypothesis", 2),
        ("p-value < 0.05 conclusion",                       "Reject null hypothesis",           2),
        ("Pearson r interpretation: r = -0.9",             "Strong negative correlation",       2),
        ("95% CI formula",                                  "x-bar +/- 1.96*(sigma/sqrt(n))",   3),
        ("Chi-square test use case",                        "Test independence of categorical variables", 3),
        ("Degrees of freedom for t-test, n=20",            "19",                2),
        ("Skewness: mean > median > mode indicates?",      "Right (positive) skew",             2),
    ],
    "Calculus": [
        ("Limit: lim x->2 of (x^2-4)/(x-2)",             "4",                 2),
        ("Derivative of x^3",                              "3x^2",              1),
        ("Derivative of sin(x)",                           "cos(x)",            1),
        ("Integral of 2x dx",                              "x^2 + C",           1),
        ("Derivative of e^x",                              "e^x",               1),
        ("Chain rule: d/dx[sin(x^2)]",                     "2x cos(x^2)",       3),
        ("Product rule: d/dx[x * sin(x)]",                 "sin(x) + x cos(x)", 3),
        ("Integral of sin(x) dx",                          "-cos(x) + C",       2),
        ("Definite integral from 0 to 1 of x^2 dx",       "1/3",               2),
        ("Derivative of ln(x)",                            "1/x",               2),
        ("Critical point of f(x) = x^2 - 4x + 3",        "x = 2",             3),
        ("Integral of e^(2x) dx",                          "(1/2)e^(2x) + C",   3),
        ("Second derivative test: f''(x) > 0 at critical pt", "Local minimum", 3),
        ("L'Hopital's rule: lim x->0 sin(x)/x",           "1",                 4),
        ("Definite integral from 0 to pi of sin(x) dx",   "2",                 4),
    ],
}

NUM_STUDENTS = 15


def make_weakness_profiles(n_students, n_topics):
    """Each student is weak in 1-2 randomly chosen topics."""
    profiles = []
    for _ in range(n_students):
        weak = random.sample(range(n_topics), k=random.randint(1, 2))
        profiles.append(weak)
    return profiles


def connect():
    return pymysql.connect(**DB, cursorclass=pymysql.cursors.DictCursor)


def seed():
    conn = connect()
    cur  = conn.cursor()

    # ── Topics ────────────────────────────────────────────────
    topic_ids = []
    for name, desc in TOPICS:
        cur.execute(
            "INSERT INTO topics(name, description) VALUES (%s, %s)",
            (name, desc)
        )
        topic_ids.append(cur.lastrowid)
    print(f"Inserted {len(topic_ids)} topics")

    # ── Questions ─────────────────────────────────────────────
    question_ids_by_topic = {}
    for (topic_name, _), topic_id in zip(TOPICS, topic_ids):
        question_ids_by_topic[topic_id] = []
        for text, answer, diff in QUESTION_TEMPLATES[topic_name]:
            cur.execute(
                """INSERT INTO questions(topic_id, difficulty, question_text, correct_answer)
                   VALUES (%s, %s, %s, %s)""",
                (topic_id, diff, text, answer)
            )
            question_ids_by_topic[topic_id].append((cur.lastrowid, diff))
    total_q = sum(len(v) for v in question_ids_by_topic.values())
    print(f"Inserted {total_q} questions")

    # ── Students ──────────────────────────────────────────────
    student_ids = []
    for _ in range(NUM_STUDENTS):
        name    = fake.name()
        email   = fake.unique.email()
        enroll  = fake.date_between(start_date="-180d", end_date="-30d")
        cur.execute(
            "INSERT INTO students(name, email, enrolled_at) VALUES (%s, %s, %s)",
            (name, email, enroll)
        )
        student_ids.append(cur.lastrowid)
    print(f"Inserted {len(student_ids)} students")

    # ── Attempts with realistic weakness patterns ─────────────
    weakness = make_weakness_profiles(NUM_STUDENTS, len(topic_ids))
    base_time = datetime.now() - timedelta(days=90)
    attempts_count = 0

    for s_idx, sid in enumerate(student_ids):
        weak_topics = [topic_ids[i] for i in weakness[s_idx]]
        n_attempts  = random.randint(30, 45)

        for _ in range(n_attempts):
            topic_id  = random.choice(topic_ids)
            questions = question_ids_by_topic[topic_id]
            if not questions:
                continue

            # Weak topics → harder questions attempted, lower scores
            if topic_id in weak_topics:
                qs_pool = [(qid, d) for qid, d in questions if d >= 3] or questions
                score   = round(random.uniform(0.0, 0.45), 3)
            else:
                qs_pool = [(qid, d) for qid, d in questions if d <= 3] or questions
                score   = round(random.uniform(0.55, 1.0), 3)

            qid, _ = random.choice(qs_pool)
            days_offset = random.randint(0, 89)
            secs_offset = random.randint(0, 86400)
            attempted_at = base_time + timedelta(days=days_offset, seconds=secs_offset)
            time_taken   = random.randint(30, 300)

            cur.execute(
                """INSERT INTO attempts(student_id, question_id, attempted_at, score, time_taken_s)
                   VALUES (%s, %s, %s, %s, %s)""",
                (sid, qid, attempted_at, score, time_taken)
            )
            attempts_count += 1

    conn.commit()
    print(f"Inserted {attempts_count} attempts")
    cur.close()
    conn.close()
    print("Seed complete!")


if __name__ == "__main__":
    seed()
