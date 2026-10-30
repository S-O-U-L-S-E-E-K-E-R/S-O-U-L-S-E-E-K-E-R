#!/bin/bash
# usage: render.sh <html> <out.png> [w] [h] [scale]
cd "$(dirname "$0")"
timeout 120 /opt/google/chrome/chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --allow-file-access-from-files --force-device-scale-factor=${5:-2} --virtual-time-budget=15000 \
  --window-size=${3:-1300},${4:-842} --screenshot="$2" "file://$(dirname "$0")/$1" 2>&1 | grep -iE "written|Uncaught|ERROR:.*console" | grep -v nss_util
