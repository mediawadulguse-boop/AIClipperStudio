from __future__ import annotations
import subprocess
from pathlib import Path
from .config import AppConfig
from .engine_manager import whisper_exe, whisper_model_path
from .models import TranscriptSegment, ClipCandidate
from .transcript import parse_srt
from .scoring import make_heuristic_candidates
from .llm import LocalLLM
from .media import extract_audio

def transcribe(video: str, workdir: str | Path, cfg: AppConfig, on_status=None) -> list[TranscriptSegment]:
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    wav = work / "audio_16k.wav"
    prefix = work / "transcript"
    srt = work / "transcript.srt"
    if on_status: on_status("Mengekstrak audio 16 kHz…")
    extract_audio(video, str(wav))
    exe = whisper_exe()
    model = whisper_model_path(cfg.whisper_model)
    if not exe or not model.exists():
        raise RuntimeError("Whisper/model belum tersedia. Jalankan Setup Otomatis terlebih dahulu.")
    if on_status: on_status("Whisper sedang mentranskripsi video…")
    cmd = [str(exe), "-m", str(model), "-f", str(wav), "-l", cfg.language, "-osrt", "-of", str(prefix)]
    flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        flags = subprocess.CREATE_NO_WINDOW
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=flags)
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout)[-3000:] or "Whisper gagal")
    if not srt.exists():
        srts = list(work.glob("transcript*.srt"))
        if srts:
            srt = srts[0]
    if not srt.exists():
        raise RuntimeError("Whisper selesai tetapi file SRT tidak ditemukan.")
    segments = parse_srt(srt)
    if not segments:
        raise RuntimeError("Transcript kosong.")
    return segments

def analyze(transcript: list[TranscriptSegment], cfg: AppConfig, on_status=None) -> list[ClipCandidate]:
    if on_status: on_status("Membuat kandidat berdasarkan struktur percakapan…")
    heuristic = make_heuristic_candidates(transcript, min_seconds=cfg.min_clip_seconds, max_seconds=cfg.max_clip_seconds, limit=max(cfg.max_candidates * 2, 18))
    if cfg.ai_mode == "local_lite":
        if on_status: on_status("Analisis Local Lite selesai.")
        return heuristic[:cfg.max_candidates]
    try:
        llm = LocalLLM(cfg.llama_model, cfg.llama_port)
        return llm.rank_candidates(heuristic, cfg.max_candidates, on_status)
    except Exception as e:
        if on_status: on_status(f"Qwen gagal/Belum siap; memakai Local Lite. Detail: {e}")
        return heuristic[:cfg.max_candidates]
