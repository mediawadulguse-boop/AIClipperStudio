from __future__ import annotations
import json
import sqlite3
from .paths import db_path
from .models import ClipCandidate, TranscriptSegment

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_path TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    transcript_json TEXT,
    candidates_json TEXT,
    status TEXT DEFAULT 'new'
);
"""

def connect() -> sqlite3.Connection:
    con = sqlite3.connect(db_path())
    con.execute(SCHEMA)
    con.commit()
    return con

def create_project(video_path: str) -> int:
    with connect() as con:
        cur = con.execute("INSERT INTO projects(video_path) VALUES (?)", (video_path,))
        con.commit()
        return int(cur.lastrowid)

def save_analysis(project_id: int, transcript: list[TranscriptSegment], candidates: list[ClipCandidate], status: str = "done") -> None:
    t = json.dumps([x.to_dict() for x in transcript], ensure_ascii=False)
    c = json.dumps([x.to_dict() for x in candidates], ensure_ascii=False)
    with connect() as con:
        con.execute("UPDATE projects SET transcript_json=?, candidates_json=?, status=? WHERE id=?", (t, c, status, project_id))
        con.commit()
