#!/usr/bin/env python3
"""Video TikTok 38s (1080x1920): Staff berintegriti - Geng Ngaji Global.

Guna: python3 build_video.py <audio.wav> <output.mp4>
Subtitle disegerakkan daripada jeda dalam audio + anggaran panjang perkataan.
"""
import math
import os
import re
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
AUDIO = sys.argv[1]
OUT = sys.argv[2]

# ---- Warna (andaian: hijau tua + emas; tukar di sini bila ada hex brand) ----
GREEN_D = (8, 44, 34)
GREEN_M = (14, 82, 62)
GREEN_L = (24, 112, 84)
GOLD = (222, 178, 64)
GOLD_L = (245, 214, 130)
CREAM = (248, 241, 222)
WHITE = (255, 255, 255)
INK = (10, 38, 30)

FD = "/usr/share/fonts/opentype/inter/"
_fc = {}


def font(size, w="ExtraBold"):
    k = (max(2, int(size)), w)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(f"{FD}Inter-{w}.otf", k[0])
    return _fc[k]


# ---- Script & masa (saat) ----
SEGS = [
    (0.22, 7.02, "Staff yang berintegriti bukan hanya baik dalam pekerjaan, tetapi juga baik dalam amanahnya kepada Allah."),
    (8.08, 14.92, "Sebagai ustaz dan ustazah, kita bukan sekadar menyampaikan ilmu, tetapi menjadi contoh kepada orang lain."),
    (16.02, 19.38, "Jujur dalam tugas, amanah dalam tanggungjawab,"),
    (20.04, 23.78, "menjaga adab dan sentiasa ikhlas dalam menyampaikan dakwah."),
    (24.59, 29.46, "Kerana integriti bukan sekadar apa yang kita tunjukkan di hadapan manusia…"),
    (30.18, 34.06, "tetapi siapa diri kita ketika tiada siapa yang melihat."),
    (34.94, 38.10, "Itulah nilai seorang pendidik yang berintegriti."),
]
KEYWORDS = {"integriti", "berintegriti", "amanah", "amanahnya", "allah", "contoh", "jujur",
            "adab", "ikhlas", "dakwah", "melihat", "pendidik", "ilmu", "tanggungjawab"}
DUR = 38.44
# sempadan scene
SCENE_T = [0, 7.55, 15.5, 24.1, 29.8, 34.5, DUR + 1]
XF = 0.35  # crossfade


def norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def build_words():
    words = []
    for si, (a, b, text) in enumerate(SEGS):
        toks = text.split()
        wts = [len(norm(t)) + 2 + (3 if t[-1] in ",…" else 0) for t in toks]
        tot = sum(wts)
        t = a
        for tok, wt in zip(toks, wts):
            d = (b - a) * wt / tot
            words.append(dict(seg=si, text=tok, n=norm(tok), s=t, e=t + d))
            t += d
    return words


WORDS = build_words()


def wstart(n, seg=None, nth=0):
    c = [w for w in WORDS if w["n"] == n and (seg is None or w["seg"] == seg)]
    return c[nth]["s"]


def build_chunks():
    chunks = []
    for si in range(len(SEGS)):
        ws = [w for w in WORDS if w["seg"] == si]
        cur = []
        for w in ws:
            cur.append(w)
            if len(cur) >= 4 or w["text"][-1] in ",…" or (len(cur) >= 2 and len(" ".join(x["text"] for x in cur)) > 20):
                chunks.append(cur)
                cur = []
        if cur:
            if chunks and chunks[-1][0]["seg"] == si and len(cur) == 1:
                chunks[-1].extend(cur)
            else:
                chunks.append(cur)
    out = []
    for i, ch in enumerate(chunks):
        s = ch[0]["s"]
        nxt = chunks[i + 1][0] if i + 1 < len(chunks) else None
        if nxt and nxt["seg"] == ch[0]["seg"]:
            e = nxt["s"]
        else:
            e = ch[-1]["e"] + 0.25
        out.append((s, e, ch))
    return out


CHUNKS = build_chunks()


