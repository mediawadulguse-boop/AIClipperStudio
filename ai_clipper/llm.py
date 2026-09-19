from __future__ import annotations
import json, socket, subprocess, time, urllib.request
from .engine_manager import llama_server_exe
from .models import ClipCandidate

def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False

class LocalLLM:
    def __init__(self, model: str, port: int = 18080):
        self.model=model; self.port=port; self.proc=None

    def ensure_server(self, on_status=None) -> None:
        if _port_open("127.0.0.1", self.port): return
        exe=llama_server_exe()
        if not exe: raise RuntimeError("llama.cpp belum tersedia. Jalankan Setup Otomatis.")
        if on_status: on_status("Menyalakan Qwen lokal. Pada pemakaian pertama model akan diunduh…")
        flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
        self.proc=subprocess.Popen([str(exe),"-hf",self.model,"--host","127.0.0.1","--port",str(self.port),"--ctx-size","8192","--jinja","--log-disable"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
        deadline=time.time()+300
        while time.time()<deadline:
            if _port_open("127.0.0.1", self.port):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health",timeout=2) as r:
                        if r.status==200 and "loading" not in r.read().decode("utf-8",errors="ignore").lower(): return
                except Exception: pass
            time.sleep(1)
        raise RuntimeError("Qwen lokal tidak siap dalam batas waktu startup.")

    def rank_candidates(self,candidates:list[ClipCandidate],max_output:int=12,on_status=None)->list[ClipCandidate]:
        if not candidates:return []
        self.ensure_server(on_status)
        payload=[{"id":i,"start":round(c.start,3),"end":round(c.end,3),"heuristic_score":c.score,"text":c.transcript[:2500]} for i,c in enumerate(candidates[:24])]
        prompt=("Anda adalah Viral Clip Editor untuk video Bahasa Indonesia. Nilai kandidat untuk Shorts/Reels/TikTok. "
                "Return JSON array saja. Maksimal "+str(max_output)+" item. Format: "
                '{"id":0,"score":92,"title":"judul pendek","reason":"alasan singkat","hook":90,"curiosity":94,"conflict":70,"information":88,"emotion":75,"standalone":91}'
                "\nKANDIDAT:\n"+json.dumps(payload,ensure_ascii=False))
        body={"model":self.model,"messages":[{"role":"system","content":"Return strict JSON only. Bahasa Indonesia."},{"role":"user","content":prompt}],"temperature":0.15,"max_tokens":2600}
        req=urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/chat/completions",data=json.dumps(body).encode("utf-8"),headers={"Content-Type":"application/json"},method="POST")
        if on_status:on_status("Qwen sedang menilai kandidat clip…")
        with urllib.request.urlopen(req,timeout=600) as r:
            content=json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
        start=content.find("["); end=content.rfind("]")
        if start<0 or end<=start: raise RuntimeError("Respons Qwen bukan JSON array.")
        arr=json.loads(content[start:end+1])
        ranked=[]; seen=set()
        for item in arr:
            try:
                idx=int(item["id"])
                if idx<0 or idx>=len(candidates) or idx in seen: continue
                seen.add(idx); base=candidates[idx]
                dims={k:_clamp(item.get(k,getattr(base,k))) for k in ["hook","curiosity","conflict","information","emotion","standalone"]}
                ranked.append(ClipCandidate(base.start,base.end,_clamp(item.get("score",base.score)),str(item.get("title") or base.title)[:100],str(item.get("reason") or base.reason)[:350],base.transcript,**dims))
            except Exception: continue
        if not ranked: raise RuntimeError("Respons Qwen tidak menghasilkan kandidat yang dapat dibaca.")
        ranked.sort(key=lambda x:x.score,reverse=True)
        return ranked[:max_output]

def _clamp(v)->int:
    try:return max(0,min(100,int(round(float(v)))))
    except Exception:return 0
