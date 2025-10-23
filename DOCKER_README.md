# Provenance Logger Container

A containerized cryptographic provenance logging system for Jetson Orin Nano with GStreamer hardware acceleration.

## Overview

The Provenance Logger captures camera frames with sensor context and builds a tamper-evident hash chain using Ed25519 digital signatures and SHA-256 hashing. This container implementation provides:

- **Python core** for all logging, cryptography, and verification
- **Optional Node.js dashboard** for web-based monitoring
- **Multi-stage Docker build** optimized for NVIDIA JetPack L4T runtime
- **Two operating modes**: logger and verifier

## Architecture

```
provenance-logger/
├── Dockerfile              # Multi-stage build (Python core + Node UI)
├── docker-compose.yml      # Easy deployment configuration
├── entrypoint.sh          # Mode switching script
├── python_core/           # Python implementation
│   ├── logger.py          # Main logger entry point
│   ├── verifier.py        # Chain verification CLI
│   ├── lib/               # Core libraries
│   │   ├── camera.py      # GStreamer camera capture
│   │   ├── crypto.py      # Ed25519 + SHA-256 crypto
│   │   ├── chain.py       # SQLAlchemy chain storage
│   │   └── sensors.py     # CAN/I2C/Serial adapters
│   └── api/
│       └── server.py      # Flask API for verification
├── node_ui/               # Optional dashboard
│   ├── server.js          # Express server
│   └── public/
│       ├── index.html     # Dashboard UI
│       └── app.js         # Client-side code
└── config/
    └── config.example.yaml

Mount Points:
├── /data    → Run outputs (frames, chain.db, exports)
├── /config  → YAML configuration
└── /keys    → Ed25519 keypair storage

Device Access:
├── /dev/video*   → Camera devices
├── /dev/i2c-*    → I2C sensors
└── can0          → CAN bus
```

## Quick Start

### 1. Build the Container

```bash
# Python-only image (smaller, ~3.5GB)
docker build --target python-core -t provenance-logger:python-core .

# Python + Node.js UI image (full features, ~4.2GB)
docker build --target node-ui -t provenance-logger:node-ui .
```

### 2. Configure Camera

Create or edit `config/config.yaml`:

```yaml
camera:
  camera: "USB"              # "CSI" or "USB"
  usb_device: "/dev/video0"
  width: 1920
  height: 1080
  jpeg_quality: 85

capture_interval_ms: 2000
```

### 3. Run Logger Mode

**Option A: Docker run (simple)**

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

**Option B: Docker Compose (recommended)**

```bash
# Start logger in background
docker compose --profile logger up -d

# View logs
docker compose logs -f logger

# Stop logger
docker compose down
```

### 4. Run Verifier Mode

**With Dashboard (Python + Node.js):**

```bash
# Using docker-compose
docker compose --profile verifier up -d

# Access dashboard at http://jetson-ip:8080
# API available at http://jetson-ip:5000
```

**Python-only (API only):**

```bash
docker compose --profile verifier-python up -d

# API available at http://jetson-ip:5000/api/status
```

**One-time CLI verification:**

```bash
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/keys:/keys \
  provenance-logger:python-core verify-cli
```

## Operating Modes

### Logger Mode

Continuously captures frames and builds the hash chain:

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

**Outputs:**
- `/data/frames/` - Captured JPEG frames
- `/data/chain.db` - SQLite database with chain entries
- `/data/chain_export.json` - JSON export (on shutdown)

### Verifier Mode

Provides verification via web API and dashboard:

```bash
docker run --rm -it \
  --network host \
  -v $(pwd)/data:/data \
  -v $(pwd)/keys:/keys \
  provenance-logger:node-ui verifier
```

**Endpoints:**
- `http://jetson-ip:8080` - Web dashboard (Node.js)
- `http://jetson-ip:5000/api/status` - Chain status
- `http://jetson-ip:5000/api/chain` - Full chain data
- `http://jetson-ip:5000/api/verify` - Run verification
- `http://jetson-ip:5000/api/latest-frame` - Latest frame image

### CLI Verification

One-time verification without web server:

```bash
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/keys:/keys \
  provenance-logger:python-core verify-cli

# Export verification report
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/keys:/keys \
  provenance-logger:python-core verify-cli \
  --export /data/verification_report.json

# JSON output
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/keys:/keys \
  provenance-logger:python-core verify-cli --json
```

