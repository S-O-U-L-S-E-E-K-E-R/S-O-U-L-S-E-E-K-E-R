#!/bin/bash
# Refresh the ShadowLens intel panel + news ticker on the public profile.
# Runs on the LAPTOP (needs the ShadowLens backend at :8001 and Chrome).
# Fetches live intel -> src/shadowlens.json + assets/ticker.svg, renders
# assets/shadowlens.png, commits and pushes. Safe to run on a cron/timer.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
CHROME="${CHROME:-/opt/google/chrome/chrome}"

# 1. pull live intel (writes src/shadowlens.json + assets/ticker.svg)
python3 scripts/shadowlens_export.py

# 2. render the panel PNG
"$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --allow-file-access-from-files --force-device-scale-factor=2 \
  --virtual-time-budget=15000 --window-size=1300,460 \
  --screenshot="$REPO/src/_sl.png" "file://$REPO/src/shadowlens.html"
convert "$REPO/src/_sl.png" -crop 2600x904+0+0 +repage "$REPO/assets/shadowlens.png"
rm -f "$REPO/src/_sl.png"

# 3. commit + push (rebase-retry against the CI bot)
git add src/shadowlens.json assets/shadowlens.png assets/ticker.svg
if git diff --cached --quiet; then echo "no changes"; exit 0; fi
git -c user.name="S-O-U-L-S-E-E-K-E-R" -c user.email="wdmitrijohn@gmail.com" \
  commit -q -m "chore: refresh shadowlens intel [skip ci]"
for i in 1 2 3; do
  if git pull --rebase -q origin main 2>/dev/null; then :; else
    git checkout --theirs assets/hero.png assets/telemetry.png src/data.json 2>/dev/null || true
    git add -A; GIT_EDITOR=true git rebase --continue >/dev/null 2>&1 || git rebase --abort || true
  fi
  if git push -q origin main 2>/dev/null; then echo "pushed (attempt $i)"; exit 0; fi
  sleep 3
done
echo "push failed after retries" >&2; exit 1
