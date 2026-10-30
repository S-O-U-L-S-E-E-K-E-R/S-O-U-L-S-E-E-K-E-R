#!/usr/bin/env python3
"""Fetch live profile data (repo activity + contribution calendar) -> src/data.json.

Auth: uses $PROFILE_TOKEN if set (can read private repos), else $GITHUB_TOKEN
(public only). Degrades gracefully: any field that can't be read is left null and
the renderer falls back to a safe default, so the Action never hard-fails.
"""
import json, os, sys, urllib.request, urllib.error, datetime, pathlib

USER = "S-O-U-L-S-E-E-K-E-R"
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
OUT = pathlib.Path(__file__).resolve().parent.parent / "src" / "data.json"

# Dossier cards -> backing repo. `classified` hides code (no link) but still
# shows live activity. Non-classified cards link out.
CARDS = [
    {"id": "01", "title": "STORM",         "repo": "custom-signal-hunter-app", "classified": True,  "role": "C-UAS GRID",  "lang": "Python", "lc": "#3b7dd8", "art": "grid"},
    {"id": "02", "title": "SIGNAL FINDER", "repo": "Signal-Finder",            "classified": False, "role": "SPECTRUM",    "lang": "Python", "lc": "#3b7dd8", "art": "wave"},
    {"id": "03", "title": "PHANTOM DRONE", "repo": "phantom-drone-app",        "classified": True,  "role": "RF DECOY",    "lang": "C++",    "lc": "#f2c94c", "art": "net"},
    {"id": "04", "title": "SHADOWLENS",    "repo": "ShadowLens",               "classified": True,  "role": "OSINT",       "lang": "Python", "lc": "#3b7dd8", "art": "stack"},
]
DESC = {
    "STORM": "Distributed C-UAS sensor grid for multi-node RF detection and direction-finding.",
    "SIGNAL FINDER": "Spectrum recon: hunt, classify and chase down unknown emitters.",
    "PHANTOM DRONE": "HackRF RF decoy that synthesizes real drone signatures for EW training.",
    "SHADOWLENS": "OSINT news intel: CAMEO event coding, GDELT indexing, story clustering.",
}


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "soulseeker-profile"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def status_from_push(iso):
    if not iso:
        return "STANDBY"
    d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    age = (datetime.datetime.now(datetime.timezone.utc) - d).days
    if age <= 21:
        return "ACTIVE"
    if age <= 90:
        return "RECENT"
    return "DORMANT"


