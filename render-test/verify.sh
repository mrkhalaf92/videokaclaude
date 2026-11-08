#!/usr/bin/env bash
# Semak out/test-video.mp4: wujud, boleh decode penuh, durasi ~5s, resolusi 1080x1920, ambil sample frame.
set -euo pipefail
F=out/test-video.mp4
test -s "$F" && echo "OK  fail wujud ($(du -h "$F" | cut -f1))"
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,pix_fmt -show_entries format=duration -of default=nw=1 "$F"
ERR=$(ffmpeg -v error -i "$F" -f null - 2>&1 || true)
[ -z "$ERR" ] && echo "OK  decode penuh tanpa error" || { echo "GAGAL decode: $ERR"; exit 1; }
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$F")
RES=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of default=nw=1:nk=1 "$F" | paste -sd x)
FR=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=nw=1:nk=1 "$F")
awk -v d="$DUR" 'BEGIN{exit !(d>4.8 && d<5.2)}' && echo "OK  durasi ${DUR}s" || { echo "GAGAL durasi $DUR"; exit 1; }
[ "$RES" = "1080x1920" ] && echo "OK  resolusi $RES" || { echo "GAGAL resolusi $RES"; exit 1; }
[ "$FR" = "150" ] && echo "OK  frame dikira: $FR" || echo "AMARAN frame: $FR"
mkdir -p frames
for t in 0.5 2.5 4.5; do ffmpeg -v error -y -ss $t -i "$F" -frames:v 1 -vf scale=360:-1 "frames/t$t.png"; done
ffmpeg -v error -y -i frames/t0.5.png -i frames/t2.5.png -i frames/t4.5.png -filter_complex hstack=3 out/sample-frames.png
echo "OK  sample frame: out/sample-frames.png"
