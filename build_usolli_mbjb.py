#!/usr/bin/env python3
"""Video TikTok ~46s (1080x1920): Usolli korporat - Majlis Bandaraya Johor Bahru, 28/10/2026.

Guna: python3 build_usolli_mbjb.py <dir_sumber> <output.mp4>
      python3 build_usolli_mbjb.py <dir_sumber> still <saat>...
dir_sumber mengandungi gambar (<id>-image.jpg) dan klip (<id>-VID*.mp4) yang dimuat naik.
Frame klip diekstrak sekali ke ./_cache_usolli (30fps, sudah diputar ke portrait).
"""
import glob
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SR = 48000
SRC = sys.argv[1]
CACHE = os.path.abspath("_cache_usolli")

NAVY = (12, 28, 58)
TEAL = (52, 168, 160)
YELLOW = (255, 210, 40)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

FD = "/usr/share/fonts/opentype/inter/"
_fc = {}


def font(size, w="Black"):
    k = (int(size), w)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(f"{FD}Inter-{w}.otf", k[0])
    return _fc[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


# ---- sumber ----
def photo_path(pid):
    return glob.glob(os.path.join(SRC, f"{pid}-image.jpg"))[0]


def clip_path(cid):
    return glob.glob(os.path.join(SRC, f"{cid}-VID*.mp4"))[0]


def prepare():
    os.makedirs(CACHE, exist_ok=True)
    for cid in CLIPS:
        d = os.path.join(CACHE, cid)
        if not os.path.isdir(d):
            os.makedirs(d)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip_path(cid), "-vf", f"fps={FPS},scale={W}:{H}",
                            "-q:v", "2", os.path.join(d, "%04d.jpg")], check=True)
        a = os.path.join(CACHE, f"{cid}.f32")
        if not os.path.exists(a):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", clip_path(cid), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                 capture_output=True, check=True).stdout
            open(a, "wb").write(raw)


_ph = {}


def photo(pid):
    if pid not in _ph:
        im = Image.open(photo_path(pid)).convert("RGB")
        s = max(W / im.width, H / im.height) * 1.35  # ruang untuk zoom
        if s < 1:
            im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        _ph[pid] = im
    return _ph[pid]


def clip_frame(cid, t):
    d = os.path.join(CACHE, cid)
    n = len(os.listdir(d))
    i = min(n, max(1, int(t * FPS) + 1))
    return Image.open(os.path.join(d, f"{i:04d}.jpg")).convert("RGB")


def cover(im, zoom, cx, cy):
    """Potong bingkai 9:16 dari im (zoom >= 1, pusat cx/cy dalam 0..1) dengan subpiksel."""
    s0 = max(W / im.width, H / im.height)
    ww, wh = W / (s0 * zoom), H / (s0 * zoom)
    x = clamp(cx * im.width - ww / 2, 0, im.width - ww)
    y = clamp(cy * im.height - wh / 2, 0, im.height - wh)
    return im.transform((W, H), Image.EXTENT, (x, y, x + ww, y + wh), Image.BILINEAR)


_fb = {}


