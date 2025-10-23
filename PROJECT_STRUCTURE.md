# Provenance Logger - Project Structure

## Complete File Tree

```
provenance-logger/
│
├── Dockerfile                      # Multi-stage build (JetPack → Python → Node)
├── docker-compose.yml              # Deployment configuration
├── .dockerignore                   # Docker build exclusions
├── entrypoint.sh                   # Container mode switching script
├── build.sh                        # Convenience build script
│
├── DOCKER_README.md               # Complete container documentation
├── CONTAINER_QUICKSTART.md        # Quick start guide
├── PROJECT_STRUCTURE.md           # This file
│
├── python_core/                    # Python implementation (core)
│   ├── logger.py                   # Main logger entry point
│   ├── verifier.py                 # CLI verification tool
│   │
│   ├── lib/                        # Core libraries
│   │   ├── __init__.py
│   │   ├── camera.py               # GStreamer camera capture
│   │   ├── crypto.py               # Ed25519 signatures + SHA-256
│   │   ├── chain.py                # SQLAlchemy chain storage
│   │   └── sensors.py              # CAN/I2C/Serial adapters (placeholders)
│   │
│   └── api/                        # Web API
│       ├── __init__.py
│       └── server.py               # Flask REST API
│
├── node_ui/                        # Optional Node.js dashboard
│   ├── package.json                # Node dependencies
│   ├── server.js                   # Express web server
│   └── public/
│       ├── index.html              # Dashboard UI
│       └── app.js                  # Client-side JavaScript
│
├── config/                         # Configuration (mounted)
│   └── config.example.yaml         # Example configuration
│
├── data/                           # Runtime data (mounted, created on first run)
│   ├── frames/                     # Captured JPEG frames
│   ├── chain.db                    # SQLite chain database
│   └── chain_export.json           # JSON export (on shutdown)
│
└── keys/                           # Cryptographic keys (mounted, auto-generated)
    ├── private_key.pem             # Ed25519 private key (keep secure!)
    └── public_key.pem              # Ed25519 public key

Existing Files (Node.js implementation, not used in container):
├── server.js                       # Original Node.js server
├── ingest.js                       # Original ingestion script
├── verify.js                       # Original verification script
├── generate_keys.js                # Original key generation
├── package.json                    # Original Node dependencies
└── public/                         # Original dashboard
```

## Container Mount Points

### `/data` - Data Output Directory

**Created automatically on first run**

```
/data/
├── frames/                         # Captured images
│   ├── frame_2024-01-15T10-00-00-000Z.jpg
│   ├── frame_2024-01-15T10-00-02-000Z.jpg
│   └── ...
├── chain.db                        # SQLite database
└── chain_export.json               # JSON export (created on shutdown)
```

**Usage:**
```bash
-v $(pwd)/data:/data
```

### `/config` - Configuration Directory

**Must contain `config.yaml`** (copied from example on first run)

```
/config/
└── config.yaml                     # Camera and sensor configuration
```

**Usage:**
```bash
-v $(pwd)/config:/config
```

### `/keys` - Keys Directory

**Auto-generated on first run** (if empty)

```
/keys/
├── private_key.pem                 # Ed25519 private key (600 permissions)
└── public_key.pem                  # Ed25519 public key (644 permissions)
```

**Usage:**
```bash
-v $(pwd)/keys:/keys
```

## Device Access

### Camera Devices

```bash
--device /dev/video0:/dev/video0    # Primary USB camera
--device /dev/video1:/dev/video1    # Additional cameras
```

For CSI cameras, use `--privileged` mode.

### I2C Devices

```bash
--device /dev/i2c-0:/dev/i2c-0
--device /dev/i2c-1:/dev/i2c-1
```

### CAN Bus

Requires host network access:

```bash
--network host
--privileged
```

## Docker Images

### Stage 1: `provenance-logger:python-core`

**Size:** ~3.5GB
**Base:** nvcr.io/nvidia/l4t-jetpack:r36.3.0

**Contains:**
- Python 3.10+
- GStreamer with NVIDIA plugins
- OpenCV
- Python packages (python-can, pyserial, cryptography, pynacl, pyyaml, sqlalchemy, flask)
- Python core modules

**Use for:**
- Logger mode
- Verifier mode (API only, no dashboard)
- CLI verification

### Stage 2: `provenance-logger:node-ui`

**Size:** ~4.2GB
**Base:** provenance-logger:python-core

**Contains:**
- Everything from python-core stage
- Node.js 18.x
- Express web server
- Dashboard UI

