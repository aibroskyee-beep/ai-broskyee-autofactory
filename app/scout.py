#!/usr/bin/env python3
"""Free public-RSS trend scout. Uses no API key, scraping login walls, or paid service."""
from __future__ import annotations
import argparse, json, re, sys, time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from pathlib import Path

FEEDS = [
    ("Google Trends US", "https://trends.google.com/trending/rss?geo=US", 1.35),
    ("Google Trends India", "https://trends.google.com/trending/rss?geo=IN", 1.30),
    ("Google Trends UK", "https://trends.google.com/trending/rss?geo=GB", 0.95),
    ("Google News US", "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en", 1.0),
    ("Google News Science", "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en", 1.15),
    ("Google News Technology", "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en", 1.10),
]
BAD = re.compile(r"\b(gore|graphic injury|suicide method|terror attack footage|pornographic)\b", re.I)

def read_feed(name: str, url: str, weight: float) -> list[dict]:
    req = Request(url, headers={"User-Agent": "AI-Broskyee-AutoFactory/1.0 (RSS reader)"})
    with urlopen(req, timeout=18) as resp:
        raw = resp.read(2_500_000)
    root = ET.fromstring(raw)
    rows = []
    for item in root.findall(".//item")[:40]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        desc = re.sub("<[^>]+>", " ", item.findtext("description") or "")
        desc = re.sub(r"\s+", " ", desc).strip()[:500]
        if not title or not link or BAD.search(title):
            continue
        rows.append({"title": title, "url": link, "source": name, "published": pub, "summary": desc, "source_weight": weight})
    return rows

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="work/trends.json")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()
    all_rows, errors = [], []
    for name, url, weight in FEEDS:
        try:
            rows = read_feed(name, url, weight)
            all_rows.extend(rows)
            print(f"OK {name}: {len(rows)} items")
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            print(f"WARN {name}: unavailable ({type(exc).__name__})")
    # Deduplicate on normalized title, with a small preference for Trends and science/tech.
    by_title = {}
    for item in all_rows:
        key = re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
        if key not in by_title or item["source_weight"] > by_title[key]["source_weight"]:
            by_title[key] = item
    rows = list(by_title.values())
    if not rows:
        print("ERROR: All free RSS feeds failed. No topic was fabricated.", file=sys.stderr)
        return 2
    rows.sort(key=lambda x: (x["source_weight"], len(x["title"])), reverse=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "feeds_checked": len(FEEDS), "feed_errors": errors, "items": rows[:max(1, min(args.limit, 50))]}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(payload['items'])} candidate topics to {out}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
