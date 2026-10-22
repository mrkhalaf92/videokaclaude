#!/usr/bin/env python3
"""Video TikTok 34s (1080x1920): HYB - Circle Anak Soleh, gaya doodle tangan melukis.

Guna: python3 build_hyb_doodle.py <output.mp4> [vo.wav]
      python3 build_hyb_doodle.py still <saat>...   (simpan still_<saat>.png)
      python3 build_hyb_doodle.py board <output.png> (contact sheet storyboard)
Tanpa vo.wav, video keluar dengan SFX pen marker sahaja. VO_CUTS ditala untuk VO 28.5s (22/10/2026);
kalau VO dirakam semula, laraskan VO_CUTS ikut jeda baru (ffmpeg silencedetect).
"""
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, S = 1080, 1920, 30, 2  # S = supersample
DUR = 34.0
HERE = os.path.dirname(os.path.abspath(__file__))

BG = (250, 247, 238)
INK = (28, 28, 34)
MUSTARD = (240, 192, 64)
MUSTARD_L = (250, 226, 160)
NAVY = (30, 46, 92)
SKIN = (242, 200, 156)
GREY = (120, 116, 108)
WHITE = (255, 255, 255)
OFF = (1300, 2350)  # posisi tangan di luar skrin

FD = "/usr/share/fonts/opentype/inter/"
_fc = {}


def font(size, w="Black"):
    k = (int(size * S), w)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(f"{FD}Inter-{w}.otf", k[0])
    return _fc[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_back(x):
    x = clamp(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def sc(pts):
    return [(x * S, y * S) for x, y in pts]


# ---- bentuk (senarai titik dalam ruang 1080x1920) ----
def ell(cx, cy, rx, ry=None, a0=-90, a1=270, n=72):
    ry = rx if ry is None else ry
    k = max(8, int(n * abs(a1 - a0) / 360))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / k)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / k))) for i in range(k + 1)]


def quad(p0, p1, p2, n=24):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]) for u in (i / n for i in range(n + 1))]


def rbox(x0, y0, x1, y1, r):
    return (ell(x0 + r, y0 + r, r, r, 180, 270, 16) + ell(x1 - r, y0 + r, r, r, 270, 360, 16)
            + ell(x1 - r, y1 - r, r, r, 0, 90, 16) + ell(x0 + r, y1 - r, r, r, 90, 180, 16) + [(x0, y0 + r)])


def heart(cx, cy, k):
    pts = []
    for i in range(73):
        a = math.pi * 2 * i / 72 + math.pi
        pts.append((cx + k * 16 * math.sin(a) ** 3,
                    cy - k * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))))
    return pts


