#!/usr/bin/env bash
# Gabung video + audio -> out/preview.mp4, kemudian semak teknikal.
set -euo pipefail
cd "$(dirname "$0")/.."
ffmpeg -v error -y -i out/video_noaudio.mp4 -i out/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/preview.mp4
F=out/preview.mp4
echo "== probe"; ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels:format=duration -of compact "$F"
echo "== decode penuh"; E=$(ffmpeg -v error -i "$F" -f null - 2>&1 || true); [ -z "$E" ] && echo OK || echo "GAGAL: $E"
echo "== loudness (target -14 LUFS, TP <= -1.5)"; ffmpeg -hide_banner -i "$F" -af ebur128=peak=true -f null - 2>&1 | grep -A12 "Summary:" | grep -E "I:|Peak:|LRA:"
echo "== clipping (sampel >= -0.1 dBFS)"; ffmpeg -hide_banner -i "$F" -af astats=metadata=0 -f null - 2>&1 | grep -E "Peak level dB|Number of samples clipped|Flat factor" | head -6
echo "== frame semakan"; mkdir -p review/final; for t in 0.5 3 9 15 21 28 35 40 47 54 61 67 73 79 84 88.5; do ffmpeg -v error -y -ss $t -i "$F" -frames:v 1 -vf scale=270:480 review/final/f_$(printf %05.1f $t).png; done
ffmpeg -v error -y -pattern_type glob -i 'review/final/f_*.png' -vf tile=8x2 review/final_sheet.png && echo "review/final_sheet.png"
