#!/usr/bin/env bash
# Setup only: never generates speech, images, or a video.
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v python3.12 >/dev/null 2>&1; then
  BEDTIME_PYTHON=python3.12
else
  BEDTIME_PYTHON=python3
fi
"$BEDTIME_PYTHON" -c 'import sys; assert sys.version_info[:2] == (3,12), "Choose Python 3.12 for this environment"'
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    if [ "$(id -u)" -eq 0 ]; then
      apt-get update
      apt-get install -y ffmpeg
    else
      sudo apt-get update
      sudo apt-get install -y ffmpeg
    fi
  else
    echo "Install FFmpeg/ffprobe with libx264, AAC and libass, then run setup again."
    exit 1
  fi
fi
if [ ! -d .venv ]; then
  "$BEDTIME_PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install -r local/requirements-lock.txt
.venv/bin/python local/cloud_preflight.py --require-no-videos
