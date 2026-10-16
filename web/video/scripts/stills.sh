#!/usr/bin/env bash
# Renders review stills: scripts/stills.sh <out-dir> <seconds...>
set -euo pipefail
out="$1"; shift
mkdir -p "$out"
for s in "$@"; do
  frame=$(node -e "console.log(Math.round($s*30))")
  pnpm exec remotion still src/index.ts ProjectOverview "$out/t$(printf '%06.2f' "$s").png" --frame="$frame" --props='{"projectName":"Vigil AI","withAudio":false}' --log=error
done
