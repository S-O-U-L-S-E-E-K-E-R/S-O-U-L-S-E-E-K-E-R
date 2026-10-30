#!/usr/bin/env python3
"""Export a compact ShadowLens news-intel summary for the public profile panel.

Runs on the LAPTOP (where ShadowLens backend lives, http://localhost:8001).
Reads the already-coded news feed (CAMEO/GDELT output) and writes a small,
publish-safe summary to src/shadowlens.json. It only reads the backend's
public-news-derived output; it does NOT touch intel_patterns.py or any
collection internals. Coordinates are intentionally dropped.

Usage:  python3 scripts/shadowlens_export.py
Env:    SL_URL (default http://localhost:8001/api/live-data), SL_TICKER (default 8)
"""
import json, os, sys, urllib.request, pathlib, datetime, html

URL = os.environ.get("SL_URL", "http://localhost:8001/api/live-data")
N = int(os.environ.get("SL_TICKER", "8"))
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "shadowlens.json"
TICKER_SVG = ROOT / "assets" / "ticker.svg"


def write_ticker(ranked):
    """Self-hosted animated scrolling news ticker SVG (replaces the external
    typing-svg). Scrolls 'ESTABLISHING SECURE LINK' + live headlines."""
    items = []
    for n in ranked[:14]:
        ev = n.get("event") or {}
        a1 = ev.get("actor1_name") or ev.get("actor1")
        a2 = ev.get("actor2_name") or ev.get("actor2")
        dyad = f"{a1} → {a2}" if (a1 and a2) else (a1 or a2 or "")
        t = (n.get("title") or "").strip()
        if not t:
            continue
        pre = f"{dyad} — " if dyad else ""
        items.append((n.get("risk_score"), f"{pre}{t}", (n.get("source") or "").strip()))
    lead = "▸ ESTABLISHING SECURE LINK // SHADOWLENS LIVE FEED"
    gap = "  ◦  "
    # build tspans: lead (red) then each item (risk red, text cream)
    sp = [f'<tspan fill="#ff3a3f">{html.escape(lead)}</tspan>']
    approx = len(lead)
    for risk, text, src in items:
        chunk = f'{gap}'
        sp.append(f'<tspan fill="#3a3a3d">{html.escape(gap)}</tspan>')
        if risk is not None:
            sp.append(f'<tspan fill="#ff3a3f">[{risk}] </tspan>')
            approx += len(str(risk)) + 3
        tail = f"{text}" + (f"  ({src})" if src else "")
        sp.append(f'<tspan fill="#c9c6bf">{html.escape(tail)}</tspan>')
        approx += len(gap) + len(tail)
    char_w = 8.4            # ~ font-size 15 mono
    text_w = int(approx * char_w)
    vb_w = 1000
    travel = vb_w + text_w
    dur = max(30, round(travel / 70))   # px/sec
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{vb_w}" height="34" viewBox="0 0 {vb_w} 34" font-family="'JetBrains Mono','DejaVu Sans Mono',monospace">
  <rect width="{vb_w}" height="34" rx="6" fill="#0a0a0b" stroke="#2a1513"/>
  <rect x="0" y="0" width="3" height="34" fill="#e3252b"/>
  <text x="0" y="22" font-size="15" letter-spacing="0.5" xml:space="preserve">
    <animateTransform attributeName="transform" type="translate" from="{vb_w} 0" to="-{text_w} 0" dur="{dur}s" repeatCount="indefinite"/>
    {''.join(sp)}
  </text>
</svg>'''
    TICKER_SVG.parent.mkdir(parents=True, exist_ok=True)
    TICKER_SVG.write_text(svg)
    return len(items), dur

QUADS = ["material conflict", "verbal conflict", "verbal cooperation", "material cooperation"]


def trim(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def main():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "shadowlens-export"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except Exception as e:
        print(f"ShadowLens fetch failed ({e}); leaving existing file", file=sys.stderr)
        sys.exit(1)

    news = d.get("news", []) or []
    coded = [n for n in news if n.get("event")]
    outlets = set()
    for n in news:
        for o in ((n.get("corroboration") or {}).get("outlet_names") or []):
            outlets.add(o)

    quad_hist = {q: 0 for q in QUADS}
    label_hist = {}
    for n in coded:
        ev = n.get("event") or {}
        q = ev.get("quad")
        if q in quad_hist:
            quad_hist[q] += 1
        lab = ev.get("label")
        if lab:
            label_hist[lab] = label_hist.get(lab, 0) + 1
    top_labels = sorted(label_hist.items(), key=lambda kv: kv[1], reverse=True)[:5]

    # ticker: highest-risk stories (coords dropped)
    ranked = sorted(news, key=lambda n: (n.get("risk_score") or 0,
                                         (n.get("corroboration") or {}).get("outlets") or 0),
                    reverse=True)
    ticker = []
    for n in ranked[:N]:
        ev = n.get("event") or {}
        a1 = ev.get("actor1_name") or ev.get("actor1")
        a2 = ev.get("actor2_name") or ev.get("actor2")
        if a1 and a2:
            dyad = f"{a1} → {a2}"
        else:
            dyad = a1 or a2 or ""
        ticker.append({
            "title": trim(n.get("title"), 76),
            "source": trim(n.get("source"), 18),
            "risk": n.get("risk_score"),
            "dyad": trim(dyad, 30),
            "code": ev.get("code"),
            "label": trim(ev.get("label"), 30),
            "quad": ev.get("quad"),
            "goldstein": ev.get("goldstein"),
            "outlets": (n.get("corroboration") or {}).get("outlets"),
        })

    out = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "feed_time": d.get("last_updated"),
        "total": len(news),
        "coded": len(coded),
        "outlets": len(outlets),
        "quad_hist": quad_hist,
        "top_labels": [{"label": k, "n": v} for k, v in top_labels],
        "ticker": ticker,
    }
    OUT.write_text(json.dumps(out, indent=2))
    nit, dur = write_ticker(ranked)
    print(f"wrote {OUT} | total={out['total']} coded={out['coded']} outlets={out['outlets']} "
          f"ticker={len(ticker)} | ticker.svg items={nit} dur={dur}s")


if __name__ == "__main__":
    main()
