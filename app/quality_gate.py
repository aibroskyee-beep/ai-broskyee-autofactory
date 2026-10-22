#!/usr/bin/env python3
"""Technical MP4 QA. Fails closed: no upload if decode/audio/layout checks fail."""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys
from pathlib import Path

def run(cmd):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=600)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout)[-2500:])
    return p.stdout, p.stderr

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('--report',default='output/quality-report.json'); ap.add_argument('--min-seconds',type=float,default=20); ap.add_argument('--max-seconds',type=float,default=55); a=ap.parse_args()
    path=Path(a.video)
    if not path.is_file() or path.stat().st_size<100_000: raise SystemExit('FAIL: MP4 is missing or implausibly small (<100 KB).')
    raw,_=run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)])
    d=json.loads(raw); streams=d.get('streams',[]); video=next((x for x in streams if x.get('codec_type')=='video'),None); audio=next((x for x in streams if x.get('codec_type')=='audio'),None)
    errors=[]; duration=float(d.get('format',{}).get('duration',0) or 0)
    if not video: errors.append('No video stream')
    else:
        if int(video.get('width',0))!=720 or int(video.get('height',0))!=1280: errors.append(f"Wrong dimensions: {video.get('width')}x{video.get('height')}")
        fps=video.get('r_frame_rate','0/1')
        try:
            num,den=fps.split('/',1); rate=float(num)/float(den)
        except Exception: rate=0
        if rate<23.5 or rate>30.5: errors.append(f'Unexpected frame rate: {fps}')
    if not audio: errors.append('Audio stream missing')
    if not a.min_seconds<=duration<=a.max_seconds: errors.append(f'Duration {duration:.2f}s outside {a.min_seconds}-{a.max_seconds}s')
    # Decode the complete MP4, not only the first frame.
    _,decode_stderr=run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'])
    decode_errors=[x for x in decode_stderr.splitlines() if x.strip()]
    if decode_errors: errors.append('Decode errors: '+' | '.join(decode_errors[:3]))
    # Detect long black sections; brief fades are allowed.
    # The blackdetect filter reports any sustained fully-black passages in stderr.
    bp=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-vf','blackdetect=d=1.6:pix_th=0.04','-an','-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=600)
    black_events=re.findall(r'black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)',bp.stderr)
    if sum(float(x[2]) for x in black_events)>max(3.0,duration*0.15): errors.append('Large amount of detected black frames; inspect visual render')
    mean_volume=max_volume=None
    if audio:
        lp=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-vn','-af','volumedetect','-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=300)
        mm=re.search(r'mean_volume:\s*(-?inf|[-\d.]+) dB',lp.stderr); mx=re.search(r'max_volume:\s*(-?inf|[-\d.]+) dB',lp.stderr)
        def db(m):
            if not m:return None
            try:return float(m.group(1))
            except:return -999.0
        mean_volume=db(mm); max_volume=db(mx)
        if mean_volume is None or mean_volume < -32: errors.append(f'Audio too quiet or silent (mean={mean_volume})')
        if max_volume is None or max_volume > -0.5: errors.append(f'Audio peak may clip (max={max_volume} dB)')
    report={'file':str(path),'bytes':path.stat().st_size,'duration_seconds':round(duration,3),'width':int(video.get('width',0)) if video else None,'height':int(video.get('height',0)) if video else None,'fps':video.get('r_frame_rate') if video else None,'video_codec':video.get('codec_name') if video else None,'audio_codec':audio.get('codec_name') if audio else None,'audio_mean_db':mean_volume,'audio_max_db':max_volume,'black_events':len(black_events),'passed':not errors,'errors':errors}
    rp=Path(a.report); rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    if errors: print('QA FAILED: do not publish.',file=sys.stderr); return 2
    print('QA PASSED: technical gate passed. Visual meaning still needs sampled-frame review.',flush=True); return 0
if __name__=='__main__': raise SystemExit(main())
