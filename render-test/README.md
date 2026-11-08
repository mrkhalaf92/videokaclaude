# render-test

Ujian render minimum (Remotion 4.0.538 + ffmpeg) sebelum guna workflow video berasaskan kod.
Semua dependency kekal dalam folder ini (`node_modules/`, tidak di-commit).

```bash
npm install      # sekali sahaja
npm run render   # -> out/test-video.mp4 (1080x1920, 30fps, 5s, H.264 yuv420p bt709)
npm run verify   # semak wujud, decode penuh, durasi, resolusi, frame count; keluarkan out/sample-frames.png
```

`render.mjs` guna Chromium headless sedia ada di `/opt/pw-browsers` kalau ada; kalau tiada,
Remotion akan muat turun browser sendiri. Boleh override dengan env `REMOTION_BROWSER`.
