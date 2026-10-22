#!/usr/bin/env python3
"""Generate an original short plan with a small local open model; no paid API."""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path

SYSTEM = """You are the story editor for AI-Broskyee, an original short-form 3D animation studio.
Return ONLY valid JSON. Write an original, entertaining English short with a clear story arc, an immediate hook, escalation, and a satisfying payoff. Topic ideas may come from public trend headlines, but never copy a headline's article, script, characters, clips, or protected expression. Avoid unsupported factual claims and misleading clickbait. Never use celebrity likenesses or copyrighted characters.
The render uses simple procedural 3D props. Each scene's visual and companion must be one of: cloud, rocket, planet, phone, brain, heart, flower, robot, book, lightbulb, atom, plant, star, camera, water_drop, gear, magnet, globe, cube, sphere, cone, cylinder, torus. Use concrete motion and emotion.
Schema: {\"title\": string, \"description\": string, \"topic\": string, \"hook\": string, \"duration_seconds\": integer 20-55, \"tags\": [4-8 short strings], \"scenes\": [{\"narration\": string, \"caption\": string max 34 characters, \"visual\": one supported type, \"companion\": one supported type, \"action\": string, \"emotion\": one of curious, happy, worried, surprised, determined, relieved}]. Use 5-8 scenes. Fit narration to duration at a natural pace. Keep captions short, no hashtag spam, no dangerous instructions, no repeated generic templates. JSON only."""

SUPPORTED = {"cloud","rocket","planet","phone","brain","heart","flower","robot","book","lightbulb","atom","plant","star","camera","water_drop","gear","magnet","globe","cube","sphere","cone","cylinder","torus"}
EMOTIONS = {"curious","happy","worried","surprised","determined","relieved"}


def call_local_model(model_path: Path, candidates: list[dict], retry_feedback: str = "") -> dict:
    if not model_path.is_file() or model_path.stat().st_size < 100_000_000:
        raise RuntimeError(f"Local model not found or unexpectedly small: {model_path}")
    try:
        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError("llama-cpp-python is not installed; no API or paid fallback will be attempted.") from exc

    brief = {
        "current_candidate_topics": [
            {"title": str(x.get("title", ""))[:220], "source": str(x.get("source", ""))[:100],
             "url": str(x.get("url", ""))[:500], "summary": str(x.get("summary", ""))[:450]}
            for x in candidates[:14]
        ],
        "quality_feedback_from_previous_attempt": retry_feedback[:1800],
        "request": "Choose the most engaging appropriate topic based on the feed evidence, then create one original 20-55 second English animated short plan. Do not state that a trend is viral unless the feed supports it. Each scene must have purposeful visual movement and narration that advances the story."
    }
    llm = Llama(model_path=str(model_path), n_ctx=8192, n_threads=max(1, int(os.environ.get("LOCAL_LLM_THREADS", "2"))), verbose=False)
    response = llm.create_chat_completion(
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(brief, ensure_ascii=False)}],
        temperature=0.75,
        max_tokens=2600,
        response_format={"type": "json_object"},
    )
    content = response["choices"][0]["message"].get("content", "")
    text = str(content or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
        raise RuntimeError("Local model returned invalid JSON; refusing to render an unchecked plan.") from exc


def validate(plan: dict, topic_candidates: list[dict]) -> dict:
    required = ["title", "description", "topic", "hook", "duration_seconds", "tags", "scenes"]
    missing = [key for key in required if key not in plan]
    if missing:
        raise ValueError(f"Plan missing fields: {missing}")
    plan["title"] = str(plan["title"]).strip()[:95]
    plan["description"] = str(plan["description"]).strip()[:4000]
    duration = int(plan["duration_seconds"])
    if not 20 <= duration <= 55:
        raise ValueError("duration_seconds must be 20..55")
    scenes = plan["scenes"]
    if not isinstance(scenes, list) or not 5 <= len(scenes) <= 8:
        raise ValueError("scenes must contain 5..8 scenes")
    for i, scene in enumerate(scenes):
        for key in ("narration", "caption", "visual", "companion", "action", "emotion"):
            if key not in scene:
                raise ValueError(f"Scene {i+1} missing {key}")
        scene["visual"] = str(scene["visual"]).lower().strip()
        scene["companion"] = str(scene["companion"]).lower().strip()
        if scene["visual"] not in SUPPORTED or scene["companion"] not in SUPPORTED:
            raise ValueError(f"Scene {i+1} uses an unsupported visual type")
        scene["caption"] = str(scene["caption"]).strip()[:34]
        scene["narration"] = str(scene["narration"]).strip()
        scene["emotion"] = str(scene["emotion"]).lower().strip()
        if scene["emotion"] not in EMOTIONS:
            scene["emotion"] = "curious"
        scene["action"] = str(scene["action"]).strip()[:220]
    plan["tags"] = [str(x).strip().lstrip("#")[:30] for x in plan.get("tags", []) if str(x).strip()][:8]
    plan["source_candidates"] = [{"title":x.get("title", ""), "url":x.get("url", ""), "source":x.get("source", "")} for x in topic_candidates[:8]]
    plan["generator"] = "Qwen2.5-1.5B-Instruct local GGUF (CPU; no API key)"
    return plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trends", default="work/trends.json")
    ap.add_argument("--out", default="work/plan.json")
    ap.add_argument("--feedback", default="")
    ap.add_argument("--model", default=os.environ.get("LOCAL_LLM_MODEL", "models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"))
    args = ap.parse_args()
    try:
        data = json.loads(Path(args.trends).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: Could not read trend candidates: {exc}", file=sys.stderr)
        return 2
    candidates = data.get("items", [])
    if not candidates:
        print("ERROR: No trend candidates were discovered. No topic was fabricated.", file=sys.stderr)
        return 3
    try:
        plan = validate(call_local_model(Path(args.model), candidates, args.feedback), candidates)
    except Exception as exc:
        print(f"ERROR: {exc}. No paid API fallback was attempted.", file=sys.stderr)
        return 4
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Story plan ready: {plan['title']} ({len(plan['scenes'])} scenes, {plan['duration_seconds']}s)")
    print("Generator: local open model; no API key or paid inference used.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
