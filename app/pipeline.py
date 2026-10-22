#!/usr/bin/env python3
"""One-job-at-a-time orchestration. Fails closed and never selects a paid AI model."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work'; OUTPUT=ROOT/'output'

def run(cmd, env=None, timeout=1800):
    print('\n+',' '.join(str(x) for x in cmd),flush=True)
    p=subprocess.run([str(x) for x in cmd],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    print(p.stdout[-12000:],flush=True)
    if p.returncode: raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(map(str,cmd))}\n{p.stdout[-2500:]}")
    return p.stdout

def main():
    WORK.mkdir(parents=True,exist_ok=True); OUTPUT.mkdir(parents=True,exist_ok=True)
    # Storage guard: protect the working volume and project size before substantial work.
    usage=shutil.disk_usage(ROOT)
    free_gb=usage.free/(1024**3)
    project_gb=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())/(1024**3)
    if free_gb<1.5: raise SystemExit(f"STOP: only {free_gb:.2f} GB free on rendering worker")
    if project_gb>9.0: raise SystemExit(f"STOP: workspace is {project_gb:.2f} GB, above 9 GB soft limit")
    print(f"Storage preflight passed: {project_gb:.3f} GB project; {free_gb:.1f} GB free on temporary worker")
    py=sys.executable
    env=os.environ.copy()
    for k in ('OPENROUTER_API_KEY','YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN','IG_USER_ID','IG_ACCESS_TOKEN','IG_GRAPH_VERSION','GITHUB_TOKEN','GITHUB_REPOSITORY'):
        if k in os.environ: env[k]=os.environ[k]
    trend_file=WORK/'trends.json'
    run([py,'app/scout.py','--out',trend_file],env=env,timeout=90)
    feedback=''
    final=OUTPUT/'final.mp4'
    report_path=OUTPUT/'quality-report.json'
    for attempt in range(1,4):
        print(f"\n========== PRODUCTION ATTEMPT {attempt}/3 ==========")
        plan=WORK/'plan.json'; visual=WORK/'visual.mp4'; voice=WORK/'voice.wav'; music=WORK/'music.wav'; candidate=WORK/'candidate.mp4'
        run([py,'app/story_writer.py','--trends',trend_file,'--out',plan,'--feedback',feedback],env=env,timeout=100)
        blender=os.environ.get('BLENDER_BIN','blender')
        blender_cmd=[blender,'--background','--threads','2','--python','app/render_story.py','--',str(plan),str(visual)]
        # xvfb is only needed on runners configured for an X session; background Blender usually needs none.
        run(blender_cmd,env=env,timeout=1400)
        piper_model=os.environ.get('PIPER_MODEL',str(ROOT/'assets/voice/en_US-lessac-medium.onnx'))
        run([py,'app/make_audio.py','--plan',plan,'--outdir',WORK,'--voice-model',piper_model],env=env,timeout=300)
        mix_filter='[1:a]volume=1.0[voice];[2:a]volume=0.22[music];[voice][music]amix=inputs=2:duration=longest:dropout_transition=1,alimiter=limit=0.94,loudnorm=I=-16:TP=-1.5:LRA=11[a]'
        run(['ffmpeg','-y','-i',visual,'-i',voice,'-i',music,'-filter_complex',mix_filter,'-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',candidate],env=env,timeout=420)
        qa_cmd=[py,'app/quality_gate.py',str(candidate),'--report',report_path]
        try:
            run(qa_cmd,env=env,timeout=700)
            shutil.copy2(candidate,final)
            shutil.copy2(plan,OUTPUT/'metadata.json')
            print(f"PASS: verified output preserved at {final}",flush=True)
            break
        except Exception as exc:
            feedback=(f"Attempt {attempt} failed technical QA. Fix the failure without copying any existing video: {str(exc)[:1800]}. Keep the next plan valid JSON and keep visual motion/captions inside portrait-safe margins.")
            (WORK/'last_qa_failure.txt').write_text(feedback,encoding='utf-8')
            if attempt==3:
                (OUTPUT/'pipeline-status.json').write_text(json.dumps({'status':'failed_quality_gate','attempts':3,'details':feedback},indent=2),encoding='utf-8')
                print('STOP: quality gate failed after 3 attempts. Nothing was published.',file=sys.stderr)
                return 2
    # Platform publishing is all-or-nothing preflight: missing auth means video is retained but not posted.
    creds_ok=all(os.environ.get(k,'').strip() for k in ('YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN','IG_USER_ID','IG_ACCESS_TOKEN','GITHUB_TOKEN','GITHUB_REPOSITORY'))
    auto=os.environ.get('AUTO_PUBLISH_ENABLED','true').lower() in ('1','true','yes')
    status={'status':'qa_passed','video':str(final.relative_to(ROOT)),'published':False}
    if auto and creds_ok:
        try:
            run([py,'app/publish.py','--video',final,'--plan',OUTPUT/'metadata.json','--out',OUTPUT/'publish-result.json'],env=env,timeout=1200)
            result=json.loads((OUTPUT/'publish-result.json').read_text(encoding='utf-8'))
            status.update(result)
        except Exception as exc:
            status.update({'status':'qa_passed_publish_failed','publish_error':str(exc)[:2000]})
            partial=OUTPUT/'publish-result.json'
            if partial.is_file():
                try: status['partial_publish_result']=json.loads(partial.read_text(encoding='utf-8'))
                except Exception: pass
            print('PUBLISH FAILED: verified MP4 retained; no retry to a paid service.',file=sys.stderr)
    else:
        missing=[k for k in ('YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN','IG_USER_ID','IG_ACCESS_TOKEN','GITHUB_TOKEN','GITHUB_REPOSITORY') if not os.environ.get(k,'').strip()]
        status.update({'status':'qa_passed_publish_not_configured','missing_credentials':missing})
        print('VIDEO READY, NOT PUBLISHED: official platform credentials are not all configured.',flush=True)
    (OUTPUT/'pipeline-status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    print(json.dumps(status,indent=2),flush=True)
    return 0
if __name__=='__main__': raise SystemExit(main())
