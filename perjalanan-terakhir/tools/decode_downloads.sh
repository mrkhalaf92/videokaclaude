#!/usr/bin/env bash
# Tukar hasil download Drive (JSON base64) -> footage/<title>. Skip yang dah ada.
D=/root/.claude/projects/-home-user-videokaclaude/e88ad0c1-1c16-5f53-8e83-3879f637f3fb/tool-results
OUT=$(dirname "$0")/../footage
for f in "$D"/mcp-Google_Drive-download_file_content-*.txt; do
  t=$(jq -r .title "$f" 2>/dev/null) || continue
  [ -n "$t" ] && [ "$t" != null ] || continue
  [ -s "$OUT/$t" ] || { jq -r .content "$f" | base64 -d > "$OUT/$t" && echo "decoded: $t"; }
done
ls "$OUT" | wc -l