def fit_blur(pid, z):
    """Gambar penuh (tanpa potong) di tengah, atas latar versi kabur yang sama."""
    if pid not in _fb:
        im = Image.open(photo_path(pid)).convert("RGB")
        bg = cover(im, 1.0, 0.5, 0.5).filter(ImageFilter.GaussianBlur(30))
        bg = Image.blend(bg, Image.new("RGB", (W, H), NAVY), 0.35)
        _fb[pid] = (im, bg)
    im, bg = _fb[pid]
    w = int(W * z)
    h = int(im.height * w / im.width)
    out = bg.copy()
    fg = im.resize((w, h), Image.BILINEAR)
    out.paste(fg, ((W - w) // 2, int(H * 0.45 - h / 2)))
    return out


# ---- shot ----
# kind, sumber, durasi, zoom (mula, akhir), pusat (mula, akhir), [mula audio klip]
CLIPS = ["84899d87", "021f9451", "b4b45a79"]
SHOTS = [
    dict(k="clip", s="84899d87", d=3.5, z=(1.0, 1.0), c=((0.5, 0.5), (0.5, 0.5)), a=0.0, punch=1.3),
    dict(k="photo", s="d8c44466", d=3.4, z=(0.96, 1.04), c=((0.5, 0.5), (0.5, 0.5)), fit=True),
    dict(k="photo", s="68822513", d=3.0, z=(1.0, 1.08), c=((0.32, 0.6), (0.5, 0.6))),
    dict(k="photo", s="bc5c8d62", d=2.4, z=(1.0, 1.06), c=((0.58, 0.55), (0.45, 0.55))),
    dict(k="photo", s="12a05b60", d=3.0, z=(1.0, 1.18), c=((0.5, 0.45), (0.55, 0.48))),
    dict(k="photo", s="6f98e4ab", d=2.2, z=(1.05, 1.15), c=((0.4, 0.5), (0.45, 0.6))),
    dict(k="clip", s="021f9451", d=4.8, z=(1.0, 1.08), c=((0.5, 0.5), (0.5, 0.45)), a=0.0),
    dict(k="photo", s="1e5b4bb9", d=3.0, z=(1.0, 1.12), c=((0.5, 0.6), (0.5, 0.52))),
    dict(k="photo", s="64eddb02", d=2.2, z=(1.0, 1.06), c=((0.35, 0.55), (0.55, 0.55))),
    dict(k="clip", s="84899d87", d=3.9, z=(1.04, 1.12), c=((0.5, 0.5), (0.5, 0.45)), a=3.5),
    dict(k="clip", s="b4b45a79", d=3.5, z=(1.0, 1.06), c=((0.5, 0.55), (0.5, 0.5)), a=0.3),
    dict(k="photo", s="3f5f8742", d=1.2, z=(1.0, 1.08), c=((0.6, 0.35), (0.6, 0.3)), xf=0.15),
    dict(k="photo", s="bb3cba42", d=1.2, z=(1.0, 1.08), c=((0.5, 0.65), (0.5, 0.6)), xf=0.15),
    dict(k="photo", s="e0a37003", d=1.2, z=(1.0, 1.08), c=((0.5, 0.45), (0.5, 0.4)), xf=0.15),
    dict(k="photo", s="8328f349", d=1.4, z=(1.0, 1.08), c=((0.45, 0.45), (0.45, 0.4))),
    dict(k="end", s="c393b46e", d=6.0),
]
t = 0.0
for sh in SHOTS:
    sh["t0"] = t
    t += sh["d"]
DUR = t
XF = 0.3


def T(i, off=0.0):
    return SHOTS[i]["t0"] + off


# ---- teks ----
# tajuk: (mula, tamat, [(teks, gaya)]) gaya: "w" putih berbayang, "y" hitam atas kotak kuning
TITLES = [
    (T(0, 0.05), T(1) - 0.1, [("DAH BERTAHUN SOLAT.", "w"), ("TAPI BETUL KE?", "y")]),
    (T(2, 0.2), T(4) - 0.1, [("20% teori.", "w"), ("80% praktikal.", "y")]),
    (T(4, 0.2), T(6) - 0.1, [("Setiap peserta", "w"), ("dibimbing satu per satu.", "y")]),
    (T(7, 0.2), T(9) - 0.1, [("Takbir sampai salam,", "w"), ("semua dikupas.", "y")]),
    (T(10, 0.2), T(11) - 0.1, [("Muslimin & muslimat,", "w"), ("semua turun praktikal.", "y")]),
    (T(11, 0.15), T(15) - 0.1, [("Suasana santai,", "w"), ("ilmunya padat.", "y")]),
]
LOWER = (T(1, 0.3), T(2) - 0.1, "Program Pemerkasaan Integriti", "Majlis Bandaraya Johor Bahru  ·  28/10/2026")

# subtitle suara asal: [(perkataan, mula, tamat)] dalam masa global; disemak dari transkripsi Whisper
SUBS = [
    [("Jangan,", T(0, 0.45), T(0, 0.9))],
    [("Angkat", T(0, 1.36), T(0, 1.84)), ("tangan", T(0, 1.84), T(0, 2.22)), ("dulu,", T(0, 2.22), T(0, 2.36))],
    [("baru", T(0, 2.36), T(0, 2.62)), ("bangun.", T(0, 2.62), T(0, 3.1))],
    [("Tadi", T(6, 2.1), T(6, 2.6)), ("ustaz", T(6, 2.6), T(6, 2.9)), ("beritahu", T(6, 2.9), T(6, 3.2)), ("apa?", T(6, 3.2), T(6, 3.5))],
    [("Waktu", T(6, 3.74), T(6, 4.3)), ("sujud.", T(6, 4.3), T(6, 4.75))],
    [("Itu", T(9, 0.7), T(9, 0.78)), ("tak", T(9, 0.78), T(9, 0.92)), ("dapat", T(9, 0.92), T(9, 1.1)),
     ("sunnah", T(9, 1.1), T(9, 1.5)), ("dia.", T(9, 1.5), T(9, 1.9))],
]


def shadow_text(img, xy, s, f, fill, anchor="mm", sh=6, blur=8, stroke=0):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text((xy[0], xy[1] + sh), s, font=f, fill=(0, 0, 0, 170), anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
    lay = lay.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(lay)
    ImageDraw.Draw(img).text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=BLACK)


def draw_title(img, t, t0, t1, lines):
    if not (t0 <= t < t1):
        return
    a = ease_out((t - t0) / 0.3) * clamp((t1 - t) / 0.2)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y = 300
    for i, (s, st) in enumerate(lines):
        p = ease_out((t - t0 - i * 0.18) / 0.3)
        if p <= 0:
            y += 120
            continue
        dy = (1 - p) * 40
        size = 72 if st == "w" else 68
        while font(size).getlength(s) > (900 if st == "w" else 860):
            size -= 2
        f = font(size)
        if st == "w":
            shadow_text(lay, (W / 2, y + dy), s, f, WHITE)
        else:
            d = ImageDraw.Draw(lay)
            x0, y0, x1, y1 = d.textbbox((W / 2, y + dy), s, font=f, anchor="mm")
            wbox = (x1 - x0 + 56) * ease_out((t - t0 - i * 0.18) / 0.25)
            d.rounded_rectangle([W / 2 - wbox / 2, y0 - 22 + dy * 0, W / 2 + wbox / 2, y1 + 22], radius=18, fill=YELLOW)
            if wbox > x1 - x0:
                d.text((W / 2, y + dy), s, font=f, fill=NAVY, anchor="mm")
        y += 120
    al = lay.getchannel("A").point(lambda v: int(v * a))
    lay.putalpha(al)
    img.alpha_composite(lay)


def draw_lower(img, t):
    t0, t1, l1, l2 = LOWER
    if not (t0 <= t < t1):
        return
    p = ease_out((t - t0) / 0.4)
    a = clamp((t1 - t) / 0.2)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = 60 - (1 - p) * 700
    y = 1240
    w1 = max(d.textlength(l1, font=font(50)), d.textlength(l2, font=font(34, "SemiBold"))) + 70
    d.rounded_rectangle([x, y, x + w1, y + 150], radius=20, fill=NAVY + (235,))
    d.rectangle([x, y, x + 12, y + 150], fill=TEAL)
    d.text((x + 40, y + 50), l1, font=font(50), fill=WHITE, anchor="lm")
    d.text((x + 40, y + 108), l2, font=font(34, "SemiBold"), fill=(200, 225, 230), anchor="lm")
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(lay)


def draw_subs(img, t):
    for ch in SUBS:
        s0, s1 = ch[0][1] - 0.08, ch[-1][2] + 0.3
        if not (s0 <= t < s1):
            continue
        p = ease_out((t - s0) / 0.18)
        f = font(int(66 * (0.92 + 0.08 * p)))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        sp = d.textlength(" ", font=f)
        rows, cur = [], []
        for item in ch:
            trial = cur + [item]
            if cur and sum(d.textlength(w, font=f) for w, _, _ in trial) + sp * (len(trial) - 1) > 900:
                rows.append(cur)
                cur = [item]
            else:
                cur = trial
        rows.append(cur)
        y = 1560 - (len(rows) - 1) * 44
        for row in rows:
            widths = [d.textlength(w, font=f) for w, _, _ in row]
            x = W / 2 - (sum(widths) + sp * (len(row) - 1)) / 2
            for (w, ws, we), wd in zip(row, widths):
                col = YELLOW if ws - 0.02 <= t < max(we, ws + 0.15) else WHITE
                d.text((x, y), w, font=f, fill=col, anchor="lm", stroke_width=7, stroke_fill=BLACK)
                x += wd + sp
            y += 88
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * min(1, p * 1.5) * clamp((s1 - t) / 0.15))))
        sh = lay.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.5))
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow.putalpha(sh)
        img.alpha_composite(shadow, (0, 6))
        img.alpha_composite(lay)


