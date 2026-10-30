#!/bin/bash
# usage: ./render.sh hero.html out.png 1300 1000 2  then: convert out.png -crop 2600x1684+0+0 +repage hero.png
cd "$(dirname "$0")"
timeout 120 /opt/google/chrome/chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --allow-file-access-from-files --force-device-scale-factor=${5:-2} --virtual-time-budget=15000 \
  --window-size=${3:-1300},${4:-842} --screenshot="$2" "file://$PWD/$1" 2>&1 | grep -iE "written|Uncaught|ERROR:.*console" | grep -v nss_util
