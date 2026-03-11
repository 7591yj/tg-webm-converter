#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
}

require_command poetry

cd "$ROOT_DIR"
poetry run pyinstaller -y "$ROOT_DIR/pyinstaller/gui_api.spec"

BACKEND_DIR="$ROOT_DIR/dist/backend"
mkdir -p "$BACKEND_DIR"

FFMPEG_BIN="${FFMPEG_BIN:-$(command -v ffmpeg)}"
FFPROBE_BIN="${FFPROBE_BIN:-$(command -v ffprobe)}"

if [[ -z "${FFMPEG_BIN}" || ! -x "${FFMPEG_BIN}" ]]; then
  echo "ffmpeg binary not found. Set FFMPEG_BIN or install ffmpeg before packaging." >&2
  exit 1
fi

if [[ -z "${FFPROBE_BIN}" || ! -x "${FFPROBE_BIN}" ]]; then
  echo "ffprobe binary not found. Set FFPROBE_BIN or install ffmpeg before packaging." >&2
  exit 1
fi

cp "$FFMPEG_BIN" "$BACKEND_DIR/ffmpeg"
cp "$FFPROBE_BIN" "$BACKEND_DIR/ffprobe"
chmod +x "$BACKEND_DIR/ffmpeg" "$BACKEND_DIR/ffprobe"
