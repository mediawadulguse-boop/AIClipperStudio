from __future__ import annotations
import json, os, shutil, subprocess
from pathlib import Path
from .paths import engines_dir
from .transcript import write_clip_srt
from .models import TranscriptSegment

def _which(name: str) -> str | None:
    found = shutil.which(name)
    if found: return found
    root = engines_dir() / "ffmpeg"
    candidates = list(root.rglob(name + (".exe" if os.name == "nt" else "")))
    return str(candidates[0]) if candidates else None

def ffmpeg_path() -> str | None: return _which("ffmpeg")
def ffprobe_path() -> str | None: return _which("ffprobe")
def ffplay_path() -> str | None: return _which("ffplay")

def probe_video(path: str) -> dict:
    exe = ffprobe_path()
    if not exe: raise RuntimeError("FFprobe belum tersedia. Jalankan Setup Otomatis.")
    cmd = [exe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path]
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if cp.returncode != 0: raise RuntimeError(cp.stderr.strip() or "Gagal membaca video")
    data = json.loads(cp.stdout or "{}")
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"duration": float(data.get("format", {}).get("duration") or 0), "width": int(video_stream.get("width") or 0), "height": int(video_stream.get("height") or 0), "codec": video_stream.get("codec_name", "")}

def extract_audio(video: str, wav_out: str) -> None:
    exe = ffmpeg_path()
    if not exe: raise RuntimeError("FFmpeg belum tersedia. Jalankan Setup Otomatis.")
    cp = subprocess.run([exe, "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav_out], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if cp.returncode != 0: raise RuntimeError(cp.stderr[-2000:] or "Gagal mengekstrak audio")

def preview_clip(video: str, start: float, duration: float) -> None:
    exe = ffplay_path()
    if not exe: raise RuntimeError("FFplay belum tersedia.")
    subprocess.Popen([exe, "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-autoexit", "-window_title", "AI Clipper Preview", video])

def export_clip(video: str, output: str, start: float, end: float, ratio: str = "original", burn_subtitles: bool = False, transcript: list[TranscriptSegment] | None = None) -> None:
    exe = ffmpeg_path()
    if not exe: raise RuntimeError("FFmpeg belum tersedia.")
    duration = max(0.1, end - start)
    vf: list[str] = []
    if ratio == "9:16": vf.append("crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=1080:1920")
    elif ratio == "1:1": vf.append("crop='min(iw,ih)':'min(iw,ih)',scale=1080:1080")
    elif ratio == "4:5": vf.append("crop='min(iw,ih*4/5)':'min(ih,iw*5/4)',scale=1080:1350")
    elif ratio == "16:9": vf.append("crop='min(iw,ih*16/9)':'min(ih,iw*9/16)',scale=1920:1080")
    if burn_subtitles and transcript:
        temp_srt = str(Path(output).with_suffix(".clip.srt"))
        write_clip_srt(transcript, start, end, temp_srt)
        esc = Path(temp_srt).resolve().as_posix().replace(":", "\\:").replace("'", "\\'")
        vf.append(f"subtitles=filename='{esc}':force_style='FontName=Arial,FontSize=22,Outline=2,Shadow=1,Alignment=2,MarginV=75'")
    cmd = [exe, "-y", "-ss", f"{start:.3f}", "-i", video, "-t", f"{duration:.3f}"]
    if vf: cmd += ["-vf", ",".join(vf)]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", output]
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if cp.returncode != 0: raise RuntimeError(cp.stderr[-3000:] or "Export gagal")