def main():
    if not TOKEN:
        print("no token available", file=sys.stderr)
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).isoformat()

    # One GraphQL call: per-repo stats (aliased) + contribution calendar.
    parts = []
    for i, c in enumerate(CARDS):
        parts.append(f'''
        r{i}: repository(owner: "{USER}", name: "{c['repo']}") {{
          stargazerCount
          pushedAt
          defaultBranchRef {{ target {{ ... on Commit {{ history(since: "{since}") {{ totalCount }} }} }} }}
        }}''')
    query = f'''query {{
      user(login: "{USER}") {{
        followers {{ totalCount }}
        contributionsCollection {{
          contributionCalendar {{
            totalContributions
            weeks {{ contributionDays {{ contributionCount weekday date }} }}
          }}
        }}
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {{
          nodes {{
            languages(first: 8, orderBy: {{field: SIZE, direction: DESC}}) {{
              edges {{ size node {{ name color }} }}
            }}
          }}
        }}
      }}
      {''.join(parts)}
    }}'''

    # Load prior data so a token WITHOUT private access preserves good values
    # instead of nulling them out.
    prior = {}
    try:
        prev = json.loads(OUT.read_text())
        prior = {c["title"]: c for c in prev.get("cards", [])}
        prior["__cal__"] = prev.get("calendar", [])
        prior["__flw__"] = prev.get("followers")
        prior["__lang__"] = prev.get("langs", [])
        prior["__tot__"] = prev.get("totals", {})
    except Exception:
        pass

    data = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "cards": [], "calendar": [], "followers": None,
            "langs": [], "totals": {}}
    try:
        res = gql(query)
        d = res.get("data") or {}
        errs = res.get("errors")
        if errs:
            print("graphql errors:", json.dumps(errs)[:400], file=sys.stderr)
        u = d.get("user") or {}
        data["followers"] = (u.get("followers") or {}).get("totalCount")
        if data["followers"] is None:
            data["followers"] = prior.get("__flw__")
        # calendar -> list of weeks, each 7 ints (level 0..4 by magnitude)
        ccal = ((u.get("contributionsCollection") or {}).get("contributionCalendar")) or {}
        cal = ccal.get("weeks") or []
        allc = [day["contributionCount"] for w in cal for day in w["contributionDays"]]
        mx = max(allc) if allc else 0
        def lvl(n):
            if n <= 0 or mx == 0: return 0
            q = n / mx
            return 1 + min(3, int(q * 4))  # 1..4
        for w in cal:
            col = [0] * 7
            for day in w["contributionDays"]:
                col[day["weekday"]] = lvl(day["contributionCount"])
            data["calendar"].append(col)
        if not data["calendar"]:
            data["calendar"] = prior.get("__cal__", [])

        # totals + streaks from ordered days
        days = sorted(({"date": day["date"], "n": day["contributionCount"]}
                       for w in cal for day in w["contributionDays"]), key=lambda x: x["date"])
        total = ccal.get("totalContributions")
        cur = longest = run = 0
        for day in days:
            if day["n"] > 0:
                run += 1; longest = max(longest, run)
            else:
                run = 0
        # current streak: walk backwards; allow today to be 0 (not over yet)
        for i, day in enumerate(reversed(days)):
            if day["n"] > 0:
                cur += 1
            elif i == 0:
                continue  # today still open
            else:
                break
        since = days[0]["date"] if days else None
        if total is not None:
            data["totals"] = {"contributions": total, "current": cur, "longest": longest, "since": since}
        else:
            data["totals"] = prior.get("__tot__", {})

        # language mix across all owned non-fork repos
        repos = ((u.get("repositories") or {}).get("nodes")) or []
        agg = {}
        for rp in repos:
            for e in ((rp.get("languages") or {}).get("edges") or []):
                nm = e["node"]["name"]
                if nm not in agg:
                    agg[nm] = {"size": 0, "color": e["node"].get("color") or "#888"}
                agg[nm]["size"] += e.get("size", 0)
        tot_sz = sum(v["size"] for v in agg.values()) or 1
        top = sorted(agg.items(), key=lambda kv: kv[1]["size"], reverse=True)[:6]
        if top:
            data["langs"] = [{"name": k, "pct": round(v["size"] * 100.0 / tot_sz, 1),
                              "color": v["color"]} for k, v in top]
        else:
            data["langs"] = prior.get("__lang__", [])
        # cards — reuse prior stats when this token can't read the repo
        for i, c in enumerate(CARDS):
            r = d.get(f"r{i}")
            p = prior.get(c["title"], {})
            if not r:  # null node = no access with this token
                stars, push, com = p.get("stars"), p.get("pushedAt"), p.get("commits30")
            else:
                hist = (((r.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {})
                stars = r.get("stargazerCount") if r.get("stargazerCount") is not None else p.get("stars")
                push = r.get("pushedAt") or p.get("pushedAt")
                com = hist.get("totalCount") if hist.get("totalCount") is not None else p.get("commits30")
            card = {"id": c["id"], "title": c["title"], "role": c["role"], "lang": c["lang"],
                    "lc": c["lc"], "art": c["art"], "classified": c["classified"],
                    "desc": DESC[c["title"]],
                    "stars": stars, "pushedAt": push, "commits30": com,
                    "status": status_from_push(push) if push else (p.get("status") or "STANDBY"),
                    "url": None if c["classified"] else f"https://github.com/{USER}/{c['repo']}"}
            data["cards"].append(card)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print("fetch failed, preserving prior stats:", e, file=sys.stderr)
        data["calendar"] = prior.get("__cal__", [])
        data["followers"] = prior.get("__flw__")
        data["langs"] = prior.get("__lang__", [])
        data["totals"] = prior.get("__tot__", {})
        for c in CARDS:
            p = prior.get(c["title"], {})
            data["cards"].append({"id": c["id"], "title": c["title"], "role": c["role"],
                                  "lang": c["lang"], "lc": c["lc"], "art": c["art"],
                                  "classified": c["classified"], "desc": DESC[c["title"]],
                                  "stars": p.get("stars"), "pushedAt": p.get("pushedAt"),
                                  "commits30": p.get("commits30"),
                                  "status": p.get("status") or "STANDBY",
                                  "url": None if c["classified"] else f"https://github.com/{USER}/{c['repo']}"})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2))
    print(f"wrote {OUT} | cards={len(data['cards'])} weeks={len(data['calendar'])} "
          f"followers={data['followers']} langs={len(data['langs'])} totals={data['totals']}")


if __name__ == "__main__":
    main()
