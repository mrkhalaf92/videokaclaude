#!/usr/bin/env python3
"""Mix audio preview -> out/mix.wav (48 kHz stereo).

Lapisan (semua timing dari timeline.json, sama dengan visual):
1. Audio asal footage (suara peserta/penceramah) - keutamaan, tidak dipercepat.
2. Muzik procedural: pad hangat (Dm-Bb-F-C), perkusi lembut masuk di Penerangan,
   tik kertas di Contoh, perkusi hilang di Takeaway, senyap+swell lembut di CTA.
3. SFX: satu gerak kertas setiap foto mendarat, tik marker setiap anotasi,
   kertas untuk polaroid, satu thud lembut untuk CTA.
Muzik di-duck ikut envelope audio footage. Tiada sampel luar, tiada lagu sedia ada.
"""
import json, os, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = json.load(open(os.path.join(ROOT, "timeline.json")))
MAN = json.load(open(os.path.join(ROOT, "src", "manifest.json")))
SR = 48000
N = int(T["duration"] * SR)
rng = np.random.default_rng(11)
sec = lambda s: int(round(s * SR))
db = lambda d: 10 ** (d / 20)

def read_wav(p):
    with wave.open(p) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return a if w.getnchannels() == 1 else a.reshape(-1, w.getnchannels()).mean(1)

def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i in range(len(x)):  # cukup laju untuk 90s
        s = (1 - a) * x[i] + a * s; y[i] = s
    return y

