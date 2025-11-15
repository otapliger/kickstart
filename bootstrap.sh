#!/bin/sh

set -eu

: "${RELEASE_VERSION:=}"

# If RELEASE_VERSION was not provided, query the GitHub Releases API for the latest tag.
# If the API call fails, fall back to 'continuous'.
if [ -z "${RELEASE_VERSION}" ]; then
  api_response="$(curl -sS -H "Accept: application/vnd.github+json" https://api.github.com/repos/otapliger/kickstart/releases/latest)" || api_response=""
  RELEASE_VERSION="$(printf '%s' "$api_response" | grep -m1 '"tag_name"' | sed -E 's|.*"tag_name": *"([^"]+)".*|\1|' || true)"

  if [ -z "${RELEASE_VERSION}" ]; then
    RELEASE_VERSION="continuous"
  fi
fi

RELEASE_BASE_URL="https://github.com/otapliger/kickstart/releases/download/${RELEASE_VERSION}"
RELEASE_URL="${RELEASE_BASE_URL}/kickstart"
CHECKSUM_URL="${RELEASE_BASE_URL}/kickstart.sha256"
CLEANUP_ON_EXIT=true

cleanup() {
  if [ "${CLEANUP_ON_EXIT:-true}" = "true" ] && [ -n "${INSTALL_DIR:-}" ] && [ -d "${INSTALL_DIR}" ]; then
    rm -rf "${INSTALL_DIR}"
  fi
}

trap cleanup EXIT INT TERM

die() {
  echo "Error: $1" >&2
  exit 1
}

check_requirements() {
  echo "Checking requirements..."

  if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="${ID:-unknown}"
  else
    DISTRO="unknown"
  fi

  case "${DISTRO}" in
    void|arch)
      ;;
    *)
      die "Unsupported distribution: ${DISTRO}. Check https://github.com/otapliger/kickstart for supported distributions."
      ;;
  esac

  if ! command -v curl >/dev/null 2>&1 || ! command -v parted >/dev/null 2>&1 || ! command -v sgdisk >/dev/null 2>&1; then
    case "${DISTRO}" in
      void)
        echo "Installing required packages (Void Linux)..."
        xbps-install -Sy xbps curl parted gptfdisk || die "Failed to install required packages"
        ;;
      arch)
        echo "Installing required packages (Arch Linux)..."
        pacman -Sy --noconfirm curl parted gptfdisk || die "Failed to install required packages"
        ;;
    esac
  fi
}

download_and_verify() {
  echo
  echo "Release version: ${RELEASE_VERSION}"
  echo "Binary URL: ${RELEASE_URL}"
  echo "Checksum URL: ${CHECKSUM_URL}"
  echo

  INSTALL_DIR=$(mktemp -d "${TMPDIR:-/tmp}/kickstart.XXXXXX") || die "mktemp failed"
  [ -d "${INSTALL_DIR}" ] || die "Failed to create temporary directory"
  cd "${INSTALL_DIR}" || die "Cannot enter temporary directory"

  echo "Downloading binary..."
  curl -fSLo kickstart -# "${RELEASE_URL}" || die "Failed to download binary from ${RELEASE_URL}"

  echo "Downloading checksum..."
  if ! curl -fSLo kickstart.sha256 -# "${CHECKSUM_URL}"; then
    die "Checksum not available at ${CHECKSUM_URL} (required)."
  fi

  echo "Verifying checksum..."
  sha256sum -c kickstart.sha256 >/dev/null 2>&1 || die "Checksum verification failed."
  chmod +x kickstart || die "Failed to make binary executable."
}

run_kickstart() {
  [ -f kickstart ] || die "Binary not found after download."

  # Keep the binary around while running it
  CLEANUP_ON_EXIT=false
  exec ./kickstart "$@" < /dev/tty
}

check_requirements
download_and_verify
run_kickstart "$@"
