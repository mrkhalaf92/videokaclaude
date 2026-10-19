#!/usr/bin/env python3
"""Video TikTok 31s (1080x1920): Circle Time - Halaqah (Geng Ngaji Global).

Guna: python3 build_circle_time.py <audio.wav> <output.mp4> [still <saat>...]
Guna semula helper dalam build_video.py.
"""
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw

import build_video as bv
from build_video import (CREAM, FPS, GOLD, GOLD_L, GREEN_D, GREEN_L, GREEN_M, H, INK, W, WHITE,
                         clamp, ease_back, ease_out, font, layer, lerp, norm, paste_alpha, prog,
                         rrect, text_c)

AUDIO, OUT = sys.argv[1], sys.argv[2]
DUR = 31.24
bv.DUR = DUR  # untuk progress bar dalam chrome()

# (mula, tamat, penutur, teks) - penutur U=Ustaz, P=Pelajar
LINES = [
    (0.22, 2.59, "U", "Assalamualaikum semua!"),
    (3.03, 5.24, "P", "Waalaikumussalam!"),
    (5.62, 7.90, "U", "Sebelum kita mula belajar hari ni,"),
    (8.10, 9.96, "U", "jom kita baca doa belajar sama-sama."),
    (10.94, 12.96, "P", "Baik ustazz!"),
    (13.59, 15.43, "U", "Okay, kalau ustaz kata…"),
    (15.71, 16.47, "U", "Halaqah!"),
    (16.99, 18.05, "P", "Ya Bunayya!"),
    (18.48, 20.37, "U", "Kalau ustaz kata… Best tak!"),
    (20.89, 21.71, "P", "Seronok!"),
    (22.48, 24.88, "U", "Haa, macam ni baru semangat!"),
    (25.22, 26.00, "U", "Hari ni semua okay?"),
    (26.43, 27.44, "U", "Dah bersedia nak belajar?"),
    (27.75, 28.41, "P", "Dahhh!"),
    (28.91, 30.00, "U", "Alhamdulillah."),
    (30.20, 30.87, "U", "Jom kita mula!"),
]
KEYWORDS = {"assalamualaikum", "waalaikumussalam", "doa", "belajar", "halaqah", "bunayya", "best",
            "seronok", "semangat", "dahhh", "alhamdulillah", "mula"}
SCENE_T = [0, 5.4, 13.2, 18.25, 22.1, 28.65, DUR + 1]
THEMES = ["dark", "dark", "cream", "gold", "dark", "gold"]
XF = 0.5
CORAL = (232, 112, 92)

# ---- masa perkataan ----
WORDS = []
for li, (a, b, spk, text) in enumerate(LINES):
    toks = text.split()
    wts = [len(norm(t)) + 2 + (3 if t[-1] in ",…" else 0) for t in toks]
    tot, t = sum(wts), a
    for tok, wt in zip(toks, wts):
        d = (b - a) * wt / tot
        WORDS.append(dict(line=li, spk=spk, text=tok, n=norm(tok), s=t, e=t + d))
        t += d


def ws(n, line=None):
    return [w for w in WORDS if w["n"] == n and (line is None or w["line"] == line)][0]["s"]


def build_chunks():
    chunks = []
    for li in range(len(LINES)):
        cur = []
        for w in [x for x in WORDS if x["line"] == li]:
            cur.append(w)
            if len(cur) >= 4 or w["text"][-1] in ",…" or (len(cur) >= 2 and len(" ".join(x["text"] for x in cur)) > 20):
                chunks.append(cur)
                cur = []
        if cur:
            if chunks and chunks[-1][0]["line"] == li and len(cur) == 1:
                chunks[-1].extend(cur)
            else:
                chunks.append(cur)
    out = []
    for i, ch in enumerate(chunks):
        s = ch[0]["s"]
        nxt = chunks[i + 1][0] if i + 1 < len(chunks) else None
        e = nxt["s"] if nxt and nxt["line"] == ch[0]["line"] else ch[-1]["e"] + 0.45
        out.append((s, e, ch))
    return out


CHUNKS = build_chunks()


