#!/usr/bin/env bash
# Normalise dua-pass out/mix_raw.wav -> out/mix.wav (-14 LUFS, true peak -1.5 dBTP).
set -euo pipefail
cd "$(dirname "$0")/.."
J=$(ffmpeg -hide_banner -i out/mix_raw.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p')
g() { echo "$J" | jq -r ".$1"; }
ffmpeg -v error -y -i out/mix_raw.wav -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000" out/mix.wav
echo "mix.wav OK (input $(g input_i) LUFS)"
