#!/usr/bin/env bash
# Build the vigilAI hackathon report PDF.
#   1. Renders the report markdown -> PDF with pandoc + xelatex (Latin Modern serif,
#      1in margins, blue links — matching the sibling vectox report).
#   2. Renders the 6-model dossier (reports/multimodel-scorecard.html) -> PDF via
#      headless Chrome and appends it as Appendix B.
# Requires: pandoc, a TeX engine (xelatex), Google Chrome, and pdfunite (poppler).
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$PATH:/Library/TeX/texbin"
MD="vigilai-brazil-pl2338-compliance.md"
OUT="vigilai-brazil-pl2338-compliance.pdf"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

pandoc "$MD" -o /tmp/_vigilai_body.pdf --resource-path "." \
  --pdf-engine=xelatex -V geometry:margin=1in -V linkcolor:blue --metadata title=

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=/tmp/_vigilai_dossier.pdf \
  "file://$(cd ..; pwd)/reports/multimodel-scorecard.html"

pdfunite /tmp/_vigilai_body.pdf /tmp/_vigilai_dossier.pdf "$OUT"
echo "built $OUT"
