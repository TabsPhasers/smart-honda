#!/usr/bin/env bash
# setup_env.sh - Install build dependencies for kernel development
set -euo pipefail

DISTRO=$(. /etc/os-release && echo "$ID")

install_debian() {
    apt-get update -qq
    apt-get install -y \
        build-essential \
        libncurses-dev \
        bison \
        flex \
        libssl-dev \
        libelf-dev \
        dwarves \
        bc \
        cpio \
        pahole \
        python3 \
        python3-pip \
        python3-venv \
        linux-headers-"$(uname -r)"
}

install_fedora() {
    dnf install -y \
        gcc \
        make \
        ncurses-devel \
        bison \
        flex \
        openssl-devel \
        elfutils-libelf-devel \
        dwarves \
        bc \
        python3 \
        python3-pip \
        "kernel-devel-$(uname -r)"
}

install_arch() {
    pacman -Sy --noconfirm \
        base-devel \
        ncurses \
        openssl \
        libelf \
        pahole \
        bc \
        python \
        python-pip \
        linux-headers
}

echo "Detected distro: $DISTRO"

case "$DISTRO" in
    ubuntu|debian) install_debian ;;
    fedora|rhel|centos) install_fedora ;;
    arch|manjaro) install_arch ;;
    *)
        echo "Unsupported distro: $DISTRO"
        echo "Please install kernel build dependencies manually."
        exit 1
        ;;
esac

# Install Python tool
pip3 install -e "$(dirname "$(dirname "$0")")" 2>/dev/null || true

echo ""
echo "Environment setup complete."
echo "Run: smart-honda --help"
