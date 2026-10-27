#!/usr/bin/env bash
set -euo pipefail
# Run in a dedicated Ubuntu 22.04+ environment. On WSL use the imported research distro.
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends build-essential gcc-arm-none-eabi libnewlib-arm-none-eabi qemu-system-arm gdb-multiarch git ca-certificates curl python3-numpy python3-scipy python3-sklearn python3-matplotlib python3-pip cmake ninja-build
python3 "$(dirname "$0")/restore_sources.py"
