#!/usr/bin/env python3
"""Draw the real GitHub contribution history over the static hero base image,
matching the rendered mockup's dense square-cell activity band, then upscale
to assets/hero.png.

The mockup band is a 5-row x ~93-col grid of ~14px square cells (measured from
src/art/hero_base.png: red grid spans x70..1382, y734..804, pitch ~14px). We
flatten the real GitHub calendar (src/data.json: 53 weeks x 7 day levels 0-4)
into a chronological day list and tile it column-major into that grid, newest
at the bottom-right exactly like GitHub. Cells stay square so the boxes are
even.
"""
import json
from PIL import Image, ImageDraw

BASE = "src/art/hero_base.png"
OUT  = "assets/hero.png"

# Grid geometry measured from the mockup band (square cells).
X0, Y0 = 70, 734          # top-left of the grid
PITCH  = 14.0             # same pitch both axes -> square cells
COLS, ROWS = 93, 5        # 93 columns x 5 rows = 465 cells
GAP    = 3.0              # px gap between cells
RADIUS = 2
OUT_W  = 1800

PAL = [(62, 11, 20), (114, 17, 27), (164, 27, 35), (216, 46, 53), (255, 83, 91)]


def load_days():
    """Return a chronological list of levels (0-4), oldest first."""
    try:
        cal = json.load(open("src/data.json")).get("calendar") or []
    except Exception:
        return []
    days = []
    for week in cal:              # weeks oldest->newest, each day Sun..Sat
        for lvl in week[:7]:
            days.append(min(4, max(0, int(lvl))))
    return days


def sample_bg(im):
    """Dark gap colour just left of the grid, for blanking the old cells."""
    px = [im.getpixel((X0 - 4, int(Y0 + r * PITCH + PITCH / 2))) for r in range(ROWS)]
    return min(px, key=lambda p: p[0] + p[1] + p[2])


def main():
    im = Image.open(BASE).convert("RGB")
    d = ImageDraw.Draw(im)
    days = load_days()

    if days:
        cap = COLS * ROWS
        days = days[-cap:]                       # most recent cap days
        cells = [0] * (cap - len(days)) + days   # oldest cells blank

        bg = sample_bg(im)
        # blank the exact grid rectangle before redrawing
        d.rectangle([X0 - 2, Y0 - 2,
                     X0 + COLS * PITCH, Y0 + ROWS * PITCH], fill=bg)

        cs = PITCH - GAP                         # square cell side
        for i, lvl in enumerate(cells):
            col, row = divmod(i, ROWS)           # column-major, newest last
            x = X0 + col * PITCH
            y = Y0 + row * PITCH
            d.rounded_rectangle([x, y, x + cs, y + cs],
                                radius=RADIUS, fill=PAL[lvl])

    im.resize((OUT_W, round(im.height * OUT_W / im.width)),
              Image.LANCZOS).save(OUT)


if __name__ == "__main__":
    main()