# ---- Audio envelope ----
def load_env():
    with wave.open(AUDIO) as wf:
        sr = wf.getframerate()
        raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    hop = sr // FPS
    n = len(raw) // hop
    env = np.sqrt((raw[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    env = env / (np.percentile(env, 98) + 1e-6)
    return np.clip(env, 0, 1)


ENV = load_env()


def env_at(t, k=0):
    i = int(t * FPS) + k
    return float(ENV[min(max(i, 0), len(ENV) - 1)])


# ---- Helpers ----
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = clamp(x)
    if x <= 0:
        return 0.0
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def prog(t, t0, d=0.4):
    return clamp((t - t0) / d)


def lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def gradient(top, bot):
    ys = np.linspace(0, 1, H)[:, None, None]
    a = np.array(top, dtype=np.float32)[None, None, :]
    b = np.array(bot, dtype=np.float32)[None, None, :]
    g = a + (b - a) * ys
    return np.broadcast_to(g, (H, W, 3)).astype(np.uint8).copy()


def star_tile(size, col, alpha):
    t = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    c = size / 2
    r = size * 0.42
    for rot in (0, math.pi / 4):
        pts = [(c + r * math.cos(rot + k * math.pi / 2 + math.pi / 4), c + r * math.sin(rot + k * math.pi / 2 + math.pi / 4)) for k in range(4)]
        d.polygon(pts, outline=col + (alpha,), width=3)
    d.ellipse([c - r * 0.28, c - r * 0.28, c + r * 0.28, c + r * 0.28], outline=col + (alpha,), width=3)
    for cx, cy in ((0, 0), (size, 0), (0, size), (size, size)):
        d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], outline=col + (alpha,), width=3)
    return t


TILE = 220


def pattern_layer(col, alpha):
    tile = star_tile(TILE, col, alpha)
    big = Image.new("RGBA", (W + TILE * 2, H + TILE * 2), (0, 0, 0, 0))
    for y in range(0, H + TILE * 2, TILE):
        for x in range(0, W + TILE * 2, TILE):
            big.alpha_composite(tile, (x, y))
    return big


PAT_LIGHT = pattern_layer(GOLD, 38)
PAT_DARK = pattern_layer(GREEN_D, 34)


def bg(top, bot, t, dark_pat=False, drift=1.0):
    img = Image.fromarray(gradient(top, bot)).convert("RGBA")
    pat = PAT_DARK if dark_pat else PAT_LIGHT
    ox = int((t * 14 * drift) % TILE)
    oy = int((t * 9 * drift) % TILE)
    img.alpha_composite(pat.crop((ox, oy, ox + W, oy + H)))
    return img


def text_c(d, xy, s, f, fill, stroke=0, stroke_fill=None, anchor="mm"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


def rrect(d, box, r, fill=None, outline=None, width=0):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def paste_alpha(base, lay, a):
    if a >= 0.999:
        base.alpha_composite(lay)
        return
    if a <= 0:
        return
    l2 = lay.copy()
    al = l2.getchannel("A").point(lambda v: int(v * a))
    l2.putalpha(al)
    base.alpha_composite(l2)


def eye(d, cx, cy, w, h, iris=GOLD, look=0.0, closed=0.0, line=GOLD_L, fillc=(255, 255, 255)):
    hh = h * (1 - closed)
    pts = []
    for i in range(0, 41):
        x = -1 + i / 20 if i <= 20 else 1 - (i - 20) / 20
        sgn = -1 if i <= 20 else 1
        xx = -1 + i / 20 if i <= 20 else 1 - (i - 20) / 20
        pts.append((cx + xx * w / 2, cy + sgn * hh * (1 - xx * xx) / 2))
    d.polygon(pts, fill=fillc, outline=line)
    d.line(pts + [pts[0]], fill=line, width=10)
    if closed < 0.7:
        r = h * 0.42
        px = cx + look * w * 0.18
        d.ellipse([px - r, cy - r * (1 - closed), px + r, cy + r * (1 - closed)], fill=iris)
        r2 = r * 0.45
        d.ellipse([px - r2, cy - r2 * (1 - closed), px + r2, cy + r2 * (1 - closed)], fill=INK)
        d.ellipse([px - r2 * 0.9 + r2 * .5, cy - r2 * 1.1, px - r2 * .1 + r2 * .5, cy - r2 * .3], fill=(255, 255, 255))


def person(d, cx, cy, s, col):
    d.ellipse([cx - s * 0.32, cy - s * 0.9, cx + s * 0.32, cy - s * 0.26], fill=col)
    d.pieslice([cx - s * 0.62, cy - s * 0.12, cx + s * 0.62, cy + s * 1.1], 180, 360, fill=col)


# ---- Elemen sepunya ----
def chrome(img, t, theme):
    d = ImageDraw.Draw(img)
    fg = CREAM if theme != "gold" and theme != "cream" else INK
    acc = GOLD if theme != "gold" else INK
    # progress bar
    x0, x1, y = 70, W - 70, 130
    d.rounded_rectangle([x0, y, x1, y + 10], 5, fill=lerp(fg, (60, 80, 70) if theme not in ('gold','cream') else (200,190,150), 0.7))
    px = x0 + (x1 - x0) * clamp(t / DUR)
    d.rounded_rectangle([x0, y, max(x0 + 10, px), y + 10], 5, fill=acc)
    # brand badge
    f = font(34, "Bold")
    txt = "GENG NGAJI GLOBAL"
    wtxt = f.getlength(txt)
    bx0, bx1 = W / 2 - wtxt / 2 - 46, W / 2 + wtxt / 2 + 46
    rrect(d, [bx0, 175, bx1, 245], 35, outline=acc, width=3)
    d.ellipse([bx0 + 24, 203, bx0 + 38, 217], fill=acc)
    text_c(d, (W / 2 + 10, 210), txt, f, fg)


def waveform(img, t, theme):
    d = ImageDraw.Draw(img)
    col = GOLD if theme not in ("gold",) else INK
    n = 31
    bw, gap = 14, 12
    tot = n * bw + (n - 1) * gap
    x = W / 2 - tot / 2
    cy = 1610
    for i in range(n):
        k = abs(i - n // 2)
        a = env_at(t, -k // 2)
        a2 = env_at(t, -k // 3 - 1)
        hgt = 10 + 95 * (0.6 * a + 0.4 * a2) * (1 - k / (n * 0.95)) ** 0.7
        d.rounded_rectangle([x, cy - hgt / 2, x + bw, cy + hgt / 2], 7, fill=col)
        x += bw + gap


def subtitles(img, t, theme):
    cur = None
    for s, e, ch in CHUNKS:
        if s - 0.02 <= t < e:
            cur = (s, e, ch)
            break
    if not cur:
        return
    s, e, ch = cur
    lay = layer()
    d = ImageDraw.Draw(lay)
    pin = ease_back(prog(t, s, 0.22))
    sc = 0.86 + 0.14 * pin
    fs = 80 * sc
    f = font(fs)
    gap = 22 * sc
    # wrap
    lines, line, lw = [], [], 0
    for w in ch:
        ww = f.getlength(w["text"])
        if line and lw + gap + ww > 940:
            lines.append((line, lw))
            line, lw = [], 0
        lw += (gap if line else 0) + ww
        line.append((w, ww))
    lines.append((line, lw))
    lh = fs * 1.32
    y0 = 1350 - (len(lines) - 1) * lh / 2
    light_bg = theme in ("gold", "cream")
    base = INK if light_bg else WHITE
    hi_text = GREEN_M if light_bg else GOLD
    box_fill = INK if light_bg else GOLD
    box_text = GOLD_L if light_bg else INK
    for li, (ln, lw) in enumerate(lines):
        x = W / 2 - lw / 2
        y = y0 + li * lh
        for w, ww in ln:
            key = w["n"] in KEYWORDS
            active = w["s"] <= t < w["e"] + 0.05
            if key and active:
                pad = 16
                rrect(d, [x - pad, y - fs * 0.62, x + ww + pad, y + fs * 0.62], 22, fill=box_fill)
                d.text((x, y), w["text"], font=f, fill=box_text, anchor="lm")
            elif key:
                d.text((x, y), w["text"], font=f, fill=hi_text, anchor="lm",
                       stroke_width=0 if light_bg else 4, stroke_fill=INK)
            else:
                d.text((x, y), w["text"], font=f, fill=base, anchor="lm",
                       stroke_width=0 if light_bg else 5, stroke_fill=INK)
            x += ww + gap
    fade = clamp((e - t) / 0.12)
    paste_alpha(img, lay, min(1, prog(t, s, 0.1)) * fade)


# ---- Scene ----
def scene1(t):
    img = bg(GREEN_D, GREEN_M, t, drift=1.0)
    lay = layer()
    d = ImageDraw.Draw(lay)
    # label kecil + INTEGRITI besar
    a = ease_out(prog(t, 0.1, 0.4))
    text_c(d, (W / 2, 520 + (1 - a) * 30), "STAFF YANG", font(64, "Bold"), CREAM)
    p = ease_back(prog(t, 0.45, 0.55))
    fs = 150 * max(p, 0.01)
    text_c(d, (W / 2, 690), "INTEGRITI", font(fs), GOLD, stroke=0)
    # garis bawah
    u = ease_out(prog(t, 1.2, 0.5))
    wu = 760 * u
    d.rounded_rectangle([W / 2 - wu / 2, 790, W / 2 + wu / 2, 802], 6, fill=GOLD_L)
    # dua pil
    def pill(y, s, key, t0, hi=False):
        pp = ease_back(prog(t, t0, 0.45))
        if pp <= 0:
            return
        f = font(44, "ExtraBold")
        wtxt = f.getlength(s)
        bw = wtxt + 150
        off = (1 - pp) * 120
        x0 = W / 2 - bw / 2
        rrect(d, [x0, y - 55 + off, x0 + bw, y + 55 + off], 55, fill=GOLD if hi else GREEN_L, outline=GOLD, width=4)
        # tanda semak
        cx, cy = x0 + 62, y + off
        d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=INK if hi else GOLD)
        d.line([(cx - 11, cy), (cx - 3, cy + 10), (cx + 13, cy - 9)], fill=GOLD if hi else INK, width=7)
        text_c(d, (x0 + 105 + wtxt / 2, y + off), s, f, INK if hi else CREAM)
    pill(950, "BAIK DALAM PEKERJAAN", "", wstart("pekerjaan", 0) - 0.5)
    pill(1065, "BAIK DALAM AMANAH KEPADA ALLAH", "", wstart("amanahnya", 0) - 0.4, hi=True)
    img.alpha_composite(lay)
    return img


def scene2(t):
    img = bg(CREAM, (238, 226, 192), t, dark_pat=True, drift=0.8)
    lay = layer()
    d = ImageDraw.Draw(lay)
    t0 = 8.1
    a = ease_out(prog(t, t0, 0.4))
    text_c(d, (W / 2, 440 + (1 - a) * 30), "USTAZ & USTAZAH", font(66), GREEN_M)
    # kad 1: menyampaikan ilmu (dicoret)
    p1 = ease_back(prog(t, t0 + 1.0, 0.45))
    if p1 > 0:
        y = 600 + (1 - p1) * 100
        rrect(d, [110, y - 90, W - 110, y + 90], 40, fill=WHITE, outline=GREEN_M, width=4)
        text_c(d, (W / 2, y), "MENYAMPAIKAN ILMU", font(60), GREEN_M)
        s = ease_out(prog(t, wstart("bukan", 1) + 0.2, 0.35))
        if s > 0:
            ww = font(60).getlength("MENYAMPAIKAN ILMU")
            x0, x1 = W / 2 - ww / 2 - 20, W / 2 + ww / 2 + 20
            d.line([(x0, y), (x0 + (x1 - x0) * s, y)], fill=(190, 50, 50), width=10)
        text_c(d, (W / 2, y + 125), "bukan sekadar", font(40, "Bold"), (120, 100, 70))
    # anak panah
    p2 = prog(t, wstart("tetapi", 1) - 0.2, 0.3)
    if p2 > 0:
        d.polygon([(W / 2 - 40, 745), (W / 2 + 40, 745), (W / 2, 745 + 60 * ease_out(p2))], fill=GREEN_M)
    # kad 2: menjadi contoh
    p3 = ease_back(prog(t, wstart("menjadi", 1) - 0.1, 0.5))
    if p3 > 0:
        y = 960 + (1 - p3) * 120
        rrect(d, [90, y - 130, W - 90, y + 130], 50, fill=GREEN_M)
        rrect(d, [90, y - 130, W - 90, y + 130], 50, outline=GOLD, width=6)
        person(d, 260, y + 10, 150, GOLD)
        text_c(d, (640, y - 45), "MENJADI", font(54, "Bold"), CREAM)
        text_c(d, (640, y + 40), "CONTOH", font(100), GOLD)
    img.alpha_composite(lay)
    return img


def scene3(t):
    img = bg(GREEN_M, GREEN_D, t, drift=-1.2)
    lay = layer()
    d = ImageDraw.Draw(lay)
    a = ease_out(prog(t, 15.6, 0.4))
    text_c(d, (W / 2, 420 + (1 - a) * 30), "4 NILAI TERAS", font(64, "Bold"), CREAM)
    rows = [
        ("JUJUR", "dalam tugas", wstart("jujur"), wstart("jujur") + 1.5),
        ("AMANAH", "dalam tanggungjawab", wstart("amanah", 2), wstart("amanah", 2) + 1.9),
        ("ADAB", "sentiasa dijaga", wstart("adab"), wstart("adab") + 1.0),
        ("IKHLAS", "dalam berdakwah", wstart("ikhlas"), wstart("ikhlas") + 1.8),
    ]
    for i, (k, sub, t0, t1) in enumerate(rows):
        p = ease_back(prog(t, t0 - 0.25, 0.45))
        if p <= 0:
            continue
        y = 555 + i * 160 + (1 - p) * 50
        active = t0 - 0.1 <= t < t1 + 0.5
        fill = GOLD if active else GREEN_L
        txtc = INK if active else CREAM
        rrect(d, [90, y - 70, W - 90, y + 70], 40, fill=fill, outline=GOLD, width=4)
        cx = 190
        d.ellipse([cx - 45, y - 45, cx + 45, y + 45], fill=INK if active else GOLD)
        text_c(d, (cx, y), str(i + 1), font(48), GOLD if active else INK)
        text_c(d, (290, y - 14), k, font(64), txtc, anchor="lm")
        text_c(d, (292, y + 38), sub, font(34, "Medium"), txtc, anchor="lm")
    img.alpha_composite(lay)
    return img


def scene4(t):
    img = bg((10, 52, 60), (6, 26, 36), t, drift=0.6)
    lay = layer()
    d = ImageDraw.Draw(lay)
    t0 = 24.2
    a = ease_out(prog(t, t0, 0.4))
    # orang ramai (titik) memerhati
    n = 9
    for i in range(n):
        pp = ease_back(prog(t, t0 + 0.3 + i * 0.07, 0.4))
        if pp <= 0:
            continue
        cx = 150 + i * (W - 300) / (n - 1)
        person(d, cx, 1000 + (1 - pp) * 60, 62 * pp, (60, 120, 130))
    # mata besar
    look = math.sin((t - t0) * 2.2) * 0.9
    blink = max(0, 1 - abs(((t - t0) % 2.4) - 2.2) / 0.1) if ((t - t0) % 2.4) > 2.1 else 0
    eye(d, W / 2, 640 + (1 - a) * 20, 700 * (0.5 + 0.5 * ease_back(prog(t, t0, 0.5))), 330, look=look, closed=blink * 0.95)
    text_c(d, (W / 2, 880), "DI HADAPAN MANUSIA", font(56, "ExtraBold"), CREAM)
    img.alpha_composite(lay)
    return img


def scene5(t):
    img = bg((4, 18, 16), (2, 8, 8), t, drift=0.3)
    lay = layer()
    d = ImageDraw.Draw(lay)
    t0 = 29.9
    # cahaya spotlight berdenyut
    pul = 0.5 + 0.5 * math.sin((t - t0) * 2.0)
    for r, al in ((620, 22), (480, 30), (340, 44)):
        rr = r + 25 * pul
        d.ellipse([W / 2 - rr, 780 - rr, W / 2 + rr, 780 + rr], fill=GOLD + (al,))
    p = ease_out(prog(t, t0, 0.5))
    closed = ease_out(prog(t, wstart('tiada') - 0.1, 0.45))
    eye(d, W / 2, 690, 620 * p, 290, iris=GOLD, look=0, closed=closed, fillc=(40, 60, 55), line=(120, 110, 70))
    # garis serong "tidak dilihat"
    sl = ease_out(prog(t, wstart("tiada") - 0.2, 0.35))
    if sl > 0:
        d.line([(W / 2 - 300, 560), (W / 2 - 300 + 600 * sl, 560 + 260 * sl)], fill=(210, 70, 70), width=16)
    # diri sebenar bercahaya
    q = ease_back(prog(t, wstart("diri") - 0.1, 0.5))
    if q > 0:
        person(d, W / 2, 1040, 120 * q, GOLD)
    lab = "TIADA SIAPA MELIHAT" if t >= wstart("tiada") - 0.1 else "DIRI SEBENAR"
    text_c(d, (W / 2, 880), lab, font(54, "ExtraBold"), (230, 210, 150))
    img.alpha_composite(lay)
    return img


def scene6(t):
    img = bg(GOLD, (200, 150, 40), t, dark_pat=True, drift=1.5)
    lay = layer()
    d = ImageDraw.Draw(lay)
    t0 = 34.6
    a = ease_out(prog(t, t0, 0.4))
    text_c(d, (W / 2, 470 + (1 - a) * 30), "NILAI SEORANG", font(60, "Bold"), INK)
    p = ease_back(prog(t, t0 + 0.2, 0.55))
    text_c(d, (W / 2, 640), "PENDIDIK", font(170 * max(p, 0.01)), INK)
    q = ease_back(prog(t, wstart("berintegriti", 6) - 0.2, 0.55))
    if q > 0:
        bw = 900 * q
        rrect(d, [W / 2 - bw / 2, 800, W / 2 + bw / 2, 960], 60, fill=INK)
        if q > 0.6:
            text_c(d, (W / 2, 880), "BERINTEGRITI", font(100), GOLD)
    h = ease_out(prog(t, 36.6, 0.5))
    if h > 0:
        text_c(d, (W / 2, 1060 + (1 - h) * 20), "@gengngajiglobal", font(46, "Bold"), INK)
    img.alpha_composite(lay)
    return img


SCENES = [scene1, scene2, scene3, scene4, scene5, scene6]
THEMES = ["dark", "cream", "dark", "dark", "dark", "gold"]


def frame(i):
    t = i / FPS
    k = 0
    for j in range(6):
        if SCENE_T[j] <= t < SCENE_T[j + 1]:
            k = j
    img = SCENES[k](t)
    theme = THEMES[k]
    # crossfade ke scene berikut
    if k < 5 and t > SCENE_T[k + 1] - XF:
        x = (t - (SCENE_T[k + 1] - XF)) / XF
        nxt = SCENES[k + 1](t)
        img = Image.blend(img, nxt, ease_out(x))
        theme = THEMES[k + 1] if x > 0.5 else theme
    chrome(img, t, theme)
    subtitles(img, t, theme)
    waveform(img, t, theme)
    # kilat emas pada peralihan
    for b in SCENE_T[1:6]:
        dt = t - b
        if 0 <= dt < 0.25:
            ov = Image.new("RGBA", (W, H), GOLD_L + (int(70 * (1 - dt / 0.25)),))
            img.alpha_composite(ov)
    return np.asarray(img.convert("RGB")).tobytes()


def main():
    total = int(round(DUR * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", AUDIO, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{DUR:.2f}",
           "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for n, buf in enumerate(pool.imap(frame, range(total), chunksize=4)):
            p.stdin.write(buf)
            if n % 100 == 0:
                print(f"{n}/{total}", flush=True)
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[3] == "still":
        for tt in sys.argv[4:]:
            Image.frombytes("RGB", (W, H), frame(int(float(tt) * FPS))).save(f"still_{tt}.png")
    else:
        main()
