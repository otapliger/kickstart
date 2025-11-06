#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/dist"
OUTPUT_BIN="kickstart"

echo "Building -> $OUTPUT_DIR/$OUTPUT_BIN"

# Prepare output
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Build and export into $OUTPUT_DIR
docker buildx build --no-cache \
  --platform linux/amd64 \
  --output type=local,dest="$OUTPUT_DIR" \
  -t kickstart-builder \
  -f Dockerfile \
  .

cd "$OUTPUT_DIR"

if [ ! -f "$OUTPUT_BIN" ]; then
  echo "Error: expected binary not found: $OUTPUT_BIN" >&2
  echo "Contents of $OUTPUT_DIR:"
  ls -alh . || true
  exit 1
fi

chmod +x "$OUTPUT_BIN" || true
printf "Build finished: dist/%s\n" "$OUTPUT_BIN"
exit 0
