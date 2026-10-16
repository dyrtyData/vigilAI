#!/usr/bin/env bash
# Encodes the website deliverables from the silent Remotion master, the soundtrack WAV and the
# poster still. Audio is encoded once, straight from the lossless WAV, into each deliverable.
# Requires: ffmpeg with libx264 (override with FFMPEG=...) and uv (Pillow's WebP encoder).
set -euo pipefail
cd "$(dirname "$0")/.."
FFMPEG="${FFMPEG:-ffmpeg}"
MASTER=out/project-overview-master.mp4
AUDIO=public/audio/soundtrack.wav
POSTER=out/project-overview-poster.png
DEST=../public/media
TITLE="Project overview"
mkdir -p "$DEST"

if [[ -f "$AUDIO" ]]; then
  audio_in=(-i "$AUDIO")
  audio_map=(-map 0:v:0 -map 1:a:0 -shortest)
  audio_full=(-c:a aac -b:a 192k -ac 2 -ar 48000)
  audio_web=(-c:a aac -b:a 128k -ac 2 -ar 48000)
else
  echo "warning: $AUDIO not found — encoding the full and 720p renditions without a soundtrack" >&2
  audio_in=(); audio_map=(-map 0:v:0); audio_full=(-an); audio_web=(-an)
fi

# Full 1080p H.264 + AAC, progressive download (moov atom first).
"$FFMPEG" -hide_banner -loglevel error -y -i "$MASTER" "${audio_in[@]}" "${audio_map[@]}" \
  -c:v libx264 -preset slow -crf 20 -profile:v high -level 4.1 -pix_fmt yuv420p -g 60 \
  "${audio_full[@]}" -metadata title="$TITLE" -movflags +faststart "$DEST/project-overview.mp4"

# 720p web rendition.
"$FFMPEG" -hide_banner -loglevel error -y -i "$MASTER" "${audio_in[@]}" "${audio_map[@]}" -vf "scale=1280:720:flags=lanczos" \
  -c:v libx264 -preset slow -crf 22 -profile:v high -level 3.1 -pix_fmt yuv420p -g 60 \
  "${audio_web[@]}" -metadata title="$TITLE" -movflags +faststart "$DEST/project-overview-720p.mp4"

# Silent 720p rendition with a keyframe every 0.5 s, for optional scroll-controlled seeking.
"$FFMPEG" -hide_banner -loglevel error -y -i "$MASTER" -map 0:v:0 -an -vf "scale=1280:720:flags=lanczos" \
  -c:v libx264 -preset slow -crf 23 -profile:v high -level 3.1 -pix_fmt yuv420p \
  -g 15 -keyint_min 15 -sc_threshold 0 -metadata title="$TITLE (silent)" -movflags +faststart "$DEST/project-overview-silent.mp4"

# Poster (WebP via Pillow; common ffmpeg builds lack libwebp).
uv run --no-project --python 3.12 --with pillow python -I -c \
  "import sys; from PIL import Image; Image.open(sys.argv[1]).convert('RGB').save(sys.argv[2], 'WEBP', quality=88, method=6)" \
  "$POSTER" "$DEST/project-overview-poster.webp"

ls -la "$DEST"
