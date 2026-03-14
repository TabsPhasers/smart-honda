#!/usr/bin/env bash
# build_kernel.sh - Fetch and build a Linux kernel from kernel.org
set -euo pipefail

VERSION="${1:-6.6}"
JOBS="${2:-$(nproc)}"
SRCDIR="${3:-/usr/src/linux-$VERSION}"
TMPDIR=$(mktemp -d)

trap 'rm -rf "$TMPDIR"' EXIT

echo "==> Building Linux $VERSION with $JOBS jobs"
echo "    Source dir: $SRCDIR"

# Download if not present
if [[ ! -d "$SRCDIR" ]]; then
    TARBALL="linux-${VERSION}.tar.xz"
    URL="https://cdn.kernel.org/pub/linux/kernel/v${VERSION%%.*}.x/$TARBALL"
    echo "==> Downloading $URL ..."
    curl -L --progress-bar -o "$TMPDIR/$TARBALL" "$URL"
    echo "==> Extracting ..."
    mkdir -p "$(dirname "$SRCDIR")"
    tar -xf "$TMPDIR/$TARBALL" -C "$(dirname "$SRCDIR")"
    mv "$(dirname "$SRCDIR")/linux-${VERSION}" "$SRCDIR"
fi

cd "$SRCDIR"

# Use running kernel config as base, then apply defaults for new options
if [[ ! -f .config ]]; then
    if [[ -f "/boot/config-$(uname -r)" ]]; then
        echo "==> Using running kernel config as base ..."
        cp "/boot/config-$(uname -r)" .config
        # Disable debug info to speed up build
        scripts/config --disable DEBUG_INFO
        make olddefconfig
    else
        echo "==> Generating defconfig ..."
        make defconfig
    fi
fi

echo "==> Starting build ..."
time make -j"$JOBS" 2>&1 | tee /tmp/kernel-build.log

echo ""
echo "==> Build complete. Artifacts:"
ls -lh arch/x86/boot/bzImage 2>/dev/null || true
ls -lh vmlinux 2>/dev/null || true
echo ""
echo "==> To install:"
echo "    sudo make modules_install"
echo "    sudo cp arch/x86/boot/bzImage /boot/vmlinuz-$VERSION"
echo "    sudo update-grub"
