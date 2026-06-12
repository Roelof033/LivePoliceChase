#!/usr/bin/env python3
"""
Police Chase Monitor — GitHub Actions versie
--------------------------------------------
Draait één keer per aanroep (GitHub Actions start hem elke 30 min via cron),
zoekt naar live police chase streams op YouTube en stuurt een pushmelding
via ntfy.sh bij nieuwe streams.

Configuratie gaat via environment variables (in GitHub: repo Secrets):
  YOUTUBE_API_KEY  - je YouTube Data API v3 key
  NTFY_TOPIC       - je ntfy.sh topic
"""

import json
import os
import sys
import urllib.parse
import urllib.request

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_SERVER = "https://ntfy.sh"

# Elke zoekterm kost 100 quota-eenheden per run (10.000/dag beschikbaar).
# 2 termen x 48 runs/dag = 9.600 -> net binnen het quotum.
SEARCH_TERMS = [
    "police chase",
    "police pursuit",
]

# Alleen alerts als de titel een van deze woorden bevat (lowercase)
TITLE_MUST_CONTAIN_ANY = ["chase", "pursuit"]

# Statebestand staat in de repo zelf en wordt na elke run teruggecommit
STATE_FILE = os.environ.get("STATE_FILE", "seen.json")


def load_seen() -> set:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen: set) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen)[-500:], f)


def search_live_streams(query: str) -> list:
    params = urllib.parse.urlencode({
        "part": "snippet",
        "q": query,
        "type": "video",
        "eventType": "live",
        "order": "date",
        "maxResults": 10,
        "relevanceLanguage": "en",
        "key": YOUTUBE_API_KEY,
    })
    url = f"https://www.googleapis.com/youtube/v3/search?{params}"
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = json.load(resp)

    results = []
    for item in data.get("items", []):
        video_id = item["id"].get("videoId")
        if not video_id:
            continue
        snippet = item["snippet"]
        results.append({
            "id": video_id,
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })
    return results


def title_matches(title: str) -> bool:
    if not TITLE_MUST_CONTAIN_ANY:
        return True
    lower = title.lower()
    return any(word in lower for word in TITLE_MUST_CONTAIN_ANY)


def send_ntfy_alert(stream: dict) -> None:
    req = urllib.request.Request(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=f"{stream['title']}\nKanaal: {stream['channel']}".encode("utf-8"),
        headers={
            "Title": "LIVE police chase!",
            "Priority": "high",
            "Tags": "rotating_light,police_car",
            "Click": stream["url"],
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20):
        pass


def main() -> int:
    if not YOUTUBE_API_KEY or not NTFY_TOPIC:
        print("FOUT: zet YOUTUBE_API_KEY en NTFY_TOPIC als environment "
              "variables (GitHub repo Secrets).")
        return 1

    seen = load_seen()
    alerts = 0

    for term in SEARCH_TERMS:
        try:
            streams = search_live_streams(term)
        except Exception as e:
            print(f"[fout] zoeken naar '{term}' mislukt: {e}")
            continue

        for stream in streams:
            if stream["id"] in seen or not title_matches(stream["title"]):
                continue
            print(f"[ALERT] {stream['title']} — {stream['url']}")
            try:
                send_ntfy_alert(stream)
                alerts += 1
            except Exception as e:
                print(f"[fout] ntfy-melding versturen mislukt: {e}")
            seen.add(stream["id"])

    save_seen(seen)
    print(f"Klaar: {alerts} nieuwe alert(s) verstuurd, "
          f"{len(seen)} streams in geschiedenis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
