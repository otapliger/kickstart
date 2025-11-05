#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/dist"
CI_BIN="kickstart-linux-x86_64"
LINK_NAME="kickstart"

echo "Building -> $OUTPUT_DIR/$CI_BIN"

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

if [ ! -f "$CI_BIN" ]; then
  echo "Error: expected binary not found: $CI_BIN" >&2
  echo "Contents of $OUTPUT_DIR:"
  ls -alh . || true
  exit 1
fi

chmod +x "$CI_BIN" || true
ln -sfn "$CI_BIN" "$LINK_NAME" || true
printf "Build finished: %s -> %s (%s)\n" "$LINK_NAME" "$CI_BIN" "$(du -h "$CI_BIN" 2>/dev/null | cut -f1 || echo 'unknown')"
exit 0
