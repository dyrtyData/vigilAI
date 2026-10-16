#!/usr/bin/env bash
# Tiles four review stills into one 1920-wide sheet: contact-sheet.sh <out.png> <a.png> <b.png> <c.png> <d.png>
set -euo pipefail
out="$1"; shift
ffmpeg -loglevel error -y -i "$1" -i "$2" -i "$3" -i "$4" -filter_complex "[0][1]hstack[a];[2][3]hstack[b];[a][b]vstack,scale=1920:-1" "$out"