def speaker(t):
    for a, b, spk, _ in LINES:
        if a - 0.05 <= t < b + 0.25:
            return spk
    return None


# ---- lukisan ----
SKINS = [(236, 190, 150), (214, 160, 118), (178, 124, 90), (245, 205, 170)]


def avatar(d, cx, cy, s, kind, skin, cloth, hat, bounce=0.0, glow=0.0, ustaz=False):
    cy = cy - bounce
    if glow > 0:
        r = s * (1.15 + 0.1 * glow)
        d.ellipse([cx - r, cy - r * 0.9, cx + r, cy + r * 1.7], fill=GOLD + (int(70 * glow),))
    if kind == "tudung":
        d.ellipse([cx - .6 * s, cy - .58 * s, cx + .6 * s, cy + .7 * s], fill=hat)
    d.pieslice([cx - .75 * s, cy + .4 * s, cx + .75 * s, cy + 2.1 * s], 180, 360, fill=cloth)
    if ustaz:
        d.pieslice([cx - .3 * s, cy + .4 * s, cx + .3 * s, cy + .95 * s], 180, 360, fill=GOLD)
    if kind == "tudung":
        d.pieslice([cx - .62 * s, cy + .3 * s, cx + .62 * s, cy + 1.3 * s], 180, 360, fill=hat)
    d.ellipse([cx - .45 * s, cy - .45 * s, cx + .45 * s, cy + .45 * s], fill=skin)
    if kind == "peci":
        d.polygon([(cx - .46 * s, cy - .18 * s), (cx + .46 * s, cy - .18 * s), (cx + .38 * s, cy - .62 * s), (cx - .38 * s, cy - .62 * s)], fill=hat)
    elif kind == "tudung":
        d.pieslice([cx - .5 * s, cy - .52 * s, cx + .5 * s, cy + .4 * s], 180, 360, fill=hat)
        d.ellipse([cx - .3 * s, cy - .22 * s, cx + .3 * s, cy + .4 * s], fill=skin)
    for sx in (-1, 1):
        d.ellipse([cx + sx * .16 * s - .05 * s, cy - .02 * s - .05 * s, cx + sx * .16 * s + .05 * s, cy - .02 * s + .05 * s], fill=INK)
    d.arc([cx - .2 * s, cy - .02 * s, cx + .2 * s, cy + .26 * s], 25, 155, fill=INK, width=max(2, int(s * .05)))


KIDS = [("peci", GREEN_L, INK), ("tudung", CORAL, (236, 150, 120)), ("peci", (60, 110, 170), WHITE), ("tudung", GOLD, (240, 214, 120)),
        ("peci", CORAL, INK), ("tudung", (60, 110, 170), (120, 160, 210)), ("peci", GOLD, WHITE), ("tudung", GREEN_L, (110, 190, 150))]


def circle_group(lay, t, cx=540, cy=800, rx=380, ry=190, s=78, force_bounce=False):
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - rx - 70, cy - ry - 30, cx + rx + 70, cy + ry + 150], outline=GOLD + (120,), width=6)
    spk = speaker(t)
    pelajar_bounce = spk == "P" or force_bounce
    items = []
    for i in range(8):
        a = math.pi * 2 * i / 8 + math.pi / 8
        items.append((cy + math.sin(a) * ry, cx + math.cos(a) * rx, i))
    for y, x, i in sorted(items):
        kind, cloth, hat = KIDS[i]
        b = 0.0
        if pelajar_bounce:
            b = abs(math.sin(t * 9 + i * 0.7)) * 22
        pop = ease_back(prog(t, 0.2 + i * 0.12, 0.5))
        if pop <= 0:
            continue
        avatar(d, x, y + (1 - pop) * 60, s * pop, kind, SKINS[i % 4], cloth, hat, bounce=b, glow=0.7 if pelajar_bounce else 0)
    ub = abs(math.sin(t * 7)) * 14 if spk == "U" else 0
    avatar(d, cx, cy - 20, 118, "peci", SKINS[0], WHITE, INK, bounce=ub, glow=0.9 if spk == "U" else 0, ustaz=True)


def star(d, cx, cy, r1, r2, n, rot, fill):
    pts = []
    for k in range(n * 2):
        r = r1 if k % 2 == 0 else r2
        a = rot + k * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=fill)


