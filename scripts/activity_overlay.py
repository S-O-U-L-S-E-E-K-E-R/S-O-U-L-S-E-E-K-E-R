#!/usr/bin/env python3
"""Draw the real GitHub contribution matrix over the static hero base image,
matching the rendered mockup's dense cell style, then upscale to assets/hero.png.
Reads src/data.json (calendar: 53 weeks x 7 levels 0-4) and src/art/hero_base.png.
"""
import json, sys
from PIL import Image, ImageDraw

BASE = "src/art/hero_base.png"
OUT  = "assets/hero.png"
# matrix region in the base crop (measured), 53 cols x 7 rows
X0, X1, Y0, Y1 = 80, 1349, 734, 788
PAL = [(62,11,20),(114,17,27),(164,27,35),(216,46,53),(255,83,91)]

def main():
    im = Image.open(BASE).convert("RGB"); d = ImageDraw.Draw(im)
    try:
        cal = json.load(open("src/data.json")).get("calendar") or []
    except Exception:
        cal = []
    if not cal:
        im.resize((1800, round(im.height*1800/im.width)), Image.LANCZOS).save(OUT)
        return
    n = len(cal)
    bg = im.getpixel((700, Y0-10))
    d.rectangle([X0-5, Y0-3, X1+5, Y1+4], fill=bg)
    cp = (X1-X0)/n; cw = cp-2.6; rp = (Y1-Y0)/7; ch = rp-1.5
    for wi, week in enumerate(cal):
        for dd, lvl in enumerate(week[:7]):
            x = X0+wi*cp; y = Y0+dd*rp
            d.rounded_rectangle([x, y, x+cw, y+ch], radius=1.4, fill=PAL[min(4, max(0, int(lvl)))])
    im.resize((1800, round(im.height*1800/im.width)), Image.LANCZOS).save(OUT)

if __name__ == "__main__":
    main()