def fade(x, fi, fo):
    x = x.copy(); fi, fo = min(fi, len(x) // 2), min(fo, len(x) // 2)
    if fi: x[:fi] *= np.linspace(0, 1, fi)
    if fo: x[-fo:] *= np.linspace(1, 0, fo)
    return x

# ---------- 1. Audio footage ----------
dia = np.zeros(N, np.float32)
for s in T["scenes"]:
    for c in MAN[s["id"]]["clips"]:
        a = read_wav(os.path.join(ROOT, "public", c["audio"]))
        rms = np.sqrt(np.mean(a ** 2) + 1e-12)
        a = a * (db(-24) / rms)              # seragamkan tahap antara klip
        a = fade(a, sec(0.03), sec(0.06))    # elak klik di potongan
        st = sec(s["start"] + c["offset"]); dia[st:st + len(a)] += a[:N - st]
dia = np.tanh(dia * 1.2) / 1.2               # lembutkan puncak tepuk/hentakan

# Envelope untuk ducking
win = sec(0.02)
env = np.sqrt(np.convolve(dia ** 2, np.ones(win) / win, "same"))
sm = np.empty_like(env); v = 0.0
att, rel = np.exp(-1 / (0.05 * SR)), np.exp(-1 / (0.35 * SR))
for i in range(N):
    k = att if env[i] > v else rel; v = k * v + (1 - k) * env[i]; sm[i] = v
duck = 1 - 0.55 * np.clip(sm / (db(-24) * 1.4), 0, 1)   # sehingga ~-7 dB bila ada suara

# ---------- 2. Muzik ----------
t = np.arange(N) / SR
bpm = 66; beat = 60 / bpm; bar = 4 * beat
chords = [[50, 57, 62, 64, 69], [46, 53, 58, 62, 65], [41, 48, 53, 57, 60], [48, 55, 60, 64, 67]]  # Dm9 Bb F C
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
pad = np.zeros(N, np.float32)
nb = int(np.ceil(T["duration"] / bar))
for b in range(nb):
    st, en = sec(b * bar), min(N, sec((b + 1) * bar + 0.6))
    tt = t[st:en] - b * bar
    e = np.minimum(1, tt / 1.2) * np.exp(-np.maximum(0, tt - bar) * 3)
    for i, m in enumerate(chords[b % 4]):
        for det in (-0.12, 0.12):
            pad[st:en] += (0.11 / (1 + i * 0.3)) * e * np.sin(2 * np.pi * hz(m + det) * tt + i)
pad = onepole_lp(pad, 1400)

beats = {s["beat"] for s in T["scenes"]}
scene_at = lambda beat_name: min(s["start"] for s in T["scenes"] if s["beat"] == beat_name)
t_pen, t_con, t_take, t_cta = scene_at("penerangan"), scene_at("contoh"), scene_at("takeaway"), scene_at("cta")
cta = next(s for s in T["scenes"] if s.get("cta")); t_cta_text = cta["start"] + cta["ctaAt"]

perc = np.zeros(N, np.float32)
def thump(at, g):
    n = sec(0.35); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * (52 + 40 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9) * g
    st = sec(at); perc[st:st + n] += x[:max(0, N - st)]
def tick(buf, at, g, dur=0.03, fc=5000):
    n = sec(dur); x = rng.normal(0, 1, n) * np.exp(-np.arange(n) / (n / 5))
    x = x - onepole_lp(x, fc * 0.4)            # high-pass kasar: bunyi kertas kering
    st = sec(at); buf[st:st + n] += (x * g)[:max(0, N - st)]

k = 0
while k * beat < T["duration"]:
    at = k * beat
    if t_pen <= at < t_take and k % 2 == 0: thump(at, 0.32)
    if t_con <= at < t_take:
        tick(perc, at + beat / 2, 0.05); tick(perc, at, 0.035)
    k += 1

# Bentuk muzik: hook nipis -> isi -> takeaway lembut -> CTA hampir senyap
gain = np.interp(t, [0, 1.5, t_pen, t_con, t_take, t_cta, t_cta_text - 0.4, t_cta_text, T["duration"] - 1.5, T["duration"]],
                    [0.0, 0.55, 0.7, 0.85, 0.65, 0.45, 0.12, 0.12, 0.25, 0.0])
music = (pad + perc) * gain

# Swell lembut di CTA (nada rendah D + A)
n = sec(T["duration"] - t_cta_text); tt = np.arange(n) / SR
sw = (np.sin(2 * np.pi * hz(38) * tt) + 0.5 * np.sin(2 * np.pi * hz(45) * tt)) * np.minimum(1, tt / 1.5) * np.exp(-tt * 0.35) * 0.16
music[sec(t_cta_text):sec(t_cta_text) + n] += sw[:N - sec(t_cta_text)]
music *= duck

# ---------- 3. SFX ----------
sfx = np.zeros(N, np.float32)
def paper_move(at, g=0.18):
    n = sec(0.22); x = rng.normal(0, 1, n)
    x = onepole_lp(x, 3500) - onepole_lp(x, 600)
    e = np.minimum(1, np.arange(n) / sec(0.02)) * np.exp(-np.arange(n) / sec(0.07))
    st = sec(at); sfx[st:st + n] += (x * e * g)[:max(0, N - st)]
for s in T["scenes"]:
    paper_move(s["start"] + 0.02)
    if s.get("note"): tick(sfx, s["start"] + s["noteAt"] + 4 / 30, 0.09, 0.05, 3000)
    if s.get("stillAt"): paper_move(s["start"] + s["stillAt"], 0.14)
thump_buf = perc; perc = sfx; thump(t_cta_text, 0.5); sfx = perc  # thud lembut CTA

# ---------- Mix ----------
mix = dia * db(0) + music * db(-6) + sfx * db(-3)
L = mix + np.roll(music, sec(0.011)) * db(-14)   # sedikit lebar stereo untuk muzik sahaja
R = mix - np.roll(music, sec(0.011)) * db(-14)
st = np.stack([L, R], 1)
peak = np.abs(st).max()
st = st / max(peak, 1e-9) * db(-3)               # headroom sebelum loudnorm
os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
with wave.open(os.path.join(ROOT, "out", "mix_raw.wav"), "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())

# Laporan untuk semakan: tahap muzik vs suara
def lvl(x, a, b): seg = x[sec(a):sec(b)]; return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)
print(f"suara footage RMS {lvl(dia, 0, 90):.1f} dB | muzik selepas duck {lvl(music * db(-6), 0, 90):.1f} dB | sfx {lvl(sfx * db(-3), 0, 90):.1f} dB")
print(f"peak sebelum normalise {20*np.log10(peak):.1f} dBFS -> out/mix_raw.wav")
