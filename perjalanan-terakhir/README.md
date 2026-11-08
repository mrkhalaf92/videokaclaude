# Perjalanan Terakhir — preview video (Scrapbook Documentary)

Portrait 1080x1920, 30fps, 90 saat. Edit footage sendiri dari folder Drive
`[06] PERJALANAN TERAKHIR / BPJ 3`. Status: **PREVIEW, belum final export.**

## Struktur
| Fail | Fungsi |
|---|---|
| `timeline.json` | Sumber tunggal: babak, klip + in-point, headline, anotasi, CTA, timing. Visual dan audio baca fail ini. |
| `tools/prep.py` | Potong klip dari `footage/` (asal, tak diubah) ke `public/`, ambil still, jana tekstur kertas. |
| `src/` | Komposisi Remotion (foto tepi koyak, pita, anotasi marker, polaroid, CTA). Warna dalam `src/theme.ts`. |
| `tools/make_audio.py` | Muzik procedural + SFX + audio footage, ducking, -> `out/mix_raw.wav`. |
| `tools/finish.sh` | Gabung video + audio -> `out/preview.mp4` dan jalankan semakan teknikal. |

## Bina semula
`footage/` tidak di-commit (fail asal kekal di Drive). Muat turun klip yang disenaraikan dalam
`timeline.json` ke `footage/`, kemudian:

```bash
npm install
python3 tools/prep.py
python3 tools/make_audio.py
bash tools/loudnorm.sh
node render.mjs
bash tools/finish.sh
```

Semak layout cepat tanpa render penuh: `node render.mjs --stills --at=1,20,88`.

## Tukar kandungan
- Teks / timing / klip: ubah `timeline.json`, jalankan semula `prep.py` (jika klip berubah), `make_audio.py`, render.
- Warna brand: `src/theme.ts`.
