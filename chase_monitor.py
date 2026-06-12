#!/usr/bin/env python3
"""
Police Chase Monitor v2 — GitHub Actions versie
------------------------------------------------
Twee detectiemethodes:

1. KANAAL-WATCHLIST (elke run, kost GEEN API-quotum)
   Checkt voor een vaste lijst betrouwbare kanalen of ze live zijn door
   hun /live-pagina op te halen. Alert alleen als de streamtitel een
   chase-woord bevat. Hierdoor kan dit elke 5 minuten draaien.

2. BREDE API-ZOEKTOCHT (1x per uur, als vangnet)
   Vindt ook chases op kanalen buiten de watchlist. Resultaten gaan
   door een blacklist-filter tegen gaming/roleplay/compilatie-rommel.

Environment variables (GitHub repo Secrets):
  YOUTUBE_API_KEY  - YouTube Data API v3 key (alleen nodig voor methode 2)
  NTFY_TOPIC       - je ntfy.sh topic
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_SERVER = "https://ntfy.sh"
STATE_FILE = os.environ.get("STATE_FILE", "seen.json")

# ---------------------------------------------------------------------------
# 1. Watchlist: kanalen die echte chases live uitzenden (LA-zenders vooral).
#    Gebruik de @handle uit de kanaal-URL. Vrij uit te breiden — elke check
#    is gratis, dus meer kanalen kost niets.
# ---------------------------------------------------------------------------
WATCHLIST = [
    "@LiveNOWfromFOX",
    "@KTLA5",
    "@FOXLA",          # FOX 11 Los Angeles
    "@ABC7",           # ABC7 Los Angeles
    "@kcalnews",       # KCAL/CBS Los Angeles
    "@NBCLA",
]

# Woorden waarvan er minstens één in de titel moet zitten
KEYWORDS = ["chase", "pursuit", "standoff"]

# Titels met deze woorden worden ALTIJD genegeerd (gaming, roleplay, herhalingen)
BLACKLIST = [
    "gta", "fivem", "roleplay", " rp ", "gameplay", "simulator", "beamng",
    "lego", "minecraft", "compilation", "best of", "top 10", "top10",
    "caught on camera", "dashcam compilation", "asmr", "lofi", "music",
    "reaction", "react", "archive", "replay", "rewind",
]

# Brede API-zoektocht alleen in het eerste run-venster van elk uur
SEARCH_TERMS = ["police chase", "police pursuit"]
API_SEARCH_WINDOW_MINUTES = 6   # run met minuut 0-5 doet de API-zoektocht

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def load_seen() -> set:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen: set) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen)[-500:], f)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
def title_ok(title: str) -> bool:
    lower = f" {title.lower()} "
    if not any(k in lower for k in KEYWORDS):
        return False
    if any(b in lower for b in BLACKLIST):
        return False
    return True


# ---------------------------------------------------------------------------
# Methode 1: watchlist-check zonder API-quotum
# ---------------------------------------------------------------------------
def check_channel_live(handle: str):
    """Haalt youtube.com/<handle>/live op. Retourneert stream-dict of None."""
    url = f"https://www.youtube.com/{handle}/live"
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    # Alleen doorgaan als de stream NU live is
    if '"isLiveNow":true' not in html:
        return None

    vid_match = re.search(r'rel="canonical" href="https://www\.youtube\.com/watch\?v=([\w-]{11})"', html)
    title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    if not vid_match or not title_match:
        return None

    title = title_match.group(1).replace(" - YouTube", "").strip()
    return {
        "id": vid_match.group(1),
        "title": title,
        "channel": handle,
        "url": f"https://www.youtube.com/watch?v={vid_match.group(1)}",
    }


# ---------------------------------------------------------------------------
# Methode 2: brede API-zoektocht (vangnet, 1x per uur)
# ---------------------------------------------------------------------------
def search_live_streams(query: str) -> list:
    params = urllib.parse.urlencode({
        "part": "snippet", "q": query, "type": "video", "eventType": "live",
        "order": "date", "maxResults": 10, "relevanceLanguage": "en",
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


# ---------------------------------------------------------------------------
# Notificatie
# ---------------------------------------------------------------------------
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


def alert_if_new(stream: dict, seen: set) -> int:
    if stream["id"] in seen or not title_ok(stream["title"]):
        return 0
    print(f"[ALERT] {stream['title']} — {stream['url']}")
    try:
        send_ntfy_alert(stream)
    except Exception as e:
        print(f"[fout] ntfy-melding versturen mislukt: {e}")
        return 0
    seen.add(stream["id"])
    return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    if not NTFY_TOPIC:
        print("FOUT: zet NTFY_TOPIC als environment variable (repo Secret).")
        return 1

    seen = load_seen()
    alerts = 0

    # Methode 1: watchlist (gratis, elke run)
    for handle in WATCHLIST:
        try:
            stream = check_channel_live(handle)
        except Exception as e:
            print(f"[fout] check van {handle} mislukt: {e}")
            continue
        if stream:
            print(f"[live] {handle}: {stream['title']}")
            alerts += alert_if_new(stream, seen)
        else:
            print(f"[idle] {handle} is niet live (of titel onbekend)")

    # Methode 2: API-zoektocht, alleen in het eerste venster van elk uur
    minute = datetime.now(timezone.utc).minute
    if YOUTUBE_API_KEY and minute < API_SEARCH_WINDOW_MINUTES:
        print("[info] uurlijkse brede API-zoektocht...")
        for term in SEARCH_TERMS:
            try:
                for stream in search_live_streams(term):
                    alerts += alert_if_new(stream, seen)
            except Exception as e:
                print(f"[fout] zoeken naar '{term}' mislukt: {e}")

    save_seen(seen)
    print(f"Klaar: {alerts} nieuwe alert(s), {len(seen)} streams in geschiedenis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
