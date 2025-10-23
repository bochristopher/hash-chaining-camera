#!/bin/bash
# Provenance Logger - Container Entrypoint
# Switches between logger and verifier modes

set -e

MODE="${1:-logger}"

echo "=========================================="
echo "Provenance Logger Container"
echo "Mode: $MODE"
echo "=========================================="

# Ensure config file exists
if [ ! -f "/config/config.yaml" ]; then
    echo "No config.yaml found, copying example..."
    cp /config/config.example.yaml /config/config.yaml
fi

# Create data directories
mkdir -p /data/frames
mkdir -p /keys

case "$MODE" in
    logger)
        echo "Starting logger mode..."
        echo ""

        # Check for keys, generate if needed
        if [ ! -f "/keys/private_key.pem" ]; then
            echo "No keypair found, generating..."
            python3 /app/python_core/logger.py --generate-keys \
                --config /config/config.yaml \
                --data /data \
                --keys /keys
            echo ""
        fi

        # Start logger
        exec python3 /app/python_core/logger.py \
            --config /config/config.yaml \
            --data /data \
            --keys /keys
        ;;

    verifier)
        echo "Starting verifier mode..."
        echo ""

        # Check if Node UI is available
        if [ -d "/app/node_ui" ]; then
            echo "Starting with web dashboard..."
            echo "  - Flask API on port 5000"
            echo "  - Node.js UI on port 8080"
            echo ""

            # Start Flask API in background
            python3 /app/python_core/api/server.py \
                --data /data \
                --keys /keys \
                --host 0.0.0.0 \
                --port 5000 &

            # Wait for Flask to start
            sleep 2

            # Start Node.js dashboard
            cd /app/node_ui
            exec npm start
        else
            echo "Starting Flask API only..."
            echo "  - API on port 5000"
            echo ""

            # Start Flask API
            exec python3 /app/python_core/api/server.py \
                --data /data \
                --keys /keys \
                --host 0.0.0.0 \
                --port 5000
        fi
        ;;

    verify-cli)
        echo "Running CLI verification..."
        echo ""

        exec python3 /app/python_core/verifier.py \
            --data /data \
            --keys /keys \
            "${@:2}"
        ;;

    bash)
        echo "Starting interactive bash shell..."
        exec /bin/bash
        ;;

    *)
        echo "Unknown mode: $MODE"
        echo ""
        echo "Usage: $0 [logger|verifier|verify-cli|bash]"
        echo ""
        echo "Modes:"
        echo "  logger      - Capture frames and build hash chain"
        echo "  verifier    - Run verification API + web dashboard"
        echo "  verify-cli  - Run one-time CLI verification"
        echo "  bash        - Interactive shell"
        exit 1
        ;;
esac
