from __future__ import annotations
import re
from .models import TranscriptSegment, ClipCandidate

QUESTION = {"kenapa","mengapa","bagaimana","siapa","apa","kok","benarkah","ternyata"}
CONFLICT = {"tapi","tetapi","namun","salah","bohong","bantah","bukan","gagal","masalah","konflik","protes","aneh","dibantah"}
EMOTION = {"kaget","marah","kecewa","takut","senang","sedih","parah","gila","luar biasa","mengejutkan","viral"}
INFO = {"data","fakta","angka","persen","miliar","juta","ribu","dokumen","hasil","laporan","bukti","anggaran"}
HOOK_PHRASES = ["ternyata","yang tidak banyak orang tahu","faktanya","masalah sebenarnya","justru","ini yang terjadi","yang mengejutkan"]

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\w%]+", text.lower(), re.UNICODE)

def _count_words(text: str, vocab: set[str]) -> int:
    return len(set(_tokenize(text)).intersection(vocab))

def _number_signal(text: str) -> int:
    return min(3, len(re.findall(r"\b\d+(?:[.,]\d+)?\b|\b\d+%", text)))

def heuristic_dimensions(text: str, duration: float) -> dict[str,int]:
    lower=text.lower(); q=_count_words(text,QUESTION); c=_count_words(text,CONFLICT); e=_count_words(text,EMOTION); inf=_count_words(text,INFO)+_number_signal(text)
    hook_hits=sum(1 for p in HOOK_PHRASES if p in lower); punct_q=text.count("?")
    hook=min(100,45+12*hook_hits+7*q+4*punct_q)
    curiosity=min(100,40+10*q+10*hook_hits+5*c)
    conflict=min(100,35+13*c)
    information=min(100,40+9*inf+min(20,len(_tokenize(text))//12))
    emotion=min(100,35+14*e+4*text.count("!"))
    length_score=100-min(55,abs(duration-42)*1.4)
    sentence_count=max(1,len(re.findall(r"[.!?]+",text)))
    standalone=min(100,48+min(28,sentence_count*5)+(12 if len(text)>160 else 0))
    standalone=int((standalone+length_score)/2)
    return {"hook":int(hook),"curiosity":int(curiosity),"conflict":int(conflict),"information":int(information),"emotion":int(emotion),"standalone":int(standalone)}

def weighted_score(d: dict[str,int]) -> int:
    score=d["hook"]*.25+d["curiosity"]*.20+d["conflict"]*.15+d["information"]*.15+d["emotion"]*.10+d["standalone"]*.15
    return max(1,min(100,int(round(score))))

def make_heuristic_candidates(segments:list[TranscriptSegment],min_seconds:int=20,max_seconds:int=75,limit:int=18)->list[ClipCandidate]:
    if not segments:return []
    candidates=[]; n=len(segments)
    for i in range(n):
        text_parts=[]; start=segments[i].start
        for j in range(i,min(n,i+18)):
            text_parts.append(segments[j].text); end=segments[j].end; dur=end-start
            if dur<min_seconds:continue
            if dur>max_seconds:break
            text=" ".join(text_parts).strip(); dims=heuristic_dimensions(text,dur); score=weighted_score(dims)
            candidates.append(ClipCandidate(start,end,score,_title_from_text(text),_reason_from_dims(dims),text,**dims))
            if dur>=35 and (j-i)>=4:break
    candidates.sort(key=lambda c:c.score,reverse=True)
    chosen=[]
    for c in candidates:
        if any(max(0.0,min(c.end,p.end)-max(c.start,p.start))/max(1.0,min(c.duration,p.duration))>.55 for p in chosen):continue
        chosen.append(c)
        if len(chosen)>=limit:break
    return chosen

def _title_from_text(text:str)->str:
    cleaned=re.sub(r"\s+"," ",text).strip(); first=re.split(r"(?<=[.!?])\s+",cleaned)[0]; words=first.split()
    if len(words)>11:first=" ".join(words[:11])+"…"
    return first[:90] or "Kandidat Clip"

def _reason_from_dims(d:dict[str,int])->str:
    labels={"hook":"hook kuat","curiosity":"memicu rasa penasaran","conflict":"mengandung kontras/konflik","information":"nilai informasi tinggi","emotion":"muatan emosi kuat","standalone":"cukup utuh tanpa konteks panjang"}
    best=sorted(d,key=d.get,reverse=True)[:3]
    return ", ".join(labels[x] for x in best).capitalize()+"."
