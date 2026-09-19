from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from .paths import config_path

@dataclass
class AppConfig:
    ai_mode: str = "local_llm"
    whisper_model: str = "small"
    qwen_model: str = "Qwen/Qwen3-4B-GGUF:Q4_K_M"
    language: str = "id"
    max_candidates: int = 12
    min_clip_seconds: int = 20
    max_clip_seconds: int = 75
    llama_port: int = 18080

def load_config() -> AppConfig:
    p = config_path()
    if not p.exists():
        cfg = AppConfig()
        save_config(cfg)
        return cfg
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return AppConfig(**{k: v for k, v in data.items() if k in AppConfig.__annotations__})
    except Exception:
        return AppConfig()

def save_config(cfg: AppConfig) -> None:
    p = config_path()
    p.write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False), encoding="utf-8")
