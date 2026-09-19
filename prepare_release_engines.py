from __future__ import annotations
import json, os, shutil, sys, time, urllib.request, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"vendor_engines"
CACHE=ROOT/".engine_cache"
FFMPEG_URL="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
WHISPER_REPO_API="https://api.github.com/repos/ggml-org/whisper.cpp/releases/latest"
LLAMA_REPO_API="https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
UA={"User-Agent":"AIClipperStudio-ReleaseBuilder/0.2.0"}

def req(url): return urllib.request.Request(url,headers=UA)
def get_json(url):
    with urllib.request.urlopen(req(url),timeout=60) as r:return json.loads(r.read().decode("utf-8"))

def human(n):
    n=float(n)
    for unit in ("B","KB","MB","GB"):
        if n<1024 or unit=="GB": return f"{n:.1f} {unit}"
        n/=1024

def zip_ok(path:Path)->bool:
    if not path.exists() or path.stat().st_size<1024:return False
    try:
        with zipfile.ZipFile(path) as z:return z.testzip() is None
    except Exception:return False

def download(url:str,dest:Path,label:str):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if zip_ok(dest):
        print(f"[OK] {label}: cache ditemukan ({human(dest.stat().st_size)}), skip download."); return
    part=dest.with_suffix(dest.suffix+".part")
    if part.exists():part.unlink()
    print(f"[DOWNLOAD] {label}\n  {url}")
    with urllib.request.urlopen(req(url),timeout=180) as r, open(part,"wb") as f:
        total=int(r.headers.get("Content-Length") or 0); got=0; last=0.0; started=time.time()
        while True:
            chunk=r.read(1024*1024)
            if not chunk:break
            f.write(chunk); got+=len(chunk); now=time.time()
            if now-last>=0.5:
                speed=got/max(now-started,.01)
                if total:print(f"  {got*100/total:6.1f}% {human(got)} / {human(total)} {human(speed)}/s")
                else:print(f"  {human(got)} {human(speed)}/s")
                last=now
    part.replace(dest)
    if not zip_ok(dest):raise RuntimeError(f"Download {label} tidak valid.")

def extract_cached(url,cache_name,target,label):
    target.mkdir(parents=True,exist_ok=True)
    z=CACHE/cache_name; download(url,z,label)
    with zipfile.ZipFile(z) as archive:archive.extractall(target)

def latest_asset(api_url,predicate):
    data=get_json(api_url)
    for asset in data.get("assets",[]):
        name=str(asset.get("name",""))
        if predicate(name.lower()):return asset["browser_download_url"],name
    raise RuntimeError("Matching Windows x64 release asset not found")

def find(root:Path,names:set[str]):
    if not root.exists():return None
    for p in root.rglob("*"):
        if p.is_file() and p.name.lower() in names:return p
    return None

def main():
    OUT.mkdir(parents=True,exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)
    if not (find(OUT/"ffmpeg",{"ffmpeg.exe"}) and find(OUT/"ffmpeg",{"ffprobe.exe"})):
        extract_cached(FFMPEG_URL,"ffmpeg-release-essentials.zip",OUT/"ffmpeg","FFmpeg")
    if not find(OUT/"whisper",{"whisper-cli.exe","main.exe"}):
        url,name=latest_asset(WHISPER_REPO_API,lambda n:n.endswith(".zip") and "x64" in n and "whisper-bin" in n and "cuda" not in n and "blas" not in n and "arm" not in n)
        extract_cached(url,"whisper_"+name,OUT/"whisper","whisper.cpp")
    if not find(OUT/"llama",{"llama-server.exe","server.exe"}):
        url,name=latest_asset(LLAMA_REPO_API,lambda n:n.endswith(".zip") and "win" in n and "x64" in n and "cpu" in n and "cuda" not in n and "vulkan" not in n)
        extract_cached(url,"llama_"+name,OUT/"llama","llama.cpp")
    missing=[]
    if not find(OUT/"ffmpeg",{"ffmpeg.exe"}):missing.append("ffmpeg")
    if not find(OUT/"ffmpeg",{"ffprobe.exe"}):missing.append("ffprobe")
    if not find(OUT/"whisper",{"whisper-cli.exe","main.exe"}):missing.append("whisper")
    if not find(OUT/"llama",{"llama-server.exe","server.exe"}):missing.append("llama")
    if missing:raise RuntimeError("Missing bundled engines: "+", ".join(missing))
    print("Release engines prepared.")

if __name__=="__main__":
    main()
