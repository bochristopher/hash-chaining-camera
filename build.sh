#!/bin/bash
# Build script for Provenance Logger containers

set -e

echo "=========================================="
echo "Provenance Logger - Container Build"
echo "=========================================="
echo ""

# Check architecture
ARCH=$(uname -m)
if [ "$ARCH" != "aarch64" ]; then
    echo "Warning: Not running on aarch64 (Jetson)"
    echo "Current architecture: $ARCH"
    echo "This container is designed for Jetson Orin Nano"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build mode
MODE="${1:-all}"

case "$MODE" in
    python|python-core)
        echo "Building Python-core image..."
        docker build --target python-core -t provenance-logger:python-core .
        echo ""
        echo "✓ Built: provenance-logger:python-core (~3.5GB)"
        ;;

    node|node-ui|full)
        echo "Building Node-UI image (includes Python core)..."
        docker build --target node-ui -t provenance-logger:node-ui .
        echo ""
        echo "✓ Built: provenance-logger:node-ui (~4.2GB)"
        ;;

    all)
        echo "Building both images..."
        echo ""
        echo "1/2: Building Python-core..."
        docker build --target python-core -t provenance-logger:python-core .
        echo ""
        echo "2/2: Building Node-UI..."
        docker build --target node-ui -t provenance-logger:node-ui .
        echo ""
        echo "✓ Built: provenance-logger:python-core (~3.5GB)"
        echo "✓ Built: provenance-logger:node-ui (~4.2GB)"
        ;;

    *)
        echo "Unknown mode: $MODE"
        echo ""
        echo "Usage: $0 [python|node|all]"
        echo ""
        echo "Modes:"
        echo "  python     - Build Python-core image only"
        echo "  node       - Build Node-UI image (includes Python)"
        echo "  all        - Build both images (default)"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo ""
echo "Quick start:"
echo ""
echo "  # Run logger:"
echo "  docker compose --profile logger up -d"
echo ""
echo "  # Run verifier with dashboard:"
echo "  docker compose --profile verifier up -d"
echo ""
echo "  # View logs:"
echo "  docker compose logs -f"
echo ""
echo "See CONTAINER_QUICKSTART.md for more examples."
echo ""