**Use for:**
- Verifier mode with web dashboard
- Full-featured deployment

## Python Module Structure

### `python_core/logger.py`

Main logger application

**Responsibilities:**
- Initialize camera, crypto, sensors
- Capture frames at intervals
- Build hash chain entries
- Store in database
- Handle graceful shutdown

**CLI:**
```bash
python3 logger.py --config /config/config.yaml --data /data --keys /keys
python3 logger.py --generate-keys
```

### `python_core/verifier.py`

Chain verification tool

**Responsibilities:**
- Load chain from database
- Verify signatures
- Verify frame hashes
- Verify chain linkage
- Export reports

**CLI:**
```bash
python3 verifier.py --data /data --keys /keys
python3 verifier.py --export /data/report.json
python3 verifier.py --json
```

### `python_core/lib/camera.py`

GStreamer camera interface

**Classes:**
- `JetsonCamera` - Camera capture with hardware acceleration

**Supports:**
- CSI (MIPI) cameras via nvarguscamerasrc
- USB cameras via v4l2src (MJPEG + raw)
- Hardware JPEG encoding

### `python_core/lib/crypto.py`

Cryptographic utilities

**Classes:**
- `ProvenanceCrypto` - Ed25519 + SHA-256 operations

**Methods:**
- `generate_keypair()` - Create new Ed25519 keys
- `create_chain_entry()` - Sign and hash entry
- `verify_entry_signature()` - Verify Ed25519 signature
- `hash_file()` - SHA-256 file hashing

### `python_core/lib/chain.py`

Chain storage with SQLAlchemy

**Classes:**
- `ChainEntry` - Database model
- `ProvenanceChain` - Chain management

**Methods:**
- `add_entry()` - Insert new entry
- `get_entry_by_index()` - Retrieve entry
- `get_all_entries()` - Get full chain
- `export_to_json()` - Export to JSON
- `import_from_json()` - Import from JSON

### `python_core/lib/sensors.py`

Sensor adapters (placeholders)

**Classes:**
- `CANAdapter` - CAN bus interface
- `I2CAdapter` - I2C sensor interface
- `SerialAdapter` - Serial/UART interface
- `SensorManager` - Unified manager

**Note:** Currently placeholders for future implementation

### `python_core/api/server.py`

Flask REST API

**Endpoints:**
- `GET /api/status` - System status
- `GET /api/chain` - Full chain (with pagination)
- `GET /api/chain/<index>` - Specific entry
- `GET /api/verify` - Run verification
- `GET /api/latest-frame` - Latest frame image
- `GET /api/frame/<index>` - Specific frame image

## Node.js Dashboard Structure

### `node_ui/server.js`

Express web server

**Responsibilities:**
- Serve static dashboard files
- Optional API proxy to Flask
- Health check endpoint

**Ports:**
- 8080 (dashboard)
- Proxies to Flask on 5000

### `node_ui/public/index.html`

Dashboard UI

**Features:**
- Real-time status display
- Latest frame preview
- Chain log (20 most recent)
- Verification trigger

### `node_ui/public/app.js`

Client-side application

**Responsibilities:**
- Fetch status from API
- Auto-refresh every 3 seconds
- Display verification results
- Handle frame updates

## Operating Modes

### Logger Mode

**Entry:** `entrypoint.sh logger`
**Process:** `python3 /app/python_core/logger.py`

**Flow:**
1. Check/generate keys
2. Test camera
3. Connect sensors
4. Enter capture loop
5. On Ctrl+C: export chain and shutdown

### Verifier Mode (with UI)

**Entry:** `entrypoint.sh verifier`
**Processes:**
- `python3 /app/python_core/api/server.py` (port 5000)
- `npm start` in `/app/node_ui` (port 8080)

**Flow:**
1. Start Flask API in background
2. Wait for Flask to initialize
3. Start Node.js dashboard
4. Dashboard calls Flask API

### Verifier Mode (Python only)

**Entry:** `entrypoint.sh verifier` (with python-core image)
**Process:** `python3 /app/python_core/api/server.py`

**Flow:**
1. Start Flask API on port 5000
2. Expose REST endpoints
3. No dashboard UI

### CLI Verification

**Entry:** `entrypoint.sh verify-cli`
**Process:** `python3 /app/python_core/verifier.py`

**Flow:**
1. Load chain from database
2. Run verification
3. Print results
4. Exit with code (0 = valid, 1 = invalid)

