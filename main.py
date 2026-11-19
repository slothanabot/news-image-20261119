#!/usr/bin/env python3
"""Atlas poster: the world news of Thursday 19 November 2026, mapped.

Draws a 1024x1024 PNG with a hand-rolled bitmap font and a hand-rolled
PNG encoder. Python 3.13 standard library only, no network, deterministic:
two runs write identical bytes.

Layout (top to bottom):
  masthead  |  date line  |  day-in-numbers strip  |  GTA VI lead band
  world map with numbered story pins and callout labels
  ticker band: the day in 36 headlines, two columns
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
INK = (16, 32, 44)          # deep atlas ink
PAPER = (244, 238, 220)     # parchment cream
PAPER_DIM = (232, 224, 200)
GOLD = (198, 158, 74)
GOLD_SOFT = (214, 182, 110)
TEAL = (14, 42, 58)         # page background
TEAL_MID = (24, 66, 84)
OCEAN = (158, 196, 190)     # map sea, pale atlas blue-green
LAND = (94, 140, 106)       # map land, muted green
LAND_EDGE = (58, 96, 72)
CORAL = (214, 74, 44)       # lead band + pins
CORAL_DARK = (168, 52, 30)
CREAM_TEXT = (244, 238, 220)
MUTED = (176, 196, 200)
GRID = (140, 178, 172)
CHIP = (250, 246, 232)
CHIP_INK = (20, 38, 50)
TICKER_BG = (12, 34, 48)
NUM_GOLD = (232, 196, 110)

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows, 5 bits wide, bit 4 = leftmost pixel. Uppercase only;
# lowercase input is upper-cased by draw_text. Poster style, all caps.
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ",": (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    ":": (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ";": (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04),
    "-": (0, 0, 0, 0x1F, 0, 0, 0),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    '"': (0x0A, 0x0A, 0x0A, 0, 0, 0, 0),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    "%": (0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "+": (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    "=": (0, 0, 0x1F, 0, 0x1F, 0, 0),
    "*": (0, 0x04, 0x15, 0x0E, 0x15, 0x04, 0),
    "#": (0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A),
    "@": (0x0E, 0x11, 0x17, 0x15, 0x16, 0x10, 0x0E),
    "[": (0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E),
    "]": (0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E),
    "_": (0, 0, 0, 0, 0, 0, 0x1F),
    "<": (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
    ">": (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
}


def advance(scale):
    return 5 * scale + max(1, scale // 2)


def text_width(text, scale):
    if not text:
        return 0
    return len(text) * advance(scale) - max(1, scale // 2)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.px), 3):
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        r, g, b = color
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def hline(self, x, y, w, color):
        self.fill_rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.fill_rect(x, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            half = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - half, cy + dy, half * 2 + 1, 1, color)

    def ring(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            half = int((r * r - dy * dy) ** 0.5)
            self.set(cx - half, cy + dy, color)
            self.set(cx + half, cy + dy, color)

    def fill_poly(self, pts, color):
        """Scanline fill, even-odd rule. pts: list of (x, y) ints."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = min(ys), max(ys)
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, yy0 = pts[i]
                x1, yy1 = pts[(i + 1) % n]
                if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                    t = (y - yy0) / (yy1 - yy0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = int(xs[k] + 0.5)
                xb = int(xs[k + 1] + 0.5)
                if xb >= xa:
                    self.fill_rect(xa, y, xb - xa + 1, 1, color)

    def poly_outline(self, pts, color):
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            self.line(x0, y0, x1, y1, color)

    def glyph(self, x, y, ch, scale, color):
        rows = FONT.get(ch, FONT["?"])
        for r in range(7):
            bits = rows[r]
            for c in range(5):
                if bits & (1 << (4 - c)):
                    self.fill_rect(x + c * scale, y + r * scale,
                                   scale, scale, color)

    def text(self, x, y, s, scale, color):
        s = s.upper()
        cx = x
        for ch in s:
            self.glyph(cx, y, ch, scale, color)
            cx += advance(scale)
        return cx

    def text_center(self, cx, y, s, scale, color):
        w = text_width(s, scale)
        return self.text(cx - w // 2, y, s, scale, color)


# ---------------------------------------------------------------- PNG out
def write_png(canvas, path):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------- world map
# Simplified continent outlines as (lon, lat) vertices, equirectangular.
# Deliberately coarse atlas style: recognisable shapes, clean edges.
NORTH_AMERICA = [
    (-168, 66), (-140, 70), (-125, 71), (-110, 68), (-95, 69), (-85, 66),
    (-80, 73), (-65, 60), (-55, 52), (-60, 47), (-70, 44), (-75, 39),
    (-80, 32), (-81, 26), (-84, 30), (-90, 21), (-97, 16), (-92, 15),
    (-83, 9), (-79, 9), (-86, 13), (-92, 14), (-97, 16), (-105, 20),
    (-110, 23), (-114, 28), (-120, 34), (-125, 40), (-124, 48), (-130, 55),
    (-145, 60), (-158, 58), (-165, 60),
]
GREENLAND = [
    (-58, 64), (-45, 60), (-40, 64), (-32, 68), (-22, 70), (-20, 74),
    (-30, 76), (-45, 76), (-58, 74), (-60, 70),
]
SOUTH_AMERICA = [
    (-79, 9), (-72, 12), (-62, 10), (-52, 5), (-50, 0), (-44, -3),
    (-35, -8), (-40, -20), (-48, -28), (-57, -38), (-65, -45), (-68, -52),
    (-70, -55), (-73, -50), (-73, -40), (-72, -30), (-70, -18), (-77, -12),
    (-80, -5), (-81, 0),
]
AFRICA = [
    (-17, 15), (-10, 31), (0, 36), (10, 37), (20, 32), (32, 31), (35, 28),
    (43, 12), (51, 11), (48, 2), (40, -5), (40, -15), (36, -25), (32, -29),
    (26, -34), (20, -35), (17, -29), (12, -18), (9, 4), (4, 6), (-8, 5),
    (-13, 8),
]
EURASIA = [
    (-10, 36), (-9, 43), (-2, 48), (0, 51), (5, 53), (8, 57), (10, 59),
    (18, 56), (21, 55), (24, 59), (30, 60), (30, 65), (40, 68), (55, 69),
    (68, 73), (75, 73), (85, 75), (100, 77), (110, 74), (120, 73),
    (130, 72), (140, 72), (158, 70), (170, 67), (178, 65), (170, 60),
    (162, 56), (158, 52), (150, 59), (142, 55), (142, 50), (140, 40),
    (135, 35), (130, 33), (127, 35), (122, 38), (120, 32), (110, 21),
    (108, 18), (105, 10), (100, 8), (98, 12), (94, 17), (91, 22),
    (89, 22), (86, 20), (80, 13), (77, 8), (75, 15), (73, 20), (70, 23),
    (66, 25), (62, 25), (58, 26), (56, 27), (52, 28), (50, 29), (48, 30),
    (44, 29), (40, 31), (36, 36), (30, 36), (27, 37), (23, 36), (19, 40),
    (15, 44), (12, 44), (8, 44), (3, 43), (-2, 44),
]
BRITAIN = [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53)]
JAPAN = [
    (130, 31), (132, 33), (135, 34), (137, 35), (139, 36), (141, 39),
    (141, 42), (143, 44), (141, 45), (139, 42), (137, 38), (135, 35),
    (132, 33),
]
AUSTRALIA = [
    (113, -22), (114, -30), (115, -35), (120, -34), (124, -33), (129, -32),
    (132, -32), (135, -35), (138, -35), (140, -38), (145, -38), (150, -37),
    (153, -32), (153, -27), (150, -22), (146, -19), (142, -15), (142, -11),
    (137, -12), (135, -15), (132, -12), (130, -13), (126, -14), (122, -17),
    (118, -20),
]
NEW_ZEALAND = [
    (167, -45), (170, -43), (173, -41), (175, -38), (177, -38), (174, -41),
    (172, -43), (168, -46),
]
INDONESIA = [
    (95, 5), (100, 0), (105, -5), (110, -7), (114, -8), (118, -8),
    (120, -10), (124, -10), (128, -8), (131, -3), (135, -2), (138, -4),
    (141, -8), (138, -8), (135, -6), (130, -3), (126, 0), (122, 1),
    (118, 2), (114, 3), (110, 1), (105, 0), (100, 0),
]
MADAGASCAR = [
    (44, -16), (47, -15), (50, -16), (49, -20), (47, -24), (45, -25),
    (43, -22), (43, -18),
]
ICELAND = [(-22, 64), (-18, 63), (-14, 64), (-15, 66), (-20, 66)]

CONTINENTS = [
    NORTH_AMERICA, GREENLAND, SOUTH_AMERICA, AFRICA, EURASIA, BRITAIN,
    JAPAN, AUSTRALIA, NEW_ZEALAND, INDONESIA, MADAGASCAR, ICELAND,
]

# Map panel geometry (equirectangular, lon -180..180, lat 85..-60).
MAP_X, MAP_Y, MAP_W, MAP_H = 24, 196, 976, 444


def project(lon, lat):
    x = MAP_X + (lon + 180.0) / 360.0 * MAP_W
    y = MAP_Y + (85.0 - lat) / 145.0 * MAP_H
    return int(round(x)), int(round(y))


def draw_map(c):
    c.fill_rect(MAP_X, MAP_Y, MAP_W, MAP_H, OCEAN)
    # graticule every 30 degrees
    for lon in range(-150, 181, 30):
        x, _ = project(lon, 0)
        c.vline(x, MAP_Y, MAP_H, GRID)
    for lat in range(-60, 86, 30):
        _, y = project(0, lat)
        c.hline(MAP_X, y, MAP_W, GRID)
    # equator, dashed
    _, yeq = project(0, 0)
    for x in range(MAP_X, MAP_X + MAP_W, 8):
        c.fill_rect(x, yeq, 4, 1, GRID)
    # ocean labels (kept inside the panel)
    c.text(*project(-30, -28), "ATLANTIC", 2, (110, 150, 146))
    c.text(*project(-150, -12), "PACIFIC", 2, (110, 150, 146))
    c.text(*project(140, -12), "PACIFIC", 2, (110, 150, 146))
    c.text(*project(55, -38), "INDIAN OCEAN", 2, (110, 150, 146))
    # land
    for poly in CONTINENTS:
        pts = [project(lon, lat) for lon, lat in poly]
        c.fill_poly(pts, LAND)
        c.poly_outline(pts, LAND_EDGE)

# ---------------------------------------------------------------- the day
# 36 headlines, each <= 38 chars so it fits one ticker line at scale 2.
HEADLINES = [
    (1, "GTA VI LAUNCHES AFTER 13-YEAR WAIT"),
    (2, "ANTHROPIC IPO: $81.3BN, DEBUTS TODAY"),
    (3, "TRUMP, XI, PUTIN MEET IN SHENZHEN"),
    (4, "US-IRAN STRIKES SPREAD ACROSS GULF"),
    (5, "EU PLANS 45BN EURO UKRAINE LOAN"),
    (6, "ICJ RULES ON MYANMAR ROHINGYA CASE"),
    (7, "CRIMEAN BRIDGE ATTACKED AGAIN"),
    (8, "NVIDIA HALTS H-SERIES SHIPS TO CHINA"),
    (9, "CYCLONE AKVAN BEARS DOWN ON INDIA"),
    (10, "VOYAGER 1 REACHES ONE LIGHT-DAY"),
    (11, "JEFFRIES FIRST BLACK SPEAKER NOMINEE"),
    (12, "PELTOLA WINS ALASKA SENATE SEAT"),
    (13, "CANADA RESETS TIES WITH CHINA"),
    (14, "AUSTRALIA SANCTIONS SETTLERS"),
    (15, "NZ V INDIA TEST STARTS IN WELLINGTON"),
    (16, "ENGLAND END SPAIN'S 43-GAME RUN 3-2"),
    (17, "INDIA BEAT PAKISTAN 2-1, WIN SAFF"),
    (18, "ISRAELI TANKS CROSS GAZA LINE"),
    (19, "SOMALIA ACCUSES UAE OF SECRET BASES"),
    (20, "LIBYA SEIZES COCAINE, MILLIONS OF PILLS"),
    (21, "ARGENTINA ROUT COSTA RICA 7-0"),
    (22, "DUCKETT 133 AS ENGLAND BEAT AUSTRALIA"),
    (23, "IMF LIFTS GERMANY GROWTH TO 1.3%"),
    (24, "VAN GOGH SELLS FOR RECORD $190.4M"),
    (25, "MCDONALD'S FACES ABUSE ALLEGATIONS"),
    (26, "FED MINUTES: MORE RATE HIKES LIKELY"),
    (27, "DOW FALLS 670 AS NVIDIA SLIDES 3%"),
    (28, "SAUDI ARABIA: DANGER HAS PASSED"),
    (29, "RUSSIAN HELD FOR SPYING ON PALANTIR"),
    (30, "MERCK AT JEFFERIES HEALTH CONFERENCE"),
    (31, "QILIN HACKER EXTRADITED TO GERMANY"),
    (32, "USS ROOSEVELT ARRIVES IN MIDDLE EAST"),
    (33, "DHONI RETIRES FROM IPL"),
    (34, "POCHETTINO NAMED MAN UTD HEAD COACH"),
    (35, "LITTON DAS SETS TEST RECORD"),
    (36, "MAHANADI COALFIELDS IPO OPENS TODAY"),
]

# Map pins: (story number, lon, lat, short label, side, dy)
# Labels are kept short (<= 20 chars) and staggered vertically so no two
# chips in one region share a row. Canada has no pin: Ottawa sits 12 px
# from New York and Washington, so it stays in the ticker only.
PINS = [
    (12, -152, 64, "PELTOLA", "R", 0),
    (8, -122, 37, "NVIDIA", "R", 0),
    (1, -80, 26, "GTA VI OUT TODAY", "R", 0),
    (2, -74, 41, "ANTHROPIC IPO", "R", -16),
    (11, -77, 39, "JEFFRIES", "L", -26),
    (16, -4, 40, "SPAIN", "R", -12),
    (25, 0, 51, "MCDONALD'S", "L", -64),
    (23, 13, 52, "GERMANY", "R", -16),
    (20, 13, 32, "LIBYA", "R", 72),
    (5, 30, 50, "EU-UKRAINE LOAN", "L", -46),
    (7, 36, 45, "CRIMEA BRIDGE", "R", -58),
    (18, 34, 31, "GAZA", "L", 44),
    (28, 47, 25, "SAUDI", "R", 58),
    (4, 56, 26, "GULF STRIKES", "R", -56),
    (19, 45, 2, "SOMALIA-UAE", "L", 0),
    (17, 90, 24, "SAFF TITLE", "R", 48),
    (9, 86, 13, "AKVAN", "R", 38),
    (6, 96, 16, "MYANMAR", "L", -46),
    (3, 114, 22, "SHENZHEN", "R", 16),
    (21, -58, -35, "ARGENTINA 7-0", "R", 0),
    (14, 149, -35, "AUSTRALIA SANCTIONS", "L", -48),
    (22, 147, -43, "DUCKETT 133", "L", 16),
    (15, 175, -41, "NZ-INDIA TEST", "L", -44),
]


def pin_chip(c, num, lon, lat, label, side, dy):
    """Leader line + label chip for one pin (pass 1 of 2)."""
    px, py = project(lon, lat)
    lx = px + 15 if side == "R" else px - 15 - text_width(label, 2)
    ly = py - 7 + dy
    # keep the chip inside the map panel
    lx = max(MAP_X + 2, min(MAP_X + MAP_W - 2 - text_width(label, 2), lx))
    ly = max(MAP_Y + 2, min(MAP_Y + MAP_H - 16, ly))
    # leader line from pin to chip
    cx = lx - 3 if side == "R" else lx + text_width(label, 2) + 3
    c.line(px, py, cx, ly + 7, CHIP_INK)
    # chip
    c.fill_rect(lx - 3, ly - 3, text_width(label, 2) + 6, 20, CHIP)
    c.fill_rect(lx - 3, ly - 3, text_width(label, 2) + 6, 1, CHIP_INK)
    c.fill_rect(lx - 3, ly + 16, text_width(label, 2) + 6, 1, CHIP_INK)
    c.fill_rect(lx - 3, ly - 3, 1, 20, CHIP_INK)
    c.fill_rect(lx + text_width(label, 2) + 2, ly - 3, 1, 20, CHIP_INK)
    c.text(lx, ly, label, 2, CHIP_INK)


def pin_disc(c, num, lon, lat):
    """Numbered pin disc (pass 2 of 2, always on top)."""
    px, py = project(lon, lat)
    c.disc(px, py, 12, CORAL)
    c.ring(px, py, 12, CREAM_TEXT)
    num_s = str(num)
    c.text(px - text_width(num_s, 2) // 2, py - 7, num_s, 2, CREAM_TEXT)


def draw_voyager(c):
    # Star marker in the map's open ocean, top right: Voyager 1 is in space,
    # so it sits apart from the geography, labelled as the day's space story.
    cx, cy = MAP_X + MAP_W - 78, MAP_Y + 26
    c.disc(cx, cy, 11, GOLD)
    c.ring(cx, cy, 11, INK)
    c.text(cx - 4, cy - 7, "*", 2, INK)
    label = "10 VOYAGER 1: ONE LIGHT-DAY"
    lx = cx - 18 - text_width(label, 2)
    c.fill_rect(lx - 3, cy - 10, text_width(label, 2) + 6, 20, CHIP)
    c.text(lx, cy - 7, label, 2, CHIP_INK)


# ---------------------------------------------------------------- build
def build():
    c = Canvas(W, H, TEAL)

    # ---- masthead
    c.text(24, 16, "THE WORLD IN ONE DAY", 5, CREAM_TEXT)
    right = "ATLAS POSTER  -  No. 323"
    c.text(W - 24 - text_width(right, 2), 22, right, 2, GOLD_SOFT)
    c.fill_rect(24, 66, W - 48, 2, GOLD)

    # ---- date line
    c.text(24, 82, "THURSDAY 19 NOVEMBER 2026", 3, NUM_GOLD)
    d_right = "36 STORIES  -  6 CONTINENTS"
    c.text(W - 24 - text_width(d_right, 2), 88, d_right, 2, MUTED)

    # ---- day in numbers
    c.fill_rect(24, 116, W - 48, 34, TEAL_MID)
    c.fill_rect(24, 116, W - 48, 1, GOLD)
    c.fill_rect(24, 149, W - 48, 1, GOLD)
    nums = ("GTA VI $79.99 - ANT IPO $81.3BN - DOW -670 - "
            "VAN GOGH $190.4M - VOYAGER 1: 1 LIGHT-DAY")
    c.text_center(W // 2, 126, nums, 2, CREAM_TEXT)

    # ---- lead band: GTA VI
    c.fill_rect(24, 158, W - 48, 38, CORAL)
    lead = "LEAD:  GTA VI LAUNCHES TODAY - VICE CITY RETURNS AFTER 13 YEARS"
    c.text_center(W // 2, 163, lead, 2, CREAM_TEXT)
    sub = "$79.99  -  PS5 + XBOX  -  METACRITIC 99  -  PRE-ORDERS TOP $1.5BN"
    c.text_center(W // 2, 180, sub, 2, (255, 220, 200))

    # ---- map
    draw_map(c)
    for num, lon, lat, label, side, dy in PINS:
        pin_chip(c, num, lon, lat, label, side, dy)
    for num, lon, lat, label, side, dy in PINS:
        pin_disc(c, num, lon, lat)
    draw_voyager(c)
    # map frame + caption
    c.fill_rect(MAP_X, MAP_Y, MAP_W, 2, INK)
    c.fill_rect(MAP_X, MAP_Y + MAP_H - 2, MAP_W, 2, INK)
    c.fill_rect(MAP_X, MAP_Y, 2, MAP_H, INK)
    c.fill_rect(MAP_X + MAP_W - 2, MAP_Y, 2, MAP_H, INK)

    # ---- ticker band
    c.fill_rect(0, 648, W, H - 648, TICKER_BG)
    c.fill_rect(24, 648, W - 48, 2, GOLD)
    c.text(24, 660, "THE DAY IN 36 HEADLINES", 2, NUM_GOLD)
    c.text(W - 24 - text_width("EACH NUMBER MATCHES A PIN ON THE MAP", 2),
           660, "EACH NUMBER MATCHES A PIN ON THE MAP", 2, MUTED)
    rows = 18
    y0 = 690
    pitch = 17
    for i, (num, text) in enumerate(HEADLINES):
        col = 0 if i < rows else 1
        row = i if i < rows else i - rows
        x = 28 if col == 0 else 528
        y = y0 + row * pitch
        line = "%d. %s" % (num, text)
        c.text(x, y, str(num) + ".", 2, NUM_GOLD)
        c.text(x + text_width(str(num) + ". ", 2), y, text, 2, CREAM_TEXT)

    return c


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    size = write_png(build(), path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