# ---- kad akhir ----
_end_bg = None


def end_card(t):
    global _end_bg
    if _end_bg is None:
        bg = cover(photo(SHOTS[-1]["s"]), 1.0, 0.5, 0.5).filter(ImageFilter.GaussianBlur(18))
        _end_bg = Image.blend(bg, Image.new("RGB", (W, H), NAVY), 0.72).convert("RGBA")
    img = _end_bg.copy()
    d = ImageDraw.Draw(img)

    def fade(i):
        return ease_out((t - 0.15 - i * 0.22) / 0.35)

    def put(i, xy, s, f, fill, anchor="mm"):
        p = fade(i)
        if p > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((xy[0], xy[1] + (1 - p) * 30), s, font=f, fill=fill, anchor=anchor)
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * p)))
            img.alpha_composite(lay)

    put(0, (W / 2, 470), "USOLLI", font(150), WHITE)
    put(0, (W / 2, 590), "Bimbingan Solat Sempurna", font(48, "SemiBold"), (170, 225, 220))
    if fade(1) > 0:
        w = 300 * fade(1)
        d.rectangle([W / 2 - w / 2, 670, W / 2 + w / 2, 676], fill=TEAL)
    put(1, (W / 2, 770), "Bengkel solat untuk organisasi", font(58, "ExtraBold"), WHITE)
    items = ["50 peserta setiap sesi", "Untuk agensi kerajaan & swasta", "HRD Claimable (swasta)"]
    for k, s in enumerate(items):
        y = 900 + k * 95
        p = fade(2 + k)
        if p > 0:
            d.ellipse([110, y - 13, 136, y + 13], fill=TEAL)
        put(2 + k, (160, y), s, font(43, "SemiBold"), WHITE, anchor="lm")
    p = fade(5)
    if p > 0:
        k = 0.9 + 0.1 * ease_out((t - 1.4) / 0.3)
        pw, ph = 760 * k, 130 * k
        pulse = 1 + 0.03 * math.sin(max(0, t - 2.0) * 5)
        pw, ph = pw * pulse, ph * pulse
        d.rounded_rectangle([W / 2 - pw / 2, 1290 - ph / 2, W / 2 + pw / 2, 1290 + ph / 2], radius=ph / 2, fill=YELLOW)
        d.text((W / 2, 1290), "Tempah tarikh · link di bio", font=font(int(52 * k)), fill=NAVY, anchor="mm")
    put(6, (W / 2, 1420), "@gengngajiglobal", font(40, "SemiBold"), (200, 210, 225))
    return img