## Configuration

### Camera Settings

```yaml
camera:
  camera: "USB"              # "CSI" for MIPI camera, "USB" for USB camera
  usb_device: "/dev/video0"  # USB device path
  width: 1920                # Capture resolution
  height: 1080
  framerate: 30              # GStreamer framerate
  jpeg_quality: 85           # JPEG quality (1-100)

capture_interval_ms: 2000    # Capture interval in milliseconds
```

### Sensor Integration (Placeholder)

```yaml
sensors:
  can:
    enabled: false
    interface: "can0"
    bitrate: 500000

  i2c:
    enabled: false
    bus: 1
    address: "0x68"          # Example: MPU-6050 IMU

  serial:
    enabled: false
    port: "/dev/ttyTHS0"
    baudrate: 9600
```

## Device Access

### Camera Devices

```bash
# List available cameras
v4l2-ctl --list-devices

# Check camera capabilities
v4l2-ctl --device=/dev/video0 --list-formats-ext

# Grant container access
docker run --device /dev/video0 ...
```

### I2C Devices

```bash
# List I2C buses
ls /dev/i2c-*

# Scan I2C devices
i2cdetect -y 1

# Grant container access
docker run --device /dev/i2c-0 --device /dev/i2c-1 ...
```

### CAN Bus

```bash
# Enable CAN interface
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

# Check CAN status
ip -details link show can0

# Container needs host network access
docker run --network host --privileged ...
```

## Build Details

### Multi-stage Build

**Stage 1: Python Core (~3.5GB)**
- Base: `nvcr.io/nvidia/l4t-jetpack:r36.3.0` (JetPack 6.0)
- Python 3.10+
- GStreamer with hardware acceleration
- OpenCV
- Python packages: python-can, pyserial, cryptography, pynacl, pyyaml, sqlalchemy, flask

**Stage 2: Node UI (~4.2GB)**
- Inherits from Python core
- Node.js 18.x
- Express dashboard

### Build Arguments

```bash
# Specify build stage
docker build --target python-core -t provenance-logger:python-core .
docker build --target node-ui -t provenance-logger:node-ui .

# Build both with docker-compose
docker compose build
```

## Data Management

### Export Chain

```bash
# Chain is auto-exported on shutdown to /data/chain_export.json

# Manual export via Python
docker exec provenance-logger python3 -c "
from pathlib import Path
from python_core.lib.chain import ProvenanceChain
chain = ProvenanceChain(Path('/data/chain.db'))
chain.export_to_json(Path('/data/export.json'))
"
```

### Import Chain

```bash
docker exec provenance-logger python3 -c "
from pathlib import Path
from python_core.lib.chain import ProvenanceChain
chain = ProvenanceChain(Path('/data/chain.db'))
chain.import_from_json(Path('/data/export.json'))
"
```

### Backup

```bash
# Backup data directory
tar -czf provenance-backup-$(date +%Y%m%d).tar.gz data/

# Backup keys separately (keep secure!)
tar -czf provenance-keys-$(date +%Y%m%d).tar.gz keys/
```

## Key Management

### Generate Keys

```bash
# Keys are auto-generated on first run

# Manual generation
docker run --rm \
  -v $(pwd)/keys:/keys \
  provenance-logger:python-core logger --generate-keys
```

**Important:**
- Private key: `/keys/private_key.pem` (600 permissions) - **KEEP SECRET**
- Public key: `/keys/public_key.pem` (644 permissions) - Safe to share

### Key Security

```bash
# Set proper permissions
chmod 600 keys/private_key.pem
chmod 644 keys/public_key.pem

# Backup private key securely
gpg --encrypt --recipient your@email.com keys/private_key.pem
```

## Troubleshooting

### Camera Not Detected

```bash
# Check camera devices
ls -l /dev/video*

# Test camera outside container
gst-launch-1.0 -e v4l2src device=/dev/video0 num-buffers=1 ! \
  image/jpeg,width=1920,height=1080 ! filesink location=test.jpg

# Check container privileges
docker run --privileged --device /dev/video0 ...
```

### Permission Denied

