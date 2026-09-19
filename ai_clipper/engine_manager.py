from __future__ import annotations
import json, os, shutil, sys, tempfile, urllib.request, zipfile
from pathlib import Path
from typing import Callable
from .paths import engines_dir, models_dir, resource_dir

ProgressCB = Callable[[str], None]
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
WHISPER_REPO_API = "https://api.github.com/repos/ggml-org/whisper.cpp/releases/latest"
LLAMA_REPO_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
WHISPER_MODELS = {
    "small": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
    "medium": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
    "large-v3-turbo": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin",
}

def _ua_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent":"AIClipperStudio/0.2.0"})

def _json_get(url: str) -> dict:
    with urllib.request.urlopen(_ua_request(url), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def _download(url: str, dest: Path, cb: ProgressCB | None=None) -> None:
    with urllib.request.urlopen(_ua_request(url), timeout=60) as r, open(dest,"wb") as f:
        total=int(r.headers.get("Content-Length") or 0); got=0
        while True:
            chunk=r.read(1024*1024)
            if not chunk: break
            f.write(chunk); got += len(chunk)
            if cb and total: cb(f"Mengunduh {dest.name}: {got*100//total}%")

def _extract_zip(zip_path: Path, target: Path) -> None:
    target.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path) as z: z.extractall(target)

def _find(root: Path, names: list[str]) -> Path | None:
    wanted={n.lower() for n in names}
    if not root.exists(): return None
    for p in root.rglob("*"):
        if p.is_file() and p.name.lower() in wanted: return p
    return None

def _bundled_root() -> Path:
    return resource_dir()/"vendor_engines"

def _is_frozen_release() -> bool:
    return bool(getattr(sys,"frozen",False))

def seed_bundled_engines(cb: ProgressCB | None=None) -> bool:
    src=_bundled_root()
    if not src.exists(): return False
    dst=engines_dir(); copied=False
    for name in ("ffmpeg","whisper","llama"):
        source=src/name; target=dst/name
        if source.exists() and not target.exists():
            if cb: cb(f"Menyiapkan engine {name} dari paket…")
            shutil.copytree(source,target); copied=True
    return copied

def _ensure_seeded() -> None:
    seed_bundled_engines(None)

def ffmpeg_exe() -> Path | None:
    _ensure_seeded(); return _find(engines_dir()/"ffmpeg",["ffmpeg.exe","ffmpeg"])

def whisper_exe() -> Path | None:
    _ensure_seeded(); return _find(engines_dir()/"whisper",["whisper-cli.exe","main.exe","whisper-cli"])

def llama_server_exe() -> Path | None:
    _ensure_seeded(); return _find(engines_dir()/"llama",["llama-server.exe","server.exe","llama-server"])

def whisper_model_path(name: str) -> Path:
    return models_dir()/f"ggml-{name}.bin"

def _runtime_download_forbidden(engine_name: str) -> None:
    if _is_frozen_release():
        raise RuntimeError(f"Engine {engine_name} tidak ada di paket release. Instal ulang dari release resmi.")

def install_ffmpeg(cb: ProgressCB | None=None) -> Path:
    existing=ffmpeg_exe()
    if existing: return existing
    _runtime_download_forbidden("FFmpeg")
    if cb: cb("Menyiapkan FFmpeg (DEV mode)…")
    target=engines_dir()/"ffmpeg"
    with tempfile.TemporaryDirectory() as td:
        z=Path(td)/"ffmpeg.zip"; _download(FFMPEG_URL,z,cb); _extract_zip(z,target)
    p=ffmpeg_exe()
    if not p: raise RuntimeError("ffmpeg.exe tidak ditemukan.")
    return p

def _latest_asset(api_url: str, matcher) -> str:
    data=_json_get(api_url)
    for a in data.get("assets",[]):
        name=str(a.get("name",""))
        if matcher(name.lower()): return a["browser_download_url"]
    raise RuntimeError("Aset Windows x64 tidak ditemukan.")

def install_whisper(cb: ProgressCB | None=None) -> Path:
    existing=whisper_exe()
    if existing:return existing
    _runtime_download_forbidden("whisper.cpp")
    if cb: cb("Mencari whisper.cpp Windows x64…")
    url=_latest_asset(WHISPER_REPO_API,lambda n:n.endswith(".zip") and "x64" in n and "whisper-bin" in n and "cuda" not in n and "blas" not in n and "arm" not in n)
    target=engines_dir()/"whisper"
    with tempfile.TemporaryDirectory() as td:
        z=Path(td)/"whisper.zip"; _download(url,z,cb); _extract_zip(z,target)
    p=whisper_exe()
    if not p: raise RuntimeError("whisper-cli.exe tidak ditemukan.")
    return p

def install_llama(cb: ProgressCB | None=None) -> Path:
    existing=llama_server_exe()
    if existing:return existing
    _runtime_download_forbidden("llama.cpp")
    if cb: cb("Mencari llama.cpp Windows x64…")
    url=_latest_asset(LLAMA_REPO_API,lambda n:n.endswith(".zip") and "win" in n and "x64" in n and "cpu" in n and "cuda" not in n and "vulkan" not in n)
    target=engines_dir()/"llama"
    with tempfile.TemporaryDirectory() as td:
        z=Path(td)/"llama.zip"; _download(url,z,cb); _extract_zip(z,target)
    p=llama_server_exe()
    if not p: raise RuntimeError("llama-server.exe tidak ditemukan.")
    return p

def install_whisper_model(name: str, cb: ProgressCB | None=None) -> Path:
    if name not in WHISPER_MODELS: raise ValueError(f"Model Whisper tidak dikenal: {name}")
    out=whisper_model_path(name)
    if out.exists() and out.stat().st_size>10_000_000:return out
    if cb: cb(f"Mengunduh model Whisper {name}…")
    tmp=out.with_suffix(out.suffix+".part"); _download(WHISPER_MODELS[name],tmp,cb); tmp.replace(out)
    return out

def status() -> dict[str,bool]:
    _ensure_seeded()
    return {
        "ffmpeg": _find(engines_dir()/"ffmpeg",["ffmpeg.exe","ffmpeg"]) is not None,
        "whisper": _find(engines_dir()/"whisper",["whisper-cli.exe","main.exe","whisper-cli"]) is not None,
        "llama": _find(engines_dir()/"llama",["llama-server.exe","server.exe","llama-server"]) is not None,
    }

def auto_setup(whisper_model: str, include_llama: bool, cb: ProgressCB | None=None) -> None:
    seed_bundled_engines(cb)
    install_ffmpeg(cb)
    install_whisper(cb)
    install_whisper_model(whisper_model,cb)
    if include_llama: install_llama(cb)
    if cb: cb("Setup engine selesai.")