# ---- render ----
_vig = None


def grade(img):
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        _vig = (1 - 0.35 * np.clip(r - 0.45, 0, 1) ** 1.4)[..., None].astype(np.float32)
    a = np.asarray(img).astype(np.float32) / 255
    a = np.clip((a - 0.5) * 1.08 + 0.5, 0, 1)  # kontras
    g = a.mean(axis=2, keepdims=True)
    a = np.clip(g + (a - g) * 1.1, 0, 1)  # saturasi
    a = a * _vig
    return Image.fromarray((a * 255).astype(np.uint8))


def shot_img(i, lt):
    sh = SHOTS[i]
    if sh["k"] == "end":
        return end_card(lt)
    p = ease_io(lt / sh["d"])
    z = sh["z"][0] + (sh["z"][1] - sh["z"][0]) * p
    if "punch" in sh:  # punch-in zoom pada titik penting
        z *= 1 + 0.16 * ease_out((lt - sh["punch"]) / 0.25)
    (cx0, cy0), (cx1, cy1) = sh["c"]
    cx, cy = cx0 + (cx1 - cx0) * p, cy0 + (cy1 - cy0) * p
    src = photo(sh["s"]) if sh["k"] == "photo" else clip_frame(sh["s"], sh["a"] + lt)
    if sh.get("fit"):
        return grade(fit_blur(sh["s"], z)).convert("RGBA")
    return grade(cover(src, z, cx, cy)).convert("RGBA")


