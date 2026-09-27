#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
════════════════════════════════════════════════════════════════
  LOCAL RANK AGENT — Syed Numan Ali Shah (Lahore)  [SERPER edition]
════════════════════════════════════════════════════════════════
  Har run par:
   1. Google LOCAL PACK (Pakistan) par target keywords track karta hai
   2. Aap ki position, rating, review count nikalta hai
   3. Rank girawat / nayi reviews / naya competitor = ALERTS
   4. history.csv + report.txt (WhatsApp-forward ready) banata hai
  GitHub Actions par roz 10:00 PKT khud chalta hai.
════════════════════════════════════════════════════════════════
"""
import csv
import json
import os
import sys
import datetime

try:
    import requests
except ImportError:
    sys.exit("PEHLE install karein:  pip install requests")

# ═══════════════════════ CONFIG ═══════════════════════
SERPER_KEY = os.environ.get("SERPER_KEY", "")
COUNTRY = "pk"

# (keyword, frequency)  frequency: "daily" | "weekly"
KEYWORDS = [
    ("astrologer in lahore",   "daily"),    # main battle
    ("zaiqa wala lahore",      "daily"),    # low-mid competition
    ("istikhara lahore",       "daily"),    # low-mid competition
    ("baba numan ali shah",    "weekly"),   # BRAND — hamesha #1 hona chahiye
    ("kangna lahore",          "weekly"),
    ("numerologist lahore",    "weekly"),
]

# Aap ka profile — in fragments me se koi match hua = aap
OUR_NAME = ["numan ali shah", "numanali", "aamil baba numan", "numan ali"]

ALERT_RATING = 3
STATE_FILE = os.path.join(os.path.dirname(__file__), "agent_state.json")
CSV_FILE   = os.path.join(os.path.dirname(__file__), "history.csv")
REPORT_FILE= os.path.join(os.path.dirname(__file__), "report.txt")
# ══════════════════════════════════════════════════════

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, ensure_ascii=False, indent=1, fp=f)

def is_ours(name):
    n = (name or "").lower()
    return any(frag in n for frag in OUR_NAME)

def search_local(keyword):
    """Google local pack (Serper /places) — Pakistan region."""
    r = requests.post(
        "https://google.serper.dev/places",
        headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
        json={"q": keyword, "gl": COUNTRY},
        timeout=45,
    )
    r.raise_for_status()
    data = r.json()
    out = []
    for item in (data.get("places") or [])[:7]:
        out.append({
            "name": item.get("title"),
            "rating": item.get("rating"),
            "reviews": item.get("ratingCount"),
            "position": item.get("position"),
        })
    return out

def fmt_pos(p):
    return str(p) if p else "not-found"

def main():
    today = datetime.date.today()
    state = load_state()
    alerts = []
    lines  = []
    new_rows = []

    for keyword, freq in KEYWORDS:
        prev = state.get(keyword, {})
        last = prev.get("last_run")
        if last:
            gap = (today - datetime.date.fromisoformat(last)).days
            if freq == "weekly" and gap < 7:
                continue
        try:
            results = search_local(keyword)
        except Exception as e:
            alerts.append(f"⚠️ '{keyword}' search fail hui: {e}")
            continue

        ours = next((x for x in results if is_ours(x["name"])), None)
        top3 = [x for x in results if x["position"] in (1, 2, 3)]

        if ours:
            pos, rating, reviews = ours["position"], ours["rating"], ours["reviews"]
            if prev.get("last_position") and pos and prev["last_position"] <= 3 and pos > 3:
                alerts.append(f"📉 '{keyword}': rank gira #{prev['last_position']} → #{pos} — is hafte 1 post + 2 reviews ka focus")
            if prev.get("last_reviews") is not None and reviews and reviews > prev["last_reviews"]:
                new_reviews = reviews - prev["last_reviews"]
                lines.append(f"🆕 '{keyword}': {new_reviews} nayi review shamil — total {reviews}, rating {rating}★")
                if rating is not None and rating < 4.5:
                    alerts.append(f"🔴 Rating {rating}★ — nayi reviews ko 24h mein reply karein")
            if keyword == "baba numan ali shah" and pos != 1:
                alerts.append(f"🔴 BRAND search par aap #1 nahi hain (#{fmt_pos(pos)}) — turant check karein")
        else:
            if prev.get("last_position"):
                alerts.append(f"🔴 '{keyword}': top-7 mein aap ABHI NAHI hain (pehle #{prev.get('last_position')}) — aaj 1 naya post + 3 review requests")
            else:
                lines.append(f"⚪ '{keyword}': abhi top-7 mein nahi — normal hai, velocity banao")

        top3_names = ", ".join((x["name"] or "")[:30] for x in top3) or "—"
        prev_top3 = set(prev.get("top3", []))
        if prev_top3:
            for x in top3:
                if x["name"] and x["name"] not in prev_top3 and not is_ours(x["name"]):
                    alerts.append(f"👀 Naya competitor top-3 mein: '{x['name']}' ('{keyword}' #{x['position']})")

        row = {
            "date": today.isoformat(),
            "keyword": keyword,
            "our_position": fmt_pos(ours["position"]) if ours else "not-found",
            "our_rating": ours["rating"] if ours else "",
            "our_reviews": ours["reviews"] if ours else "",
            "top1": top3[0]["name"] if len(top3) > 0 else "",
            "top2": top3[1]["name"] if len(top3) > 1 else "",
            "top3": top3[2]["name"] if len(top3) > 2 else "",
            "top3_names": top3_names,
        }
        new_rows.append(row)
        state[keyword] = {
            "last_run": today.isoformat(),
            "last_position": ours["position"] if ours else None,
            "last_rating": ours["rating"] if ours else None,
            "last_reviews": ours["reviews"] if ours else None,
            "top3": [x["name"] for x in top3 if x["name"]],
        }

    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(new_rows[0].keys()) if new_rows else
                           ["date","keyword","our_position","our_rating","our_reviews","top1","top2","top3","top3_names"])
        if write_header:
            w.writeheader()
        w.writerows(new_rows)

    save_state(state)

    rep = []
    rep.append("📊 LOCAL RANK AGENT — REPORT")
    rep.append(f"📅 {today.strftime('%d %b %Y')}")
    rep.append("─" * 40)
    for keyword, freq in KEYWORDS:
        s = state.get(keyword)
        if not s or s.get("last_run") != today.isoformat():
            continue
        if s.get("last_position"):
            rep.append(f"📍 {keyword}: #{s['last_position']}  |  {s.get('last_rating')}★  |  {s.get('last_reviews')} reviews")
        else:
            rep.append(f"📍 {keyword}: top-7 mein abhi nahi")
    for ln in lines:
        rep.append(ln)
    rep.append("─" * 40)
    if alerts:
        rep.append("⚡ ACTIONS:")
        rep.extend(alerts)
    else:
        rep.append("✅ Sab theek — rank stable, naya alert nahi.")
    rep.append("─" * 40)
    rep.append("Aaj ka kaam: 2-3 review requests bhejein + naya review ka reply + 10 min activity.")

    report_text = "\n".join(rep)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text + "\n")

    print(report_text)
    print(f"\n[saved] {REPORT_FILE}\n[saved] {CSV_FILE}")

if __name__ == "__main__":
    if not SERPER_KEY:
        sys.exit("SERPER_KEY env var set karein.")
    main()
