#!/usr/bin/env python3
"""Create an original story plan using OpenRouter's FREE model router only."""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SYSTEM = """You are the story editor for AI-Broskyee, a short-form original 3D animation studio.
Return ONLY valid JSON. Write an original, entertaining English short with a clear story arc, a strong first-second hook, escalation, a surprising but satisfying payoff, and no filler. Topic inspiration may come from public trending headlines, but do not copy a headline's article, script, characters, clips, or protected creative expression. Avoid unsupported factual claims; when a topic is factual, keep claims modest and state them only if common and verifiable. Never use celebrity likenesses or copyrighted characters. Give the audience genuine entertainment or educational value, not a misleading hook.
The production uses a compact procedural 3D prop vocabulary. Each scene must use a visual type from: cloud, rocket, planet, phone, brain, heart, flower, robot, book, lightbulb, atom, plant, star, camera, water_drop, gear, magnet, globe, cube, sphere, cone, cylinder, torus. Provide specific movement and emotion but keep each scene renderable using these assets.
Schema: {\"title\": string, \"description\": string, \"topic\": string, \"hook\": string, \"duration_seconds\": integer 20-55, \"tags\": [4-8 short strings], \"scenes\": [{\"narration\": string, \"caption\": string (max 34 characters), \"visual\": one supported type, \"companion\": one supported type, \"action\": string, \"emotion\": one of curious, happy, worried, surprised, determined, relieved}]. Use 5-8 scenes. Narration across all scenes must fit the selected duration at a natural pace. Keep captions short, no hashtag spam, no dangerous instructions, and no generic repeated story template. JSON only."""

SUPPORTED = {"cloud","rocket","planet","phone","brain","heart","flower","robot","book","lightbulb","atom","plant","star","camera","water_drop","gear","magnet","globe","cube","sphere","cone","cylinder","torus"}
EMOTIONS = {"curious","happy","worried","surprised","determined","relieved"}

def call_free_router(api_key: str, candidates: list[dict], retry_feedback: str = "") -> dict:
    user = {
      "current_candidate_topics": [{"title":x.get("title"),"source":x.get("source"),"url":x.get("url"),"summary":x.get("summary","")} for x in candidates[:18]],
      "quality_feedback_from_previous_attempt": retry_feedback,
      "request": "Choose the strongest topic for an English 3D short likely to earn genuine watch time. Create one original and complete story plan using the required JSON schema. Prefer an evergreen or currently relevant hook without misleading clickbait. Every scene needs purposeful visual movement."
    }
    body = json.dumps({"model":"openrouter/free","messages":[{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps(user, ensure_ascii=False)}],"temperature":0.85,"max_tokens":3200}).encode()
    headers = {"Authorization":f"Bearer {api_key}","Content-Type":"application/json","HTTP-Referer":os.environ.get("OPENROUTER_SITE_URL","https://github.com/aibroskyee-beep"),"X-Title":os.environ.get("OPENROUTER_APP_NAME","AI-Broskyee AutoFactory")}
    req = Request("https://openrouter.ai/api/v1/chat/completions", data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=70) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", "replace")
        raise RuntimeError(f"Free AI request failed with HTTP {exc.code}; no paid fallback was attempted. {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Free AI request unavailable; no paid fallback was attempted: {exc}") from exc
    content = payload["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    text = str(content).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
        raise RuntimeError("Free model returned invalid JSON; refusing to render an unchecked plan.") from exc

def validate(plan: dict, topic_candidates: list[dict]) -> dict:
    required = ["title","description","topic","hook","duration_seconds","tags","scenes"]
    missing = [key for key in required if key not in plan]
    if missing: raise ValueError(f"Plan missing fields: {missing}")
    plan["title"] = str(plan["title"]).strip()[:95]
    plan["description"] = str(plan["description"]).strip()[:4000]
    duration = int(plan["duration_seconds"])
    if not 20 <= duration <= 55: raise ValueError("duration_seconds must be 20..55")
    scenes = plan["scenes"]
    if not isinstance(scenes, list) or not 5 <= len(scenes) <= 8: raise ValueError("scenes must contain 5..8 scenes")
    for i, scene in enumerate(scenes):
        for key in ("narration","caption","visual","companion","action","emotion"):
            if key not in scene: raise ValueError(f"Scene {i+1} missing {key}")
        scene["visual"] = str(scene["visual"]).lower().strip()
        scene["companion"] = str(scene["companion"]).lower().strip()
        if scene["visual"] not in SUPPORTED or scene["companion"] not in SUPPORTED:
            raise ValueError(f"Scene {i+1} uses an unsupported visual type")
        scene["caption"] = str(scene["caption"]).strip()[:34]
        scene["narration"] = str(scene["narration"]).strip()
        scene["emotion"] = str(scene["emotion"]).lower().strip()
        if scene["emotion"] not in EMOTIONS: scene["emotion"] = "curious"
        scene["action"] = str(scene["action"]).strip()[:220]
    plan["tags"] = [str(x).strip().lstrip("#")[:30] for x in plan.get("tags",[]) if str(x).strip()][:8]
    plan["source_candidates"] = [{"title":x.get("title",""),"url":x.get("url",""),"source":x.get("source","")} for x in topic_candidates[:8]]
    plan["generator"] = "openrouter/free"
    return plan

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--trends", default="work/trends.json")
    ap.add_argument("--out", default="work/plan.json")
    ap.add_argument("--feedback", default="")
    args=ap.parse_args()
    key=os.environ.get("OPENROUTER_API_KEY","").strip()
    if not key:
        print("ERROR: OPENROUTER_API_KEY is missing. Add a free-only key locally or as a repository secret; no paid AI fallback exists.",file=sys.stderr)
        return 3
    data=json.loads(Path(args.trends).read_text(encoding="utf-8"))
    candidates=data.get("items",[])
    if not candidates: print("ERROR: No trend candidates were discovered.",file=sys.stderr); return 4
    try:
        plan=validate(call_free_router(key,candidates,args.feedback),candidates)
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); return 5
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"Story plan ready: {plan['title']} ({len(plan['scenes'])} scenes, {plan['duration_seconds']}s)")
    return 0
if __name__=="__main__": raise SystemExit(main())
