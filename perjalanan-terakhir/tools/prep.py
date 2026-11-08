#!/usr/bin/env python3
"""Sedia aset dari footage/ (asal, tak diubah) -> public/:
- clips/<id>_<n>.mp4 : potongan ikut timeline (H.264, 30fps, tiada audio)
- audio/<id>_<n>.wav : audio asal potongan (48k mono, untuk mix)
- stills/<id>.jpg    : frame untuk cutout polaroid
- paper.png          : tekstur kertas procedural
Gagal kalau klip tak cukup panjang untuk babak."""
import json, os, re, subprocess
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = json.load(open(os.path.join(ROOT, "timeline.json")))
FOOT, PUB = os.path.join(ROOT, "footage"), os.path.join(ROOT, "public")
for d in ("clips", "audio", "stills"):
    os.makedirs(os.path.join(PUB, d), exist_ok=True)

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", p]).decode())

manifest = {}
for s in T["scenes"]:
    total = s["end"] - s["start"]
    clips = s["clips"]; used = 0.0; out = []
    for n, c in enumerate(clips):
        src = os.path.join(FOOT, c["src"]); d = dur(src)
        length = c.get("len", total - used) if n < len(clips) - 1 else total - used
        if c["in"] + length > d + 0.01:
            raise SystemExit(f"{s['id']}: {c['src']} cuma {d:.2f}s, perlu {c['in']+length:.2f}s")
        name = f"{s['id']}_{n}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["in"]), "-i", src, "-t", f"{length:.3f}",
                        "-an", "-vf", "fps=30,scale=720:1280", "-c:v", "libx264", "-crf", "18", "-g", "15",
                        "-pix_fmt", "yuv420p", os.path.join(PUB, "clips", name + ".mp4")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["in"]), "-i", src, "-t", f"{length:.3f}",
                        "-vn", "-ac", "1", "-ar", "48000", os.path.join(PUB, "audio", name + ".wav")], check=True)
        out.append({"file": f"clips/{name}.mp4", "audio": f"audio/{name}.wav", "offset": round(used, 3), "len": round(length, 3)})
        used += length
    m = {"clips": out}
    if "still" in s:
        st = s["still"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(st["at"]), "-i", os.path.join(FOOT, st["src"]),
                        "-frames:v", "1", "-q:v", "3", os.path.join(PUB, "stills", s["id"] + ".jpg")], check=True)
        m["still"] = f"stills/{s['id']}.jpg"
    manifest[s["id"]] = m

# Tekstur kertas: warna asas #e9dfc9 + noise halus + serat + vignette lembut
rng = np.random.default_rng(7)
W, H = 1080, 1920
base = np.array([0xe9, 0xdf, 0xc9], np.float32)
n1 = Image.fromarray((rng.random((H // 4, W // 4)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
n1 = np.asarray(n1.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255 - 0.5
n2 = rng.normal(0, 1, (H, W)).astype(np.float32)
fib = np.asarray(Image.fromarray(((n2 * 30) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(1)), np.float32) / 255 - 0.5
yy, xx = np.mgrid[0:H, 0:W]
vig = ((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2) ** 0.5
img = base[None, None, :] + (n1 * 14 + fib * 10 - vig[..., None].squeeze() * 22)[..., None]
Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(os.path.join(PUB, "paper.png"))

json.dump(manifest, open(os.path.join(ROOT, "src", "manifest.json"), "w"), indent=1)
print("prep OK:", sum(len(v["clips"]) for v in manifest.values()), "potongan,",
      sum("still" in v for v in manifest.values()), "still")