def confetti(d, t, t0, n=46):
    cols = [GOLD, CREAM, CORAL, GREEN_L, (60, 110, 170)]
    for i in range(n):
        sd = (i * 7919) % 1000 / 1000
        x = 60 + ((i * 131) % 960)
        sp = 260 + sd * 280
        y = -80 + ((t - t0) * sp + sd * 600) % 1100 if t > t0 else -100
        if t > t0:
            c = cols[i % 5]
            a = (t - t0) * 4 + i
            w_, h_ = 22, 12
            pts = [(x + math.cos(a) * w_ - math.sin(a) * 0, y + math.sin(a) * w_ * .5), (x + math.cos(a + 1.6) * h_, y + math.sin(a + 1.6) * h_),
                   (x - math.cos(a) * w_, y - math.sin(a) * w_ * .5), (x - math.cos(a + 1.6) * h_, y - math.sin(a + 1.6) * h_)]
            d.polygon(pts, fill=c)


def sparkles(d, t, n=18):
    for i in range(n):
        x = 80 + (i * 173) % 920
        y = 1150 - ((t * (30 + (i % 5) * 12) + i * 90) % 800)
        r = 6 + (i % 4) * 3
        a = 0.5 + 0.5 * math.sin(t * 3 + i)
        star(d, x, y, r * 1.8, r * .5, 4, 0.0, GOLD_L + (int(40 + 120 * a),))


def book(d, cx, cy, w, h, col, page):
    d.polygon([(cx, cy - h * .35), (cx - w / 2, cy - h * .5), (cx - w / 2, cy + h * .4), (cx, cy + h * .5)], fill=page, outline=col)
    d.polygon([(cx, cy - h * .35), (cx + w / 2, cy - h * .5), (cx + w / 2, cy + h * .4), (cx, cy + h * .5)], fill=page, outline=col)
    d.line([(cx, cy - h * .35), (cx, cy + h * .5)], fill=col, width=8)
    for k in range(4):
        yy = cy - h * .22 + k * h * .15
        d.line([(cx - w * .42, yy - h * .03), (cx - w * .08, yy + h * .03)], fill=col, width=6)
        d.line([(cx + w * .08, yy + h * .03), (cx + w * .42, yy - h * .03)], fill=col, width=6)


def hands(d, cx, cy, s, col):
    for sx in (-1, 1):
        pts = [(cx + sx * .06 * s, cy + .5 * s), (cx + sx * .62 * s, cy + .35 * s), (cx + sx * .78 * s, cy - .3 * s),
               (cx + sx * .55 * s, cy - .38 * s), (cx + sx * .4 * s, cy - .05 * s), (cx + sx * .06 * s, cy + .05 * s)]
        d.polygon(pts, fill=col)


def pop_text(d, t, t0, xy, s, size, fill, dur=0.55, w="ExtraBold", stroke=0, sf=None):
    p = ease_back(prog(t, t0, dur))
    if p <= 0.01:
        return
    text_c(d, xy, s, font(size * p, w), fill, stroke=stroke, stroke_fill=sf)


# ---- babak ----
def sc1(t):
    img = bv.bg(GREEN_D, GREEN_M, t, drift=0.8)
    lay = layer()
    d = ImageDraw.Draw(lay)
    a = ease_out(prog(t, 0.3, 0.7))
    text_c(d, (W / 2, 395 + (1 - a) * 30), "CIRCLE TIME", font(86), GOLD)
    text_c(d, (W / 2, 485 + (1 - a) * 30), "Ustaz & Pelajar", font(44, "Medium"), CREAM)
    circle_group(lay, t)
    img.alpha_composite(lay)
    return img


