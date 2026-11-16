"""SQLite projections. Raw account responses and credentials are never persisted."""
import json
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sessions (
 source TEXT NOT NULL, external_id TEXT NOT NULL, day TEXT NOT NULL,
 title TEXT NOT NULL, PRIMARY KEY(source,external_id));
CREATE TABLE IF NOT EXISTS sets (
 source TEXT NOT NULL, session_id TEXT NOT NULL, movement_pos INTEGER NOT NULL,
 position INTEGER NOT NULL, exercise TEXT NOT NULL, equipment TEXT,
 kind TEXT, done INTEGER, weight_kg REAL, reps REAL, rpe REAL, duration_seconds REAL,
 PRIMARY KEY(source,session_id,movement_pos,position),
 FOREIGN KEY(source,session_id) REFERENCES sessions(source,external_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS body (
 source TEXT NOT NULL, day TEXT NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL,
 unit TEXT NOT NULL, measured_at TEXT, PRIMARY KEY(source,day,metric));
CREATE TABLE IF NOT EXISTS forecasts (
 id TEXT PRIMARY KEY, source TEXT NOT NULL, created_at TEXT NOT NULL,
 target_day TEXT NOT NULL, exercise TEXT NOT NULL, equipment TEXT NOT NULL,
 weight_kg REAL NOT NULL, cutoff TEXT NOT NULL, prediction REAL NOT NULL,
 model TEXT NOT NULL, suggestion TEXT NOT NULL, actual REAL, actual_day TEXT,
 adopted INTEGER, feedback_note TEXT);
CREATE INDEX IF NOT EXISTS sessions_day ON sessions(day);
CREATE INDEX IF NOT EXISTS body_day ON body(day);
"""

def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    if "duration_seconds" not in {r[1] for r in db.execute("PRAGMA table_info(sets)")}:
        db.execute("ALTER TABLE sets ADD COLUMN duration_seconds REAL")
        db.commit()
    return db

def history(db, start="0001-01-01", end="9999-12-31", source=None):
    query = """SELECT s.day,s.source,s.external_id,s.title,g.* FROM sessions s JOIN sets g
      ON s.source=g.source AND s.external_id=g.session_id WHERE s.day BETWEEN ? AND ?"""
    args = [start, end]
    if source:
        query += " AND s.source=?"
        args.append(source)
    training = [dict(r) for r in db.execute(query+" ORDER BY s.day,s.external_id,g.movement_pos,g.position", args)]
    body_query = "SELECT * FROM body WHERE day BETWEEN ? AND ?"
    body_args = [start, end]
    if source:
        body_query += " AND source=?"
        body_args.append(source)
    body = [dict(r) for r in db.execute(body_query+" ORDER BY day,metric", body_args)]
    return {"training": training, "body": body}

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8",newline="\n")
