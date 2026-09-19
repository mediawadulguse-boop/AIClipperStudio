from __future__ import annotations
import re
from pathlib import Path
from .models import TranscriptSegment

_TS = re.compile(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{3})")

def _to_seconds(ts: str) -> float:
    m = _TS.search(ts.strip())
    if not m:
        raise ValueError(f"Timestamp tidak valid: {ts}")
    return int(m.group("h")) * 3600 + int(m.group("m")) * 60 + int(m.group("s")) + int(m.group("ms")) / 1000

def parse_srt(path: str | Path) -> list[TranscriptSegment]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    out: list[TranscriptSegment] = []
    for block in blocks:
        lines = [x.strip("\ufeff") for x in block.splitlines() if x.strip()]
        if len(lines) < 2:
            continue
        idx = 1 if lines[0].strip().isdigit() else 0
        if idx >= len(lines) or "-->" not in lines[idx]:
            continue
        a, b = [x.strip() for x in lines[idx].split("-->", 1)]
        try:
            start, end = _to_seconds(a), _to_seconds(b)
        except ValueError:
            continue
        body = " ".join(lines[idx + 1:]).strip()
        if body:
            out.append(TranscriptSegment(start, end, body))
    return out

def seconds_to_clock(sec: float) -> str:
    sec = max(0, int(round(sec)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def seconds_to_srt(sec: float) -> str:
    ms_total = max(0, int(round(sec * 1000)))
    h, rem = divmod(ms_total, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write_clip_srt(segments: list[TranscriptSegment], clip_start: float, clip_end: float, out_path: str | Path) -> None:
    rows: list[str] = []
    n = 1
    for seg in segments:
        if seg.end <= clip_start or seg.start >= clip_end:
            continue
        start = max(seg.start, clip_start) - clip_start
        end = min(seg.end, clip_end) - clip_start
        rows.append(f"{n}\n{seconds_to_srt(start)} --> {seconds_to_srt(end)}\n{seg.text}\n")
        n += 1
    Path(out_path).write_text("\n".join(rows), encoding="utf-8")