def sc2(t):
    img = bv.bg((52, 36, 14), GREEN_D, t, drift=0.5)
    lay = layer()
    d = ImageDraw.Draw(lay)
    sparkles(d, t)
    t0 = ws("doa", 3) - 0.9
    p = ease_back(prog(t, t0, 0.7))
    if p > 0:
        y = 410 + (1 - p) * 80
        rrect(d, [150, y - 95, W - 150, y + 95], 48, fill=GOLD)
        book(d, 285, y + 4, 150 * min(1, p), 100 * min(1, p), GREEN_D, CREAM)
        text_c(d, (640, y - 24), "DOA", font(56, "Bold"), INK)
        text_c(d, (640, y + 38), "BELAJAR", font(76), INK)
    circle_group(lay, t, cy=870)
    img.alpha_composite(lay)
    return img


def sc3(t):
    img = bv.bg(CREAM, (238, 226, 192), t, dark_pat=True, drift=0.7)
    lay = layer()
    d = ImageDraw.Draw(lay)
    a = ease_out(prog(t, 13.6, 0.6))
    text_c(d, (W / 2, 420 + (1 - a) * 30), "KALAU USTAZ KATA…", font(60, "Bold"), GREEN_M)
    p1 = ease_back(prog(t, ws("halaqah") - 0.1, 0.6))
    if p1 > 0:
        y = 640 + (1 - p1) * 100
        rrect(d, [90, y - 130, W - 90, y + 130], 60, fill=GREEN_M, outline=GOLD, width=6)
        avatar(d, 235, y - 10, 70 * p1, "peci", SKINS[0], WHITE, INK, ustaz=True)
        text_c(d, (650, y), "HALAQAH!", font(104 * min(1, p1)), GOLD)
    p2 = ease_back(prog(t, ws("bunayya") - 0.1, 0.6))
    if p2 > 0:
        y = 960 + (1 - p2) * 100
        rrect(d, [90, y - 130, W - 90, y + 130], 60, fill=GOLD, outline=INK, width=6)
        for k, (x, i) in enumerate(((190, 0), (275, 1), (360, 2))):
            kind, cloth, hat = KIDS[i]
            avatar(d, x, y + 10 - abs(math.sin(t * 9 + k)) * 18, 50 * p2, kind, SKINS[i % 4], cloth, hat)
        text_c(d, (700, y), "YA BUNAYYA!", font(70 * min(1, p2)), INK)
    img.alpha_composite(lay)
    return img


def sc4(t):
    img = bv.bg(GOLD, (200, 150, 40), t, dark_pat=True, drift=1.3)
    lay = layer()
    d = ImageDraw.Draw(lay)
    t1, t2 = ws("best"), ws("seronok")
    sb = ease_out(prog(t, t1, 0.6))
    if sb > 0:
        star(d, W / 2, 560, 330 * sb, 240 * sb, 14, t * 0.4, (255, 233, 170, 150))
    pop_text(d, t, t1 - 0.1, (W / 2, 560), "BEST TAK!", 118, INK)
    if t >= t2 - 0.1:
        star(d, W / 2, 985, 270, 200, 16, -t * 0.6, GREEN_M + (255,))
        pop_text(d, t, t2 - 0.1, (W / 2, 985), "SERONOK!", 88, GOLD_L)
        confetti(d, t, t2 - 0.1)
    img.alpha_composite(lay)
    return img


def sc5(t):
    img = bv.bg(GREEN_D, GREEN_M, t, drift=0.9)
    lay = layer()
    d = ImageDraw.Draw(lay)
    a = ease_out(prog(t, 22.4, 0.5))
    t3 = ws("dahhh")
    if t < t3 - 0.1:
        text_c(d, (W / 2, 370 + (1 - a) * 20), "SEMANGAT", font(60, "Bold"), CREAM)
        fill = ease_out(prog(t, ws("macam") - 0.1, 2.2))
        rrect(d, [140, 420, W - 140, 480], 30, fill=GREEN_L)
        if fill > 0:
            rrect(d, [140, 420, 140 + (W - 280) * fill, 480], 30, fill=GOLD)
    circle_group(lay, t, cy=900, force_bounce=22.3 <= t < 25.0 or 27.7 <= t < 28.7)
    if t >= t3 - 0.1:
        star(d, W / 2, 610, 300 * ease_out(prog(t, t3, .4)), 225 * ease_out(prog(t, t3, .4)), 14, t * 0.8, GOLD + (255,))
        pop_text(d, t, t3 - 0.1, (W / 2, 610), "DAHHH!", 86, INK)
    img.alpha_composite(lay)
    return img


