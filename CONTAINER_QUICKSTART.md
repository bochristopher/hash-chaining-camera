# Provenance Logger - Container Quick Start

**One-command deployment for Jetson Orin Nano**

## 1. Build

```bash
# Python-only (3.5GB)
docker build --target python-core -t provenance-logger:python-core .

# With Node.js dashboard (4.2GB)
docker build --target node-ui -t provenance-logger:node-ui .
```

## 2. Configure

```bash
# Copy example config
mkdir -p config data keys
cp config/config.example.yaml config/config.yaml

# Edit config/config.yaml for your camera
```

## 3. Run

### Logger Mode (Capture frames)

```bash
docker run --rm -it \
  --privileged \
  --network host \
  --device /dev/video0 \
  -v $(pwd)/data:/data \
  -v $(pwd)/config:/config \
  -v $(pwd)/keys:/keys \
  provenance-logger:python-core logger
```

**Or with docker-compose:**

```bash
docker compose --profile logger up -d
```

### Verifier Mode (Dashboard + API)

```bash
docker run --rm -it \
  --network host \
  -v $(pwd)/data:/data \
  -v $(pwd)/keys:/keys \
  provenance-logger:node-ui verifier
```

**Or with docker-compose:**

```bash
docker compose --profile verifier up -d
```

**Access:**
- Dashboard: http://jetson-ip:8080
- API: http://jetson-ip:5000

## 4. Verify

```bash
# One-time CLI verification
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/keys:/keys \
  provenance-logger:python-core verify-cli
```

## Common Commands

```bash
# View logs
docker compose logs -f

# Stop container
docker compose down

# Interactive shell
docker run --rm -it \
  --privileged \
  -v $(pwd)/data:/data \
  -v $(pwd)/config:/config \
  -v $(pwd)/keys:/keys \
  provenance-logger:python-core bash

# Check camera devices
v4l2-ctl --list-devices
```

## Outputs

- **Frames**: `data/frames/frame_*.jpg`
- **Chain DB**: `data/chain.db`
- **Export**: `data/chain_export.json` (on shutdown)
- **Keys**: `keys/private_key.pem` (auto-generated, **keep secure**)

## Architecture

**Base**: NVIDIA JetPack L4T r36.3.0 (JetPack 6.0)
**Python**: 3.10+
**Stack**: GStreamer, OpenCV, python-can, pyserial, cryptography, pynacl, flask
**Optional UI**: Node.js 18 + Express
**Target**: aarch64 (Jetson Orin Nano)

## Modes

| Mode | Description | Ports | Image |
|------|-------------|-------|-------|
| `logger` | Capture + hash chain | - | python-core |
| `verifier` | API + dashboard | 5000, 8080 | node-ui |
| `verify-cli` | One-time verification | - | python-core |
| `bash` | Interactive shell | - | python-core |

## Full Documentation

See `DOCKER_README.md` for complete documentation.
