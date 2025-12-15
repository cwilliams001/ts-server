#!/bin/bash
# Cross-compilation build script for ts-server

set -e

VERSION="2.0.0"
OUTPUT_DIR="./build"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Building ts-server v${VERSION} for multiple platforms..."
echo ""

# Build for each platform
platforms=(
    "linux/amd64"
    "linux/arm64"
    "darwin/amd64"
    "darwin/arm64"
    "windows/amd64"
    "windows/arm64"
    "freebsd/amd64"
)

for platform in "${platforms[@]}"; do
    platform_split=(${platform//\// })
    GOOS=${platform_split[0]}
    GOARCH=${platform_split[1]}

    output_name="ts-server-${GOOS}-${GOARCH}"

    # Add .exe extension for Windows
    if [ "$GOOS" = "windows" ]; then
        output_name="${output_name}.exe"
    fi

    echo "Building for ${GOOS}/${GOARCH}..."

    env GOOS=$GOOS GOARCH=$GOARCH mise exec -- go build \
        -ldflags="-s -w" \
        -o "${OUTPUT_DIR}/${output_name}"

    # Calculate size
    size=$(du -h "${OUTPUT_DIR}/${output_name}" | cut -f1)
    echo "  -> ${output_name} (${size})"
done

echo ""
echo "Build complete! Binaries are in ${OUTPUT_DIR}/"
echo ""
echo "To create compressed archives:"
echo "  cd ${OUTPUT_DIR} && tar -czf ts-server-linux-amd64.tar.gz ts-server-linux-amd64"