def render(t):
    i = max(k for k, sh in enumerate(SHOTS) if sh["t0"] <= t) if t < DUR else len(SHOTS) - 1
    sh = SHOTS[i]
    lt = t - sh["t0"]
    img = shot_img(i, lt)
    xf = sh.get("xf", XF)
    if i + 1 < len(SHOTS) and lt > sh["d"] - xf:
        k = ease_io((lt - (sh["d"] - xf)) / xf)
        # zoom-through: shot lama membesar sedikit sambil pudar ke shot baru
        a = img.resize((int(W * (1 + 0.06 * k)), int(H * (1 + 0.06 * k))), Image.BILINEAR)
        a = a.crop(((a.width - W) // 2, (a.height - H) // 2, (a.width - W) // 2 + W, (a.height - H) // 2 + H))
        img = Image.blend(a, shot_img(i + 1, 0.0), k)
    for t0, t1, lines in TITLES:
        draw_title(img, t, t0, t1, lines)
    draw_lower(img, t)
    draw_subs(img, t)
    return img.convert("RGB")


def frame(n):
    return np.asarray(render(n / FPS)).tobytes()


# ---- audio ----
def audio_track(path):
    n = int(DUR * SR)
    out = np.zeros(n, np.float32)
    clips = {c: np.fromfile(os.path.join(CACHE, f"{c}.f32"), np.float32) for c in CLIPS}
    # bunyi bilik dari klip (low-pass) sebagai alas bawah babak gambar
    bed = clips["b4b45a79"]
    k = 400
    bed = np.convolve(bed, np.ones(k) / k, mode="same") * 2.2
    bed_mask = np.zeros(n, np.float32)
    for sh in SHOTS:
        a, b = int(sh["t0"] * SR), min(n, int((sh["t0"] + sh["d"]) * SR))
        if sh["k"] == "clip":
            src = clips[sh["s"]]
            s0 = int(sh["a"] * SR)
            seg = src[s0:s0 + (b - a)]
            env = np.ones(len(seg), np.float32)
            f = int(0.04 * SR)
            env[:f] = np.linspace(0, 1, f)
            env[-f:] = np.linspace(1, 0, f)
            out[a:a + len(seg)] += seg * env
        else:
            bed_mask[a:b] = 0.2 if sh["k"] == "photo" else 0.12
    sm = int(0.3 * SR)
    bed_mask = np.convolve(bed_mask, np.ones(sm) / sm, mode="same")
    reps = int(np.ceil(n / len(bed)))
    out += np.tile(bed, reps)[:n] * bed_mask
    # whoosh lembut pada setiap peralihan
    rng = np.random.default_rng(3)
    for sh in SHOTS[1:]:
        m = int(0.35 * SR)
        a = int(sh["t0"] * SR) - m // 2
        tt = np.linspace(0, 1, m)
        noise = rng.standard_normal(m).astype(np.float32)
        kk = 1 + (40 * (1 - tt)).astype(int)
        sm2 = np.array([noise[max(0, j - kk[j]):j + 1].mean() for j in range(m)], np.float32)
        out[a:a + m] += sm2 * np.sin(np.pi * tt) ** 2 * 0.5
    end0 = int(SHOTS[-1]["t0"] * SR)
    out[end0:] *= np.linspace(1, 0.0, n - end0) ** 0.5
    peak = np.abs(out).max()
    out = out / max(peak, 1e-6) * 0.89
    pcm = (out * 32767).astype(np.int16)
    import wave
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def main(out):
    prepare()
    wav = os.path.splitext(out)[0] + "_audio.wav"
    audio_track(wav)
    total = int(round(DUR * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), "-c:a", "aac", "-b:a", "192k", "-t", f"{DUR:.2f}", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, buf in enumerate(pool.imap(frame, range(total), chunksize=4)):
            p.stdin.write(buf)
            if k % 150 == 0:
                print(f"{k}/{total}", flush=True)
    p.stdin.close()
    p.wait()
    os.remove(wav)


if __name__ == "__main__":
    if sys.argv[2] == "still":
        prepare()
        for tt in sys.argv[3:]:
            render(float(tt)).save(f"still_{tt}.png")
    else:
        main(sys.argv[2])
