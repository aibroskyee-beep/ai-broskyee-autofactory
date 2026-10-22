#!/usr/bin/env python3
"""Generate narration with Piper and a fully original lightweight synth bed; no paid audio API."""
from __future__ import annotations
import argparse, json, math, os, random, shutil, subprocess, sys, wave
from pathlib import Path

SR=44100

def make_music(path: Path, duration: float):
    # A gentle, original four-chord pulse. No samples or copyrighted track is used.
    chords=[[220.00,261.63,329.63],[174.61,220.00,261.63],[130.81,164.81,196.00],[196.00,246.94,293.66]]
    rng=random.Random(2107)
    n=int(SR*duration)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        block=4096
        for off in range(0,n,block):
            frames=[]
            for j in range(off,min(off+block,n)):
                t=j/SR; chord=chords[int(t/4.0)%4]
                # slow amplitude envelope and a low-level pluck every half second
                env=0.65+0.35*math.sin(2*math.pi*t/8.0)
                pad=sum(math.sin(2*math.pi*f*t + 0.08*math.sin(2*math.pi*0.18*t)) for f in chord)/3
                bass=0.45*math.sin(2*math.pi*(chord[0]/2)*t)
                beat_phase=t%0.5
                pluck=0.11*math.exp(-beat_phase*9)*math.sin(2*math.pi*chord[1]*t) if beat_phase<0.22 else 0.0
                fade=min(1.0,t/1.2,max(0.0,(duration-t)/1.3))
                val=(pad*0.10+bass*0.05+pluck*0.07)*env*fade
                sample=max(-1,min(1,val))
                pcm=int(sample*32767)
                frames.append(pcm.to_bytes(2,'little',signed=True)*2)
            w.writeframes(b''.join(frames))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--plan',default='work/plan.json'); ap.add_argument('--outdir',default='work'); ap.add_argument('--voice-model',default=os.environ.get('PIPER_MODEL','')); ap.add_argument('--piper-bin',default=os.environ.get('PIPER_BIN','piper')); args=ap.parse_args()
    plan=json.loads(Path(args.plan).read_text(encoding='utf-8'))
    out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True)
    text=' '.join(str(s.get('narration','')).strip() for s in plan['scenes']).strip()
    if len(text)<80: raise SystemExit('ERROR: Narration is too short; refusing to create a silent or low-value video.')
    txt_path=out/'narration.txt'; txt_path.write_text(text,encoding='utf-8')
    voice_path=out/'voice.wav'; music_path=out/'music.wav'
    piper=shutil.which(args.piper_bin) or (args.piper_bin if Path(args.piper_bin).exists() else None)
    if not piper: raise SystemExit('ERROR: Piper TTS is unavailable. No paid TTS fallback will be used.')
    if not args.voice_model or not Path(args.voice_model).is_file(): raise SystemExit('ERROR: PIPER_MODEL must point to the downloaded English voice model.')
    model_json=Path(args.voice_model+'.json')
    if not model_json.exists(): raise SystemExit(f'ERROR: Voice config not found: {model_json}')
    cmd=[piper,'--model',args.voice_model,'--config',str(model_json),'--output_file',str(voice_path)]
    res=subprocess.run(cmd,input=text.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240)
    if res.returncode!=0: raise SystemExit('ERROR: Piper failed: '+res.stderr.decode('utf-8','replace')[-1200:])
    # Use the selected story duration. Speech occupies the timeline; the bed is trimmed with the final MP4.
    make_music(music_path,float(plan.get('duration_seconds',36)))
    print(f'Voice and original synth bed ready: {voice_path}, {music_path}')
if __name__=='__main__': main()