```bash
# Run with privileged mode
docker run --privileged ...

# Or grant specific capabilities
docker run --cap-add=SYS_ADMIN ...
```

### Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :5000
sudo lsof -i :8080

# Kill conflicting process or change port
docker run -e PORT=8081 ...
```

### GStreamer Errors

```bash
# Enable debug logging
docker run -e GST_DEBUG=3 ...

# Check GStreamer plugins
docker run --rm provenance-logger:python-core \
  bash -c "gst-inspect-1.0 | grep nvjpegenc"
```

## API Reference

### Status Endpoint

```bash
curl http://jetson-ip:5000/api/status
```

Response:
```json
{
  "status": "online",
  "timestamp": "2024-01-15T10:30:00Z",
  "chain_length": 150,
  "latest_entry": {
    "index": 149,
    "timestamp": "2024-01-15T10:29:58Z",
    "entry_hash": "abc123..."
  }
}
```

### Chain Data

```bash
# Get full chain
curl http://jetson-ip:5000/api/chain

# Paginated
curl http://jetson-ip:5000/api/chain?limit=20&offset=0

# Specific entry
curl http://jetson-ip:5000/api/chain/42
```

### Verification

```bash
curl http://jetson-ip:5000/api/verify
```

Response:
```json
{
  "valid": true,
  "total_entries": 150,
  "verified_entries": 150,
  "failed_entries": 0,
  "failures": [],
  "verification_time": "0:00:02.345"
}
```

### Frames

```bash
# Latest frame
curl http://jetson-ip:5000/api/latest-frame -o latest.jpg

# Specific frame
curl http://jetson-ip:5000/api/frame/42 -o frame_42.jpg
```

## Performance

- **Capture rate**: Up to 30 fps (configurable via `capture_interval_ms`)
- **Frame size**: ~200-500KB at 1920x1080 JPEG quality 85
- **Database**: SQLite (lightweight, file-based)
- **Verification**: ~100 entries/second
- **Memory usage**: ~500MB Python + ~200MB Node.js (if using dashboard)

## Security & Privacy

### Cryptographic Guarantees

- **Ed25519** digital signatures (industry standard)
- **SHA-256** hash chaining (cryptographically secure)
- **Tamper detection**: Any modification breaks verification
- **Timestamp integrity**: Prevents replay attacks

### Privacy Considerations

This system provides **proof-only provenance**, meaning:

- Frame integrity is cryptographically verified
- Chain linkage is tamper-evident
- **No external transmission** - all processing is local
- **No cloud dependencies** - runs entirely on Jetson

### Data Retention

- Frames stored locally in `/data/frames/`
- Chain database in `/data/chain.db`
- You control data lifecycle (retention, deletion)

**To limit storage:**

```yaml
# Add to config.yaml (future feature)
storage:
  max_frames: 10000
  retention_days: 30
  auto_cleanup: true
```

## Performance Tuning

### Reduce Storage

```yaml
camera:
  width: 1280          # Lower resolution
  height: 720
  jpeg_quality: 70     # Lower quality

capture_interval_ms: 5000  # Capture less frequently
```

### Optimize Database

```bash
# Vacuum database periodically
docker exec provenance-logger python3 -c "
import sqlite3
conn = sqlite3.connect('/data/chain.db')
conn.execute('VACUUM')
conn.close()
"
```

## Development

### Interactive Shell

```bash
docker run --rm -it \
  --privileged \
  --network host \
  --device /dev/video0 \
  -v $(pwd)/data:/data \
  -v $(pwd)/config:/config \
  -v $(pwd)/keys:/keys \
  provenance-logger:python-core bash
```

### Testing

```bash
# Test camera
docker run --rm -it --device /dev/video0 \
  provenance-logger:python-core python3 -c "
from lib.camera import JetsonCamera
camera = JetsonCamera({'camera': 'USB', 'usb_device': '/dev/video0'})
camera.test_camera()
"

# Test crypto
docker run --rm -it -v $(pwd)/keys:/keys \
  provenance-logger:python-core python3 -c "
from lib.crypto import ProvenanceCrypto
crypto = ProvenanceCrypto('/keys')
crypto.generate_keypair()
"
```

## License

See main repository for license information.

## Support

For issues, questions, or contributions, see the main repository README.
