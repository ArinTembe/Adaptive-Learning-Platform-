-- ============================================================
-- Personalized Adaptive Learning Platform
-- MySQL 8.0 Schema
-- ============================================================

-- Drop tables in reverse dependency order (safe re-run)
DROP TABLE IF EXISTS mastery;
DROP TABLE IF EXISTS attempts;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS topics;
DROP TABLE IF EXISTS students;

-- ============================================================
-- 1. students
-- ============================================================
CREATE TABLE students (
    student_id   INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    email        VARCHAR(150) NOT NULL UNIQUE,
    enrolled_at  DATE NOT NULL
);

-- ============================================================
-- 2. topics
-- ============================================================
CREATE TABLE topics (
    topic_id    INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

-- ============================================================
-- 3. questions
-- difficulty 1 (easiest) → 5 (hardest)
-- ============================================================
CREATE TABLE questions (
    question_id   INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    topic_id      INT NOT NULL,
    difficulty    TINYINT NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    question_text TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
);

-- ============================================================
-- 4. attempts
-- score: 0.000 – 1.000
-- ============================================================
CREATE TABLE attempts (
    attempt_id   INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    student_id   INT NOT NULL,
    question_id  INT NOT NULL,
    attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    score        DECIMAL(4,3) NOT NULL CHECK (score BETWEEN 0 AND 1),
    time_taken_s INT CHECK (time_taken_s > 0),
    FOREIGN KEY (student_id)  REFERENCES students(student_id)  ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);

CREATE INDEX idx_attempts_student  ON attempts(student_id);
CREATE INDEX idx_attempts_question ON attempts(question_id);

-- ============================================================
-- 5. mastery  (auto-updated by trigger after each attempt)
-- mastery_score: 0.0000 – 1.0000
-- ============================================================
CREATE TABLE mastery (
    student_id    INT NOT NULL,
    topic_id      INT NOT NULL,
    mastery_score DECIMAL(5,4) NOT NULL DEFAULT 0 CHECK (mastery_score BETWEEN 0 AND 1),
    last_updated  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, topic_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id)   REFERENCES topics(topic_id)    ON DELETE CASCADE
);

-- ============================================================
-- VIEWS
-- ============================================================

-- V1: per-student, per-topic aggregated stats (teacher dashboard)
CREATE OR REPLACE VIEW v_student_topic_stats AS
SELECT
    s.student_id,
    s.name                                        AS student_name,
    t.topic_id,
    t.name                                        AS topic_name,
    COUNT(a.attempt_id)                           AS total_attempts,
    ROUND(AVG(a.score), 4)                        AS avg_score,
    ROUND(AVG(q.difficulty), 2)                   AS avg_difficulty_attempted,
    MAX(a.attempted_at)                           AS last_attempt
FROM students s
JOIN attempts  a ON a.student_id  = s.student_id
JOIN questions q ON q.question_id = a.question_id
JOIN topics    t ON t.topic_id    = q.topic_id
GROUP BY s.student_id, s.name, t.topic_id, t.name;

-- V2: mastery overview joined with names (heatmap source)
CREATE OR REPLACE VIEW v_mastery_overview AS
SELECT
    s.student_id,
    s.name         AS student_name,
    t.topic_id,
    t.name         AS topic_name,
    m.mastery_score,
    m.last_updated
FROM mastery  m
JOIN students s ON s.student_id = m.student_id
JOIN topics   t ON t.topic_id   = m.topic_id
ORDER BY s.student_id, m.mastery_score;

-- V3: recent attempt log with names
CREATE OR REPLACE VIEW v_recent_attempts AS
SELECT
    a.attempt_id,
    s.name          AS student_name,
    t.name          AS topic_name,
    q.difficulty,
    a.score,
    a.attempted_at
FROM attempts  a
JOIN students  s ON s.student_id  = a.student_id
JOIN questions q ON q.question_id = a.question_id
JOIN topics    t ON t.topic_id    = q.topic_id
ORDER BY a.attempted_at DESC;

-- ============================================================
-- TRIGGER: auto-update mastery after each attempt insert
--
-- Formula: weighted average where the 5 most recent attempts
--          count 2x (recency bias), older attempts count 1x.
--          Result is then scaled by avg_difficulty / 5 so that
--          answering harder questions correctly boosts mastery more.
--
-- Uses MySQL 8.0 window function ROW_NUMBER() OVER (ORDER BY ...)
-- inside a derived table to assign recency weights.
-- ON DUPLICATE KEY UPDATE handles the upsert cleanly.
-- ============================================================

DELIMITER $$

CREATE TRIGGER trg_update_mastery
AFTER INSERT ON attempts
FOR EACH ROW
BEGIN
    DECLARE v_topic_id     INT;
    DECLARE v_weighted_sum DECIMAL(10,6) DEFAULT 0;
    DECLARE v_total_weight DECIMAL(10,6) DEFAULT 0;
    DECLARE v_avg_diff     DECIMAL(5,2)  DEFAULT 1;
    DECLARE v_new_score    DECIMAL(5,4)  DEFAULT 0;

    -- Step 1: find which topic this question belongs to
    SELECT topic_id INTO v_topic_id
    FROM questions
    WHERE question_id = NEW.question_id;

    -- Step 2: compute weighted sums using ROW_NUMBER() to rank by recency
    --         Recent 5 attempts get weight=2, older get weight=1
    SELECT
        SUM(w.weight * w.score),
        SUM(w.weight),
        AVG(w.difficulty)
    INTO v_weighted_sum, v_total_weight, v_avg_diff
    FROM (
        SELECT
            a.score,
            q.difficulty,
            CASE WHEN ROW_NUMBER() OVER (ORDER BY a.attempted_at DESC) <= 5
                 THEN 2 ELSE 1
            END AS weight
        FROM attempts  a
        JOIN questions q ON q.question_id = a.question_id
        WHERE a.student_id = NEW.student_id
          AND q.topic_id   = v_topic_id
    ) w;

    -- Step 3: compute final mastery score (clamped to [0,1])
    IF v_total_weight > 0 THEN
        SET v_new_score = LEAST(1.0,
            GREATEST(0, (v_weighted_sum / v_total_weight) * (v_avg_diff / 5.0))
        );
    END IF;

    -- Step 4: upsert into mastery (ON DUPLICATE KEY UPDATE = MySQL's UPSERT)
    INSERT INTO mastery(student_id, topic_id, mastery_score, last_updated)
    VALUES (NEW.student_id, v_topic_id, v_new_score, NOW())
    ON DUPLICATE KEY UPDATE
        mastery_score = v_new_score,
        last_updated  = NOW();

END$$

DELIMITER ;