## Configuration Structure

### `config.yaml`

```yaml
camera:
  camera: "USB" | "CSI"
  usb_device: "/dev/video0"
  width: 1920
  height: 1080
  framerate: 30
  jpeg_quality: 85

capture_interval_ms: 2000

sensors:
  can:
    enabled: false
    interface: "can0"
    bitrate: 500000
  i2c:
    enabled: false
    bus: 1
    address: "0x68"
  serial:
    enabled: false
    port: "/dev/ttyTHS0"
    baudrate: 9600

logging:
  level: "INFO"

metadata:
  device_id: "jetson-001"
  location: "field"
  project: "provenance-stack"
```

## Database Schema

### `chain_entries` Table

```sql
CREATE TABLE chain_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    index INTEGER UNIQUE NOT NULL,
    timestamp VARCHAR(32) NOT NULL,
    frame_path VARCHAR(512) NOT NULL,
    frame_hash VARCHAR(64) NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    entry_hash VARCHAR(64) NOT NULL,
    signature VARCHAR(256) NOT NULL,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Data Flow

### Logger Mode

```
Camera Capture (GStreamer)
    ↓
JPEG Frame → /data/frames/frame_<timestamp>.jpg
    ↓
SHA-256 Hash
    ↓
Sensor Data (optional) → CAN/I2C/Serial
    ↓
Chain Entry Creation
    ├─ index
    ├─ timestamp
    ├─ frame_hash
    ├─ previous_hash
    └─ metadata
    ↓
Ed25519 Signature
    ↓
Entry Hash (SHA-256)
    ↓
SQLite Database → /data/chain.db
```

### Verifier Mode

```
Load Chain from Database
    ↓
For each entry:
    ├─ Verify frame file exists
    ├─ Verify frame hash matches
    ├─ Verify Ed25519 signature
    └─ Verify entry hash
    ↓
Verify chain linkage
    └─ Check previous_hash references
    ↓
Generate Result
    ├─ CLI: Print to console
    ├─ JSON: Export to file
    └─ API: Return via HTTP
```

## Build Process

```
Dockerfile
    ↓
Stage 1: python-core
    ├─ Base: NVIDIA JetPack L4T r36.3.0
    ├─ Install system packages
    ├─ Install Python packages
    ├─ Copy python_core/
    ├─ Copy entrypoint.sh
    └─ Tag: provenance-logger:python-core
    ↓
Stage 2: node-ui
    ├─ Inherit from python-core
    ├─ Install Node.js 18
    ├─ Copy node_ui/
    ├─ npm install
    └─ Tag: provenance-logger:node-ui
```

## Ports and Network

### Host Network Mode

Used for:
- CAN bus access
- Simplified device access

```bash
docker run --network host ...
```

**Ports:**
- 5000: Flask API
- 8080: Node.js dashboard

### Bridge Network Mode

Not recommended for Jetson deployment due to device access requirements.

## Storage Estimates

### Frame Storage

**1920x1080 @ JPEG quality 85:**
- ~200-500 KB per frame
- ~1.2-3.0 MB per minute (2s interval)
- ~1.7-4.3 GB per day
- ~52-130 GB per month

**Recommendations:**
- Use lower resolution for extended deployments
- Implement frame rotation/cleanup
- External storage for large deployments

### Database Size

**Chain database overhead:**
- ~500 bytes per entry
- ~15 KB per minute
- ~21 MB per day
- ~650 MB per month

## File Permissions

### Keys

```
/keys/
├── private_key.pem    # 600 (rw-------)  CRITICAL
└── public_key.pem     # 644 (rw-r--r--)  Safe to share
```

### Data

```
/data/
├── frames/            # 755 (rwxr-xr-x)
│   └── *.jpg          # 644 (rw-r--r--)
├── chain.db           # 644 (rw-r--r--)
└── chain_export.json  # 644 (rw-r--r--)
```

### Config

```
/config/
└── config.yaml        # 644 (rw-r--r--)
```

## Security Considerations

1. **Private Key Protection**
   - Never commit to git
   - Backup securely (encrypted)
   - Restrict file permissions (600)

2. **Container Isolation**
   - Use specific device mounts
   - Avoid `--privileged` if possible
   - Use read-only mounts where appropriate

3. **Network Exposure**
   - API has no authentication (local use only)
   - Use firewall rules for production
   - Consider adding API authentication

4. **Data Integrity**
   - Tamper detection via hash chain
   - Signature verification with public key
   - Frame hash validation