def sc6(t):
    img = bv.bg(GOLD, (200, 150, 40), t, dark_pat=True, drift=1.5)
    lay = layer()
    d = ImageDraw.Draw(lay)
    p = ease_back(prog(t, 28.8, 0.7))
    if p > 0:
        book(d, W / 2, 560, 560 * p, 330 * p, INK, CREAM)
    pop_text(d, t, ws("alhamdulillah") - 0.1, (W / 2, 840), "ALHAMDULILLAH", 92, INK)
    t2 = ws("mula")
    if t >= t2 - 0.1:
        q = ease_back(prog(t, t2 - 0.1, 0.55))
        bw = 760 * q
        rrect(d, [W / 2 - bw / 2, 930, W / 2 + bw / 2, 1070], 60, fill=INK)
        if q > 0.6:
            text_c(d, (W / 2, 1000), "JOM MULA!", font(86), GOLD)
    img.alpha_composite(lay)
    return img


SCENES = [sc1, sc2, sc3, sc4, sc5, sc6]


# ---- subtitle ----
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
    light = theme in ("gold", "cream")
    base = INK if light else WHITE
    hi_text = GREEN_M if light else GOLD
    box_fill = INK if light else GOLD
    box_text = GOLD_L if light else INK
    pin = ease_back(prog(t, s, 0.28))
    sc = 0.86 + 0.14 * pin
    fs = 80 * sc
    f = font(fs)
    gap = 22 * sc
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
    for li, (ln, lw) in enumerate(lines):
        x = W / 2 - lw / 2
        y = y0 + li * lh
        for w, ww in ln:
            key = w["n"] in KEYWORDS and not (w["n"] == "mula" and w["line"] != len(LINES) - 1)
            active = w["s"] <= t < w["e"] + 0.05
            if key and active:
                rrect(d, [x - 16, y - fs * .62, x + ww + 16, y + fs * .62], 22, fill=box_fill)
                d.text((x, y), w["text"], font=f, fill=box_text, anchor="lm")
            elif key:
                d.text((x, y), w["text"], font=f, fill=hi_text, anchor="lm", stroke_width=0 if light else 4, stroke_fill=INK)
            else:
                d.text((x, y), w["text"], font=f, fill=base, anchor="lm", stroke_width=0 if light else 5, stroke_fill=INK)
            x += ww + gap
    # label penutur
    spk = ch[0]["spk"]
    lab = "USTAZ" if spk == "U" else "PELAJAR"
    lf = font(36, "Bold")
    lwid = lf.getlength(lab) + 70
    ly = y0 - lh * .5 - 62
    if spk == "U":
        rrect(d, [W / 2 - lwid / 2, ly - 30, W / 2 + lwid / 2, ly + 30], 30, fill=INK if light else GOLD)
        text_c(d, (W / 2, ly), lab, lf, GOLD_L if light else INK)
    else:
        rrect(d, [W / 2 - lwid / 2, ly - 30, W / 2 + lwid / 2, ly + 30], 30, outline=INK if light else CREAM, width=4)
        text_c(d, (W / 2, ly), lab, lf, INK if light else CREAM)
    fade = clamp((e - t) / 0.15)
    paste_alpha(img, lay, min(1, prog(t, s, 0.12)) * fade)


def frame(i):
    t = i / FPS
    k = 0
    for j in range(6):
        if SCENE_T[j] <= t < SCENE_T[j + 1]:
            k = j
    img = SCENES[k](t)
    theme = THEMES[k]
    if k < 5 and t > SCENE_T[k + 1] - XF:
        x = (t - (SCENE_T[k + 1] - XF)) / XF
        img = Image.blend(img, SCENES[k + 1](t), ease_out(x))
        theme = THEMES[k + 1] if x > 0.5 else theme
    bv.chrome(img, t, theme)
    subtitles(img, t, theme)
    bv.waveform(img, t, theme)
    return np.asarray(img.convert("RGB")).tobytes()


def main():
    total = int(round(DUR * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", AUDIO, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{DUR:.2f}", "-movflags", "+faststart", OUT]
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
