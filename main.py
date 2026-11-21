#!/usr/bin/env python3
"""VELDORA - a travel poster for a place that does not exist.

Draws a 1024x1024 travel poster with the Python standard library only
(no PIL, no network) and writes it to /output/entry.png.

The place is invented: Veldora, an archipelago of floating terraces
where the waterfalls climb upward into a dusk sky, above a calm amber
sea. The program is fully deterministic: two runs write byte-identical
output (fixed palette, fixed geometry, fixed zlib settings, no time,
no randomness from the environment).
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
INK = (255, 240, 214)          # warm cream for the type
INK_SHADOW = (38, 18, 58)      # deep plum shadow behind the type
SKY_TOP = (24, 22, 62)
SKY_MID = (96, 56, 112)
SKY_LOW = (214, 110, 88)
SKY_HORIZON = (255, 178, 102)
SUN_CORE = (255, 232, 170)
SUN_GLOW = (255, 190, 110)
RIDGE_FAR = (74, 42, 96)
RIDGE_NEAR = (52, 30, 74)
ROCK_DARK = (58, 34, 66)
ROCK_LIT = (122, 74, 96)
TERRACE_TOP = (96, 140, 82)
TERRACE_TOP_LIT = (150, 178, 96)
WATERFALL = (196, 232, 240)
WATERFALL_DEEP = (140, 196, 214)
SEA_TOP = (22, 96, 100)
SEA_DEEP = (8, 42, 60)
SEA_SHIMMER = (255, 196, 120)
BOAT = (26, 18, 44)
BORDER = (255, 240, 214)


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self, w, h, color=(0, 0, 0)):
        self.w = w
        self.h = h
        self.px = bytearray(color * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def blend(self, x, y, color, alpha):
        """Blend color over the pixel with alpha in [0, 1]."""
        if 0 <= x < self.w and 0 <= y < self.h and alpha > 0.0:
            i = (y * self.w + x) * 3
            a = max(0.0, min(1.0, alpha))
            for c in range(3):
                old = self.px[i + c]
                self.px[i + c] = int(old + (color[c] - old) * a + 0.5)

    def fill_rect(self, x0, y0, x1, y1, color):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = bytes(color) * (x1 - x0)

    def vgrad(self, y0, y1, stops):
        """Vertical gradient; stops is a list of (pos 0..1, color)."""
        for y in range(y0, y1):
            t = (y - y0) / max(1, y1 - y0 - 1)
            c0 = stops[0][1]
            c1 = stops[-1][1]
            for k in range(len(stops) - 1):
                p0, col0 = stops[k]
                p1, col1 = stops[k + 1]
                if p0 <= t <= p1:
                    f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                    c0, c1 = col0, col1
                    t = f
                    break
            col = tuple(int(c0[i] + (c1[i] - c0[i]) * t + 0.5) for i in range(3))
            self.fill_rect(0, y, self.w, y + 1, col)

    def disc(self, cx, cy, r, color, alpha=1.0):
        r2 = r * r
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r2 - dy * dy)))
            for x in range(cx - dx, cx + dx + 1):
                if alpha >= 1.0:
                    self.set(x, y, color)
                else:
                    self.blend(x, y, color, alpha)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0):
        for y in range(cy - ry, cy + ry + 1):
            dy = (y - cy) / ry
            rem = 1.0 - dy * dy
            if rem < 0:
                continue
            dx = int(rx * math.sqrt(rem))
            for x in range(cx - dx, cx + dx + 1):
                if alpha >= 1.0:
                    self.set(x, y, color)
                else:
                    self.blend(x, y, color, alpha)

    def fill_poly(self, pts, color):
        """Scanline fill of a simple polygon (even-odd rule)."""
        ys = [p[1] for p in pts]
        y_min, y_max = max(0, min(ys)), min(self.h - 1, max(ys))
        n = len(pts)
        for y in range(y_min, y_max + 1):
            xs = []
            for k in range(n):
                x0, y0 = pts[k]
                x1, y1 = pts[(k + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, int(math.ceil(xs[k])))
                xb = min(self.w - 1, int(math.floor(xs[k + 1])))
                for x in range(xa, xb + 1):
                    self.set(x, y, color)

    def thick_line(self, x0, y0, x1, y1, width, color):
        """A line drawn as a filled rectangle strip (for birds, stems)."""
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length == 0:
            return
        nx, ny = -dy / length, dx / length
        hw = width / 2.0
        pts = [
            (int(x0 + nx * hw), int(y0 + ny * hw)),
            (int(x1 + nx * hw), int(y1 + ny * hw)),
            (int(x1 - nx * hw), int(y1 - ny * hw)),
            (int(x0 - nx * hw), int(y0 - ny * hw)),
        ]
        self.fill_poly(pts, color)


# ------------------------------------------------------------- bitmap font
# A hand-drawn 5x7 pixel font, one row per string, '#' = ink.
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
}


def text_width(text, scale):
    return len(text) * 5 * scale + max(0, len(text) - 1) * scale


def draw_text(cv, text, cx, y, scale, color, shadow=None):
    """Draw text centred on cx, top edge at y."""
    w = text_width(text, scale)
    x = cx - w // 2
    if shadow is not None:
        draw_text_raw(cv, text, x + scale, y + scale, scale, shadow)
    draw_text_raw(cv, text, x, y, scale, color)


def draw_text_raw(cv, text, x, y, scale, color):
    cx = x
    for ch in text:
        glyph = GLYPHS.get(ch.upper(), GLYPHS[" "])
        for row in range(7):
            for col in range(5):
                if glyph[row][col] == "1":
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 cx + (col + 1) * scale, y + (row + 1) * scale,
                                 color)
        cx += 6 * scale


# ------------------------------------------------------------------- scene
def draw_sky(cv):
    cv.vgrad(0, 660, [
        (0.00, SKY_TOP),
        (0.35, SKY_MID),
        (0.70, SKY_LOW),
        (1.00, SKY_HORIZON),
    ])
    # Stars: fixed positions from a tiny deterministic generator.
    seed = 123456789
    for _ in range(90):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        sx = seed % W
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        sy = seed % 300
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        bright = 0.35 + (seed % 100) / 100.0 * 0.65
        if sy < 300:
            cv.blend(sx, sy, (255, 244, 220), bright * 0.9)
            if seed % 7 == 0:
                cv.blend(sx + 1, sy, (255, 244, 220), bright * 0.5)


def draw_sun(cv):
    # Wide soft glow, then the disc, sitting in the clear gap between
    # the right terrace and the ridge so the whole disc shows.
    for r, a in ((240, 0.10), (185, 0.12), (140, 0.16), (112, 0.22)):
        cv.disc(700, 520, r, SUN_GLOW, a)
    cv.disc(700, 520, 80, SUN_CORE)
    cv.disc(700, 520, 64, (255, 242, 200))


def draw_clouds(cv):
    # Soft horizontal cloud bands catching the dusk light.
    bands = [
        (180, 300, 260, 26, (255, 170, 130), 0.35),
        (420, 330, 200, 20, (255, 190, 150), 0.30),
        (820, 260, 220, 22, (240, 150, 130), 0.30),
        (640, 350, 300, 24, (255, 180, 140), 0.28),
        (120, 420, 180, 18, (250, 160, 120), 0.25),
    ]
    for cx, cy, rx, ry, col, a in bands:
        cv.ellipse(cx, cy, rx, ry, col, a)
        cv.ellipse(cx + rx // 2, cy + 6, rx // 2, ry // 2, col, a * 0.8)


def draw_birds(cv):
    birds = [(300, 180), (350, 150), (560, 120), (620, 170), (880, 140)]
    for bx, by in birds:
        cv.thick_line(bx - 12, by, bx, by - 7, 3, INK)
        cv.thick_line(bx, by - 7, bx + 12, by, 3, INK)


def draw_ridge(cv):
    # Far ridge, then a nearer, darker one.
    cv.fill_poly([(0, 640), (120, 560), (260, 610), (380, 545),
                  (520, 605), (660, 555), (800, 610), (920, 565),
                  (1024, 615), (1024, 660), (0, 660)], RIDGE_FAR)
    cv.fill_poly([(0, 660), (160, 600), (300, 645), (470, 595),
                  (640, 650), (820, 600), (1024, 648), (1024, 660),
                  (0, 660)], RIDGE_NEAR)


def draw_upward_fall(cv, x, y_top, y_base, width):
    """A waterfall that climbs: a pale ribbon rising from y_base to y_top,
    narrowing as it rises, with rising droplets above it."""
    steps = 24
    for k in range(steps):
        t = k / (steps - 1)          # 0 at base, 1 at top
        y = int(y_base - (y_base - y_top) * t)
        sway = int(10 * math.sin(t * math.pi * 2.2))
        half = max(2, int(width * (1.0 - 0.55 * t) / 2))
        col = WATERFALL if k % 3 else WATERFALL_DEEP
        cv.fill_rect(x + sway - half, y - 6, x + sway + half, y + 6, col)
    # Droplets rising past the top of the ribbon.
    for k in range(6):
        dy = 14 + k * 12
        dx = int(12 * math.sin((y_top - dy) * 0.02))
        cv.disc(x + dx, y_top - dy, max(2, 5 - k // 2), WATERFALL,
                0.9 - k * 0.12)


def draw_terrace(cv, x0, x1, y_top, y_base, lit=True):
    """One floating rock terrace: flat green-gold top, tapering rock
    underside, a few small trees, and waterfalls climbing off its base."""
    top_col = TERRACE_TOP_LIT if lit else TERRACE_TOP
    rock_col = ROCK_LIT if lit else ROCK_DARK
    # Rock body: trapezoid narrowing downward to a point.
    mid_x = (x0 + x1) // 2
    cv.fill_poly([(x0, y_top), (x1, y_top),
                  (mid_x + (x1 - x0) // 6, y_base),
                  (mid_x - (x1 - x0) // 6, y_base)], rock_col)
    # Lit edge on the sun side.
    cv.fill_poly([(x1 - 14, y_top), (x1, y_top),
                  (mid_x + (x1 - x0) // 6, y_base),
                  (mid_x + (x1 - x0) // 6 - 10, y_base)], ROCK_LIT)
    # Vegetated top slab.
    cv.fill_poly([(x0 - 6, y_top), (x1 + 6, y_top),
                  (x1 - 4, y_top + 16), (x0 + 4, y_top + 16)], top_col)
    # Small trees: dark triangles with a trunk.
    for tx in (x0 + (x1 - x0) // 4, x0 + (x1 - x0) // 2, x0 + 3 * (x1 - x0) // 4):
        th = 26 if lit else 20
        cv.fill_poly([(tx, y_top - th), (tx - 12, y_top),
                      (tx + 12, y_top)], (34, 84, 52) if lit else (26, 62, 44))
        cv.fill_rect(tx - 2, y_top - 4, tx + 2, y_top + 2, (52, 34, 30))
    # Waterfalls climbing from the terrace's underside.
    draw_upward_fall(cv, mid_x - (x1 - x0) // 5, y_top - 120, y_base - 6, 16)
    draw_upward_fall(cv, mid_x + (x1 - x0) // 5, y_top - 90, y_base - 10, 12)


def draw_sea(cv):
    cv.vgrad(660, H, [(0.0, SEA_TOP), (1.0, SEA_DEEP)])
    # Sun's reflection: soft shimmering bands under the sun, fading
    # with distance and toward their edges, ending above the footer.
    for k in range(18):
        y = 668 + k * 13
        half = 22 + int(40 * (k / 17.0))
        peak = 0.55 - 0.38 * (k / 17.0)
        for x in range(700 - half, 700 + half):
            edge = 1.0 - abs(x - 700) / half
            cv.blend(x, y, SEA_SHIMMER, peak * edge * edge)
            cv.blend(x, y + 3, SEA_SHIMMER, peak * edge * edge * 0.6)
    # Calm horizontal ripple lines.
    for y, a in ((700, 0.25), (760, 0.20), (830, 0.16), (900, 0.12), (970, 0.10)):
        for x in range(40, 984, 7):
            if (x * 7 + y * 13) % 11 < 6:
                cv.blend(x, y, (190, 230, 235), a)


def draw_boat(cv):
    # A small lateen-sailed boat on the amber sea, heading for the isles.
    bx, by = 330, 800
    cv.fill_poly([(bx - 70, by), (bx + 70, by), (bx + 46, by + 16),
                  (bx - 46, by + 16)], BOAT)
    cv.thick_line(bx, by - 4, bx, by - 96, 4, BOAT)
    cv.fill_poly([(bx + 4, by - 92), (bx + 4, by - 10), (bx + 62, by - 10)],
                 (255, 240, 214))
    cv.fill_poly([(bx - 4, by - 84), (bx - 4, by - 10), (bx - 48, by - 10)],
                 (214, 110, 88))


def draw_poster():
    cv = Canvas(W, H)
    draw_sky(cv)
    draw_sun(cv)
    draw_clouds(cv)
    draw_birds(cv)
    draw_ridge(cv)
    # The landmark: three floating terraces, waterfalls climbing skyward.
    draw_terrace(cv, 560, 880, 330, 470, lit=True)    # right, sunlit
    draw_terrace(cv, 120, 470, 400, 560, lit=False)   # left, in shade
    draw_terrace(cv, 430, 580, 250, 330, lit=True)    # small, high centre
    draw_sea(cv)
    draw_boat(cv)
    # Type: name first, then the promise, then the small line.
    draw_text(cv, "VELDORA", W // 2, 64, 16, INK, shadow=INK_SHADOW)
    draw_text(cv, "WHERE THE WATERFALLS CLIMB", W // 2, 214, 4, INK,
              shadow=INK_SHADOW)
    draw_text(cv, "THE SKYWARD ISLES", W // 2, 946, 3, INK,
              shadow=INK_SHADOW)
    # Thin poster border.
    for t in range(3):
        x0, y0, x1, y1 = 22 + t, 22 + t, W - 22 - t, H - 22 - t
        cv.fill_rect(x0, y0, x1, y0 + 1, BORDER)
        cv.fill_rect(x0, y1, x1, y1 + 1, BORDER)
        cv.fill_rect(x0, y0, x0 + 1, y1, BORDER)
        cv.fill_rect(x1, y0, x1 + 1, y1, BORDER)
    return cv


# --------------------------------------------------------------------- png
def png_bytes(cv):
    """Encode the canvas as a PNG (colour type 2, RGB, 8 bit).
    Deterministic: filter 0 on every row, zlib level 9, no ancillary
    chunks, so identical pixels always give identical bytes."""
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp)
            + chunk(b"IEND", b""))


def main():
    out = os.environ.get("OUTPUT_PATH", "/output/entry.png")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    data = png_bytes(draw_poster())
    with open(out, "wb") as f:
        f.write(data)
    print(f"wrote {out} ({len(data)} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