def cum(pts):
    c = [0.0]
    for a, b in zip(pts, pts[1:]):
        c.append(c[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return c


def part(pts, p):
    """Bahagian polyline sehingga pecahan p, dan titik hujung (tip)."""
    c = cum(pts)
    L = c[-1] * clamp(p)
    out = [pts[0]]
    for i in range(1, len(pts)):
        if c[i] <= L:
            out.append(pts[i])
        else:
            seg = c[i] - c[i - 1]
            u = (L - c[i - 1]) / seg if seg else 0
            out.append((pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * u, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * u))
            break
    return out, out[-1]


# ---- aksi ----
class Act:
    def __init__(self, t0, t1, guide, draw, hand=True, z=1, sfx=True):
        self.t0, self.t1, self.guide, self.draw, self.hand, self.z, self.sfx = t0, t1, guide, draw, hand, z, sfx

    def p(self, t):
        return clamp((t - self.t0) / max(1e-6, self.t1 - self.t0))


def stroke(t0, t1, pts, w=7, col=INK):
    def draw(img, d, p):
        sub, _ = part(pts, p)
        if len(sub) > 1:
            d.line(sc(sub), fill=col, width=int(w * S), joint="curve")
        for x, y in (sub[0], sub[-1]):
            r = w * S / 2
            d.ellipse([x * S - r, y * S - r, x * S + r, y * S + r], fill=col)
    return Act(t0, t1, pts, draw)


def seq(t0, t1, items, w=7, col=INK):
    """Lukis beberapa garisan berturutan; masa dibahagi ikut panjang."""
    lens = [cum(it)[-1] + 60 for it in items]
    tot, t, acts = sum(lens), t0, []
    for it, ln in zip(items, lens):
        d = (t1 - t0) * ln / tot
        acts.append(stroke(t, t + d * 0.85, it, w, col))
        t += d
    return acts


def fill(t, shape, col, dur=0.25, kind="poly"):
    def draw(img, d, p):
        c = lerp(BG, col, p)
        if kind == "poly":
            d.polygon(sc(shape), fill=c)
        else:
            d.ellipse([v * S for v in shape], fill=c)
    return Act(t, t + dur, None, draw, hand=False, z=0, sfx=False)


_tc = {}


def text_img(s, size, w, col, stroke_w=0, stroke_col=INK):
    k = (s, size, w, col, stroke_w)
    if k not in _tc:
        f = font(size, w)
        sw = int(stroke_w * S)
        x0, y0, x1, y1 = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), s, font=f, anchor="mm", stroke_width=sw)
        im = Image.new("RGBA", (x1 - x0 + 8, y1 - y0 + 8), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((-x0 + 4, -y0 + 4), s, font=f, fill=col, anchor="mm", stroke_width=sw, stroke_fill=stroke_col)
        _tc[k] = (im, x0 - 4, y0 - 4)
    return _tc[k]


def text_w(s, size, w="Black"):
    im, _, _ = text_img(s, size, w, INK)
    return im.width / S


def text(t0, t1, s, cx, cy, size, w="Black", col=INK, stroke_w=0, hand=True):
    im, ox, oy = text_img(s, size, w, col, stroke_w)
    x0, x1 = cx + ox / S, cx + (ox + im.width) / S
    gy = cy + im.height / S * 0.2

    def draw(img, d, p):
        cw = int(im.width * p)
        if cw > 0:
            piece = im.crop((0, 0, cw, im.height))
            img.paste(piece, (int(cx * S + ox), int(cy * S + oy)), piece)
    return Act(t0, t1, [(x0 + 6, gy), (x1 - 6, gy)] if hand else None, draw, hand=hand, sfx=hand)


def highlight(t0, t1, s, cx, cy, size, w="Black", h=30):
    tw = text_w(s, size, w)
    y = cy + size * 0.22
    return stroke(t0, t1, [(cx - tw / 2 - 6, y), (cx + tw / 2 + 6, y)], h, MUSTARD)


def pop(t0, cx, cy, make, dur=0.4):
    cache = {}

    def draw(img, d, p):
        if "im" not in cache:
            cache["im"] = make()
        k = ease_back(p)
        if k <= 0.01:
            return
        im = cache["im"]
        sz = (max(1, int(im.width * k)), max(1, int(im.height * k)))
        im2 = im.resize(sz, Image.BILINEAR)
        img.paste(im2, (int(cx * S - sz[0] / 2), int(cy * S - sz[1] / 2)), im2)
    return Act(t0, t0 + dur, None, draw, hand=False, sfx=False)


# ---- watak doodle ----
def boy(t0, t1, cx, cy, r, extra=True):
    items = [ell(cx, cy, r),
             ell(cx, cy - r * 0.45, r * 0.92, r * 0.62, 190, 350)]  # kopiah
    items[1] = items[1] + [items[1][0]]
    acts = [fill(t0 + (t1 - t0) * 0.6, items[1][:-1], WHITE)]
    if extra:
        items += [ell(cx - r * 0.33, cy + r * 0.05, r * 0.06), ell(cx + r * 0.33, cy + r * 0.05, r * 0.06),
                  ell(cx, cy + r * 0.2, r * 0.38, r * 0.3, 20, 160)]
    return acts + seq(t0, t1, items, w=max(5, r * 0.07))


def girl(t0, t1, cx, cy, r):
    tud = ell(cx, cy + r * 0.25, r * 1.22, r * 1.42)
    items = [tud, ell(cx, cy + r * 0.12, r * 0.86, r * 0.9),
             ell(cx - r * 0.3, cy + r * 0.1, r * 0.06), ell(cx + r * 0.3, cy + r * 0.1, r * 0.06),
             ell(cx, cy + r * 0.28, r * 0.33, r * 0.26, 20, 160)]
    return [fill(t0 + 0.15, tud, MUSTARD_L), fill(t0 + 0.2, [cx - r * 0.86, cy - r * 0.78, cx + r * 0.86, cy + r * 1.02], BG, kind="ell")] \
        + seq(t0, t1, items, w=max(5, r * 0.07))


def head(t0, t1, cx, cy, r):
    return boy(t0, t1, cx, cy, r, extra=r > 40)


# ---- tangan ----
def make_hand():
    k = 2 * S / 2  # sprite dilukis pada skala supersample
    im = Image.new("RGBA", (int(900 * k), int(900 * k)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = 6 * k

    def P(pts):
        return [(x * k, y * k) for x, y in pts]

    d.polygon(P([(215, 330), (330, 215), (900, 780), (780, 900)]), fill=NAVY, outline=INK, width=int(o))
    d.line(P([(250, 365), (365, 250)]), fill=(60, 80, 140), width=int(10 * k))
    d.ellipse(P([(118, 118), (312, 312)]), fill=SKIN, outline=INK, width=int(o))
    d.polygon(P([(4, 4), (34, 22), (22, 34)]), fill=INK)
    d.polygon(P([(30, 18), (188, 160), (160, 188), (18, 30)]), fill=(40, 52, 80), outline=INK, width=int(4 * k))
    for x, y in ((108, 150), (134, 186), (166, 216)):
        d.ellipse(P([(x - 36, y - 24), (x + 36, y + 24)]), fill=SKIN, outline=INK, width=int(o))
    d.ellipse(P([(124, 92), (204, 136)]), fill=SKIN, outline=INK, width=int(o))
    return im


HAND = None


# ---- adegan ----
L1, L2, L3 = 430, 545, 660
HS = 86  # saiz tajuk
# sempadan adegan, disegerakkan dengan jeda dalam VO
B = [0.0, 3.0, 7.3, 11.6, 15.7, 22.1, 25.8, 29.3, DUR]
# potongan VO: (mula sumber, tamat sumber, mula dalam video)
VO_CUTS = [(0.0, 1.62, 0.1), (2.05, 5.80, 3.1), (6.18, 10.0, 7.4), (10.44, 13.99, 11.7),
           (14.29, 19.97, 15.8), (20.27, 23.04, 22.2), (23.47, 25.60, 25.9), (26.01, 28.52, 29.4)]


def headline(t0, lines, hl=None, speed=0.042, size=HS, ys=None):
    """lines: senarai teks; hl: indeks baris yang di-highlight. Pulangkan (acts, masa tamat)."""
    ys = ys or [L1, L2, L3][:len(lines)]
    acts, t = [], t0
    for i, (s, y) in enumerate(zip(lines, ys)):
        if i == hl:
            acts.append(highlight(t, t + 0.2, s, 540, y, size))
            t += 0.25
        d = max(0.3, len(s) * speed)
        acts.append(text(t, t + d, s, 540, y, size))
        t += d + 0.05
    return acts, t


def scene1(s0, s1):
    a, t = headline(s0 + 0.1, ["ANAK DAH MASUK", "SEKOLAH RENDAH?"], hl=1, size=84, speed=0.032)
    a.append(text(t, t + 0.28, "(umur 7–12 tahun)", 540, 650, 46, "SemiBold", GREY))
    t += 0.32
    bx, by = 540, 1150
    bag = rbox(bx - 125, by - 120, bx + 125, by + 160, 44)
    flap = [(bx - 125, by - 30), (bx - 125, by - 75)] + ell(bx, by - 75, 125, 75, 180, 360)[1:] + [(bx + 125, by - 30), (bx - 125, by - 30)]
    a += [fill(t + 0.2, bag, MUSTARD)]
    a += seq(t, t + 0.36, [bag, flap, ell(bx, by - 140, 44, 44, 180, 360), rbox(bx - 50, by + 40, bx + 50, by + 115, 16)])
    a += boy(t + 0.38, t + 0.68, 225, 1110, 108)
    a += girl(t + 0.7, t + 1.05, 855, 1080, 92)
    return s0, s1, a


def scene2(s0, s1):
    a, t = headline(s0 + 0.2, ["Ibu ayah mencari", "circle anak soleh"], hl=1, speed=0.05)
    t += 0.05
    cx, cy = 500, 1080
    a += [fill(t + 0.3, [cx - 225, cy - 225, cx + 225, cy + 225], (255, 252, 244), kind="ell")]
    a += seq(t, t + 0.55, [ell(cx, cy, 225), ell(cx, cy, 200), [(cx + 170, cy + 170), (cx + 320, cy + 320)]], w=9)
    a.append(stroke(t + 0.5, t + 0.62, [(cx + 175, cy + 175), (cx + 315, cy + 315)], 30))
    t += 0.65
    a += seq(t, t + 0.4, [[(cx - 70, cy + 110), (cx + 70, cy + 40)], [(cx + 70, cy + 110), (cx - 70, cy + 40)],
                          quad((cx - 80, cy + 20), (cx - 40, cy + 40), (cx, cy + 40)) + quad((cx, cy + 40), (cx + 40, cy + 40), (cx + 80, cy + 20)),
                          [(cx - 80, cy + 20), (cx - 80, cy - 30)] + quad((cx - 80, cy - 30), (cx - 40, cy - 10), (cx, cy - 10)) + [(cx, cy + 40)],
                          [(cx, cy - 10)] + quad((cx, cy - 10), (cx + 40, cy - 10), (cx + 80, cy - 30)) + [(cx + 80, cy + 20)]], w=6)
    t += 0.45
    for i, (x, y) in enumerate([(cx - 140, cy - 10), (cx, cy - 130), (cx + 140, cy - 10)]):
        a += head(t + i * 0.25, t + i * 0.25 + 0.23, x, y, 46)
    return s0, s1, a


def scene3(s0, s1):
    a, t = headline(s0 + 0.15, ["Umur ni, kawan", "yang bentuk anak."], hl=1, speed=0.04)
    a += boy(t, t + 0.4, 540, 1070, 110)
    t += 0.42
    pos = [(230, 890), (850, 890), (230, 1260), (850, 1260)]
    for i, (x, y) in enumerate(pos):
        a += head(t + i * 0.14, t + i * 0.14 + 0.13, x, y, 58)
    t += 0.6
    arrows = []
    for x, y in pos:
        dx, dy = 540 - x, 1070 - y
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        p0, p1 = (x + ux * 85, y + uy * 85), (540 - ux * 140, 1070 - uy * 140)
        arrows.append([p0, p1, (p1[0] - ux * 26 - uy * 18, p1[1] - uy * 26 + ux * 18), p1, (p1[0] - ux * 26 + uy * 18, p1[1] - uy * 26 - ux * 18)])
    a += seq(t, t + 0.45, arrows, w=6)
    return s0, s1, a


def scene4(s0, s1):
    a, t = headline(s0 + 0.15, ["Hantar ke circle", "anak soleh"], speed=0.04, size=82)
    hx, hy = 220, 1230
    house = [(hx - 85, hy - 90), (hx - 85, hy + 70), (hx + 85, hy + 70), (hx + 85, hy - 90)]
    roof = [(hx - 110, hy - 80), (hx, hy - 175), (hx + 110, hy - 80), (hx - 110, hy - 80)]
    a += [fill(t + 0.25, roof, MUSTARD)]
    a += seq(t, t + 0.4, [roof, house, rbox(hx - 25, hy + 5, hx + 25, hy + 70, 6)])
    t += 0.45
    path = quad((hx + 100, hy + 60), (450, 1420), (640, 1300))
    dashes = [path[i:i + 3] for i in range(0, len(path) - 2, 4)]
    a += seq(t, t + 0.3, dashes, w=6)
    t += 0.35
    mx, my = 760, 1300
    dome = ell(mx, my - 200, 115, 105, 180, 360) + [(mx - 115, my - 200)]
    a += [fill(t + 0.25, dome, MUSTARD), fill(t + 0.55, [(950, 1010), (990, 1010), (990, 1300), (950, 1300)], MUSTARD_L)]
    a += seq(t, t + 0.65, [[(mx - 150, my - 200), (mx - 150, my), (mx + 150, my), (mx + 150, my - 200), (mx - 150, my - 200)],
                           dome, [(mx, my - 305), (mx, my - 350)], ell(mx, my - 362, 12),
                           [(mx - 35, my)] + ell(mx, my - 70, 35, 45, 180, 360) + [(mx + 35, my)],
                           [(950, 1300), (950, 1010), (970, 975), (990, 1010), (990, 1300)]])
    t = max(t + 0.7, s0 + 2.6)  # "dekat rumah je" ikut VO
    b, _ = headline(t, ["dekat rumah je."], hl=0, speed=0.036, size=82, ys=[L3])
    return s0, s1, a + b


_logo = None


def logo_img(w):
    global _logo
    if _logo is None:
        src = Image.open(os.path.join(HERE, "assets", "hyb_wordmark.png")).convert("RGBA")
        _logo = src.resize((int(w * S), int(src.height * w * S / src.width)), Image.LANCZOS)
    return _logo


def scene5(s0, s1):
    a, t = [], s0 + 0.15
    lw, lcx, lcy = 1000, 540, 600

    def draw_logo(img, d, p):
        im = logo_img(lw)
        cw = int(im.width * p)
        if cw > 0:
            piece = im.crop((0, 0, cw, im.height))
            img.paste(piece, (int((lcx - lw / 2) * S), int(lcy * S - im.height / 2)), piece)
    a.append(Act(t, t + 1.3, [(lcx - lw * 0.45, lcy + 40), (lcx + lw * 0.45, lcy + 40)], draw_logo))
    # ikon: buku, sejadah, hati - ikut VO "Al-Quran", "solat", "adab"
    t = s0 + 3.0
    bx, by = 240, 1060
    book = [(bx - 85, by - 45), (bx, by - 22), (bx + 85, by - 45), (bx + 85, by + 50), (bx, by + 73), (bx - 85, by + 50), (bx - 85, by - 45)]
    a += [fill(t + 0.15, book, MUSTARD_L)]
    a += seq(t, t + 0.4, [book, [(bx, by - 22), (bx, by + 73)], [(bx - 62, by - 5), (bx - 22, by + 6)], [(bx + 22, by + 6), (bx + 62, by - 5)]], w=6)
    a.append(text(t + 0.42, t + 0.62, "Al-Quran", bx, by + 140, 46, "Bold"))
    t = s0 + 4.35
    sx, sy = 540, 1060
    mat = [(sx - 68, sy - 78), (sx + 68, sy - 78), (sx + 68, sy + 78), (sx - 68, sy + 78), (sx - 68, sy - 78)]
    arch = [(sx - 40, sy + 56), (sx - 40, sy - 10)] + ell(sx, sy - 10, 40, 45, 180, 360) + [(sx + 40, sy + 56)]
    a += [fill(t + 0.15, mat, MUSTARD_L)]
    a += seq(t, t + 0.35, [mat, arch], w=6)
    a.append(text(t + 0.37, t + 0.52, "Solat", sx, sy + 140, 46, "Bold"))
    t = s0 + 5.1
    hp = heart(840, 1055, 4.7)
    a += [fill(t + 0.2, hp, MUSTARD)]
    a += seq(t, t + 0.32, [hp], w=6)
    a.append(text(t + 0.34, t + 0.5, "Adab", 840, 1200, 46, "Bold"))
    return s0, s1, a


def scene6(s0, s1):
    t = s0 + 0.12
    cx, cy = 225, 470
    a = seq(t, t + 0.3, [ell(cx, cy, 46), [(cx, cy - 26), (cx, cy), (cx + 21, cy + 12)]], w=6)
    a.append(text(t + 0.32, t + 0.8, "Setiap Sabtu · 9–11 pagi", 590, 470, 48, "Bold"))
    t += 0.85
    a.append(text(t, t + 0.2, "YURAN", 540, 640, 54))
    a.append(text(t + 0.25, t + 0.9, "RM50", 540, 840, 300, col=MUSTARD, stroke_w=9))
    a.append(stroke(t + 0.95, t + 1.2, quad((290, 1000), (540, 1050), (800, 990)), 9))
    a.append(text(t + 1.25, t + 1.6, "/ SEBULAN", 540, 1110, 66))
    return s0, s1, a


def scene7(s0, s1):
    a, t = headline(s0 + 0.15, ["Satu tempat,", "20 pelajar je."], hl=1, speed=0.042)
    t = max(t, s0 + 1.45)
    cells = [(540 + (c - 2) * 140, 860 + r * 140) for r in range(4) for c in range(5)]
    for i, (x, y) in enumerate(cells):
        a.append(stroke(t + i * 0.035, t + i * 0.035 + 0.032, ell(x, y, 50), 6))
    t += 20 * 0.035 + 0.05
    for i, (x, y) in enumerate(cells):
        def draw(img, d, p, x=x, y=y):
            r = 44 * ease_back(p)
            d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=MUSTARD)
        a.append(Act(t + i * 0.035, t + i * 0.035 + 0.2, None, draw, hand=False, sfx=False))
    return s0, s1, a


def bubble():
    w, h = 760, 190
    im = Image.new("RGBA", (int((w + 40) * S), int((h + 80) * S)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = 7 * S
    d.polygon([(90 * S, (h + 10) * S), (90 * S, (h + 70) * S), (170 * S, (h + 10) * S)], fill=MUSTARD, outline=INK, width=int(o))
    d.rounded_rectangle([20 * S, 20 * S, (w + 20) * S, (h + 20) * S], radius=40 * S, fill=MUSTARD, outline=INK, width=int(o))
    d.polygon([(96 * S, (h + 6) * S), (96 * S, (h + 50) * S), (160 * S, (h + 6) * S)], fill=MUSTARD)
    d.text(((w + 40) / 2 * S, (h + 40) / 2 * S), "KOMEN LOKASI ANDA", font=font(60), fill=INK, anchor="mm")
    return im


def scene8(s0, s1):
    a = [text(s0 + 0.12, s0 + 0.65, "Nak info lanjut?", 540, 470, 88)]
    t = s0 + 0.7
    px, py = 540, 700
    pin = ell(px, py, 82, 82, 140, 400) + [(px, py + 150), ell(px, py, 82, 82, 140, 400)[0]]
    a += [fill(t + 0.3, pin, MUSTARD)]
    a += seq(t, t + 0.42, [pin, ell(px, py, 28)])
    t = s0 + 1.2
    a.append(pop(t, 540, 1020, bubble, dur=0.45))
    t += 0.6
    box = rbox(170, 1210, 910, 1310, 22)
    a.append(stroke(t, t + 0.4, box, 6))
    a.append(text(t + 0.45, t + 1.0, "Bangi, Selangor", 470, 1260, 46, "SemiBold", GREY))
    a.append(text(t + 1.2, t + 1.21, "@gengngajiglobal", 540, 1420, 40, "SemiBold", GREY, hand=False))
    return s0, s1, a


SCENES = [f(B[i], B[i + 1]) for i, f in enumerate([scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8])]
FADE = 0.25


def hand_pos(t, s0, s1, acts):
    ha = sorted([x for x in acts if x.hand], key=lambda x: x.t0)
    keys = []  # (t, titik) di antara aksi
    for x in ha:
        if x.t0 <= t <= x.t1:
            _, tip = part(x.guide, x.p(t))
            j = 3 * math.sin(t * 37) if x.p(t) < 1 else 0
            return (tip[0] + j, tip[1] + j * 0.6)
    prev_t, prev_p = max(s0, ha[0].t0 - 0.45), OFF
    for x in ha:
        if t < x.t0:
            k = ease_io((t - prev_t) / max(1e-6, x.t0 - prev_t))
            g = x.guide[0]
            return (prev_p[0] + (g[0] - prev_p[0]) * k, prev_p[1] + (g[1] - prev_p[1]) * k)
        prev_t, prev_p = x.t1, part(x.guide, 1)[1]
    k = ease_io((t - prev_t) / 0.45)
    return (prev_p[0] + (OFF[0] - prev_p[0]) * k, prev_p[1] + (OFF[1] - prev_p[1]) * k)


def render(t):
    global HAND
    if HAND is None:
        HAND = make_hand()
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)
    s0, s1, acts = next(sc_ for sc_ in SCENES if sc_[0] <= t < sc_[1]) if t < DUR else SCENES[-1]
    for z in (0, 1):
        for x in acts:
            if x.z == z and t >= x.t0:
                x.draw(img, d, x.p(t))
    hx, hy = hand_pos(t, s0, s1, acts)
    img.paste(HAND, (int(hx * S - 4 * S), int(hy * S - 4 * S)), HAND)
    img = img.resize((W, H), Image.LANCZOS)
    if s1 < DUR and t > s1 - FADE:
        img = Image.blend(img, Image.new("RGB", (W, H), BG), clamp((t - (s1 - FADE)) / FADE))
    return img


def frame(i):
    return np.asarray(render(i / FPS)).tobytes()


def load_vo(path, sr):
    """Tukar VO ke mono sr, potong ikut VO_CUTS dan letak pada masa video."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    src = np.frombuffer(raw, np.float32)
    out = np.zeros(int(DUR * sr), np.float32)
    for a, b, t in VO_CUTS:
        piece = src[int(a * sr):int(b * sr)]
        k = int(t * sr)
        out[k:k + len(piece)] += piece[: len(out) - k]
    return out


def sfx_track(path, vo=None):
    sr = 44100
    n = int(DUR * sr)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(7)
    for s0, s1, acts in SCENES:
        for x in acts:
            if x.sfx and x.hand and x.t1 - x.t0 > 0.04:
                a, b = int(x.t0 * sr), min(n, int(x.t1 * sr))
                m = b - a
                noise = rng.standard_normal(m).astype(np.float32)
                noise = np.diff(np.concatenate([[0], noise]))  # high-pass ringan
                tt = np.arange(m) / sr
                mod = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * (7 + rng.random() * 4) * tt))
                env = np.minimum(1, np.minimum(tt / 0.02, (m / sr - tt) / 0.03))
                out[a:b] += noise * mod * env * 0.05
            elif not x.hand and x.draw.__name__ == "draw" and x.t1 - x.t0 >= 0.39:  # pop
                a = int(x.t0 * sr)
                m = int(0.12 * sr)
                tt = np.arange(m) / sr
                tone = np.sin(2 * np.pi * (700 + 900 * tt / 0.12) * tt) * np.exp(-tt * 30) * 0.25
                out[a:a + m] += tone[: max(0, min(m, n - a))]
    if vo:
        out = out * 0.6 + load_vo(vo, sr)
    pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def main(out, vo=None):
    sfx = os.path.splitext(out)[0] + "_sfx.wav"
    sfx_track(sfx, vo)
    total = int(round(DUR * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", sfx]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{DUR:.2f}", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for n, buf in enumerate(pool.imap(frame, range(total), chunksize=4)):
            p.stdin.write(buf)
            if n % 100 == 0:
                print(f"{n}/{total}", flush=True)
    p.stdin.close()
    p.wait()
    os.remove(sfx)


# panel storyboard: (saat, label babak, VO)
BOARD = [
    (1.4, "HOOK 0–3s", "Anak dah masuk sekolah rendah?"),
    (2.7, "HOOK 0–3s", "(tiada VO, teks umur 7–12 tahun)"),
    (4.6, "ISI 1 3–7.3s", "Ramai ibu ayah sekarang tengah cari…"),
    (7.0, "ISI 1 3–7.3s", "…circle anak soleh."),
    (11.3, "ISI 2 7.3–11.6s", "Sebab umur macam ni, kawan sekeliling yang bentuk anak kita."),
    (13.5, "ISI 3 11.6–15.7s", "Hantar mereka ke circle anak soleh…"),
    (15.4, "ISI 3 11.6–15.7s", "…dekat rumah je."),
    (17.6, "ISI 4 15.7–22.1s", "HYB, Halaqah Ya Bunayya."),
    (21.8, "ISI 4 15.7–22.1s", "Bimbingan Al-Quran, solat dan adab."),
    (23.0, "ISI 5 22.1–25.8s", "Seminggu sekali…"),
    (25.5, "ISI 5 22.1–25.8s", "…lima puluh ringgit je sebulan."),
    (27.5, "ISI 6 25.8–29.3s", "Satu tempat…"),
    (29.0, "ISI 6 25.8–29.3s", "…dua puluh pelajar je."),
    (30.6, "CTA 29.3–34s", "Nak info lanjut?"),
    (33.5, "CTA 29.3–34s", "Komen lokasi anda."),
]


def board(out):
    cols, tw, th = 5, 360, 640
    rows = math.ceil(len(BOARD) / cols)
    cap = 150
    sheet = Image.new("RGB", (cols * (tw + 30) + 30, rows * (th + cap + 30) + 130), (40, 40, 44))
    d = ImageDraw.Draw(sheet)
    d.text((30, 40), "STORYBOARD · HYB Circle Anak Soleh · 34s · 1080x1920", font=ImageFont.truetype(f"{FD}Inter-Bold.otf", 40), fill=WHITE)
    fb = ImageFont.truetype(f"{FD}Inter-Bold.otf", 24)
    fr = ImageFont.truetype(f"{FD}Inter-Regular.otf", 21)
    for i, (t, lab, vo) in enumerate(BOARD):
        x = 30 + (i % cols) * (tw + 30)
        y = 120 + (i // cols) * (th + cap + 30)
        sheet.paste(render(t).resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x, y + th + 12), f"{i + 1:02d} · {lab} · {t:.1f}s", font=fb, fill=MUSTARD)
        words, line, ly = ("VO: " + vo).split(), "", y + th + 48
        for wd in words:
            if d.textlength(line + " " + wd, font=fr) > tw:
                d.text((x, ly), line.strip(), font=fr, fill=WHITE)
                line, ly = "", ly + 28
            line += " " + wd
        d.text((x, ly), line.strip(), font=fr, fill=WHITE)
    sheet.save(out)


if __name__ == "__main__":
    if sys.argv[1] == "still":
        for tt in sys.argv[2:]:
            render(float(tt)).save(f"still_{tt}.png")
    elif sys.argv[1] == "board":
        board(sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
