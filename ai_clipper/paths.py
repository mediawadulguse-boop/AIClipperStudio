from __future__ import annotations
import os
import sys
from pathlib import Path

APP_NAME = "AIClipperStudio"

def app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path

def resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]

def engines_dir() -> Path:
    p = app_data_dir() / "engines"; p.mkdir(parents=True, exist_ok=True); return p

def models_dir() -> Path:
    p = app_data_dir() / "models"; p.mkdir(parents=True, exist_ok=True); return p

def projects_dir() -> Path:
    p = app_data_dir() / "projects"; p.mkdir(parents=True, exist_ok=True); return p

def exports_dir() -> Path:
    p = app_data_dir() / "exports"; p.mkdir(parents=True, exist_ok=True); return p

def db_path() -> Path:
    return app_data_dir() / "aiclipper.db"

def config_path() -> Path:
    return app_data_dir() / "config.json"
