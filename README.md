# Hash-Chaining Camera for Jetson Orin Nano

A real-time provenance tracking camera system using Ed25519 digital signatures and SHA-256 hash chaining. Designed specifically for Jetson Orin Nano with GStreamer hardware acceleration.

<p align="center">
  <video src="https://i.imgur.com/XtW05gm.mp4" width="720" autoplay loop muted playsinline></video>
  <br>
  <em>Hash-Chained Sensor Provenance Logging in Action 🚀</em>
</p>

## Features

- **Hardware-accelerated capture** using Jetson's GStreamer elements
- **Cryptographic provenance** with Ed25519 + SHA-256 hash chaining
- **Real-time dashboard** with live preview and chain monitoring
- **Tamper detection** with immediate visual feedback
- **Zero external dependencies** - uses only Node.js built-ins

[![Untampered vs Tampered Comparison](https://i.imgur.com/ClhetxX.png)](https://imgur.com/a/hash-chain-camera-BFvuRRk)

## Quick Start

### Prerequisites (run these commands on your Jetson)

```bash
# Install GStreamer and camera utilities
sudo apt-get update
sudo apt-get install -y gstreamer1.0-tools gstreamer1.0-plugins-good \
                        gstreamer1.0-plugins-bad v4l-utils

# Ensure nvargus-daemon is running (for CSI cameras)
sudo systemctl status nvargus-daemon
```

### Setup and Run

```bash
# Navigate to the project
cd hash-chaining-camera

# Generate Ed25519 keypair
npm run generate-keys

# Configure camera (edit config.json)
# For CSI camera: set "camera": "CSI"
# For USB camera: set "camera": "USB" and adjust "usbDevice"

# Start the real-time dashboard
npm run demo:dashboard
```

Open http://your-jetson-ip:8080 in your browser.

## Project Structure

```
hash-chaining-camera/
├── package.json          # npm scripts and metadata
├── config.json          # Camera configuration
├── server.js            # Main server with GStreamer + SSE
├── generate_keys.js     # Ed25519 keypair generation
├── ingest.js           # Hash chain ingestion
├── verify.js           # Chain verification
├── ai_quality.py       # Optional quality assessment
├── keys/               # Ed25519 keys (generated)
├── images/             # Captured frames
├── scripts/
│   └── tamper_one.js   # Tamper demonstration
└── public/             # Dashboard assets
    ├── index.html      # Main dashboard
    ├── app.js          # Real-time client
    └── styles.css      # Dashboard styling
```

## Configuration

Edit `config.json` to match your setup:

```json
{
  "camera": "CSI",              // "CSI" or "USB"
  "usbDevice": "/dev/video0",   // USB camera device path
  "width": 1920,               // Capture resolution
  "height": 1080,
  "jpegQuality": 85,           // JPEG compression quality
  "captureIntervalMs": 2000    // Capture interval
}
```

### Camera Setup

**For CSI (MIPI) cameras:**
- Uses `nvarguscamerasrc` with hardware JPEG encoding
- Requires `nvargus-daemon` to be running

**For USB cameras:**
- First tries MJPEG fast path (`v4l2src` → `jpegparse`)
- Falls back to raw conversion (`v4l2src` → `nvvidconv` → `nvjpegenc`)

List your USB cameras:
```bash
v4l2-ctl --list-devices
```

## Usage

### Dashboard Features

- **Live Preview**: Shows camera feed, updates every ~2 seconds
- **Chain Log**: Real-time hash chain entries with timestamps
- **Status Indicator**:
  - 🟢 Green = All verifications pass
  - 🔴 Red blinking = Tamper detected
- **Tamper Button**: Demonstrates tampering by corrupting a random frame

### Command Line Tools

```bash
# Generate new keypair
npm run generate-keys

# Manually ingest a frame
npm run ingest images/frame_2024-01-01T12-00-00-000Z.jpg

# Verify entire chain
npm run verify

# Tamper with a random frame (for demo)
npm run tamper-demo
```

## How It Works

### Hash Chaining
1. Each frame is captured and saved with timestamp
2. Frame content is hashed (SHA-256)
3. Chain entry combines: index, timestamp, frame hash, previous chain hash
4. Entry is digitally signed with Ed25519 private key
5. Entry hash becomes the new chain head

### Verification
1. Verifies each frame file exists and matches stored hash
2. Validates Ed25519 signatures with public key
3. Confirms hash chain linkage (each entry references previous)
4. Detects any tampering immediately

### GStreamer Pipelines

**CSI Camera:**
```bash
gst-launch-1.0 -e nvarguscamerasrc num-buffers=1 ! \
  "video/x-raw(memory:NVMM),width=1920,height=1080,format=NV12,framerate=30/1" ! \
  nvjpegenc quality=85 ! \
  filesink location=images/latest.jpg
```

**USB Camera (MJPEG):**
```bash
gst-launch-1.0 -e v4l2src device=/dev/video0 num-buffers=1 ! \
  image/jpeg,width=1920,height=1080,framerate=30/1 ! \
  jpegparse ! \
  filesink location=images/latest.jpg
```

**USB Camera (Raw fallback):**
```bash
gst-launch-1.0 -e v4l2src device=/dev/video0 num-buffers=1 ! \
  "video/x-raw,format=YUY2,width=1920,height=1080,framerate=30/1" ! \
  nvvidconv ! \
  nvjpegenc quality=85 ! \
  filesink location=images/latest.jpg
```

## Troubleshooting

### Port 8080 in use
```bash
# Find what's using port 8080
sudo lsof -i :8080

# Kill the process or change PORT in server.js
```

### CSI Camera Issues
```bash
# Check nvargus-daemon status
sudo systemctl status nvargus-daemon

# Restart if needed
sudo systemctl restart nvargus-daemon

# Check for camera hardware
ls /dev/video*
```

### USB Camera Issues
```bash
# List available cameras
v4l2-ctl --list-devices

# Test camera capabilities
v4l2-ctl --device=/dev/video0 --list-formats-ext

# Check supported resolutions
v4l2-ctl --device=/dev/video0 --list-framesizes=MJPG
```

### GStreamer Debug
Add `GST_DEBUG=3` environment variable for detailed logging:
```bash
GST_DEBUG=3 npm run demo:dashboard
```

## Demo Presentation Script

1. **Open dashboard**: http://jetson-ip:8080
2. **Show live preview**: Camera feed updating every 2 seconds
3. **Show growing chain**: Each capture creates a new hash-chained entry
4. **Click "Tamper a Frame"**: Dashboard flashes red with tamper detection
5. **Explain**: "Any altered data breaks the chain, proving tampering occurred"
6. **Show recovery**: New frames continue building the chain

## Performance Notes

- Hardware JPEG encoding provides excellent performance
- 1920x1080 @ 85% quality ≈ 200-500KB per frame
- Chain verification is near-instantaneous
- Dashboard supports 50+ concurrent chain entries
- Memory usage remains stable during extended operation

## Security

- **Ed25519**: Industry-standard elliptic curve digital signatures
- **SHA-256**: Cryptographically secure hashing
- **No network keys**: All cryptography happens locally
- **Immutable chain**: Any tampering breaks cryptographic verification
- **Timestamp integrity**: Prevents replay attacks

## API Reference

**Server Endpoints:**
- `GET /` - Dashboard homepage
- `GET /latest.jpg` - Current camera frame
- `GET /events` - Server-Sent Events stream
- `POST /tamper` - Tamper with random frame (demo only)

**SSE Events:**
- `chain_head` - New frame ingested
- `verify_ok` - Verification passed
- `verify_fail` - Tamper detected
- `tampered` - Frame tampered (demo)
- `error` - System error

## Help Wanted

We welcome contributions! Here are some bite-sized tasks to get started:

### Easy Tasks (Good First Issues)
- **Improve dashboard visuals**: Add better styling, animations, or color themes
- **Add frame thumbnails**: Show small previews in the chain log
- **Export functionality**: Add buttons to export chain data as CSV/JSON
- **Configuration UI**: Build a web interface to edit `config.json`
- **Better error messages**: Make verification errors more user-friendly

### Medium Tasks
- **Add IMU logging**: Integrate accelerometer/gyroscope data into each frame entry
- **GPS coordinates**: Include location data in the provenance chain
- **Multiple camera support**: Allow switching between multiple USB cameras
- **Frame compression**: Add options for different image formats (WebP, HEIF)
- **Docker support**: Create Dockerfile for easy deployment

### Advanced Tasks
- **Mobile app**: Build React Native/Flutter app to view chains remotely
- **Blockchain integration**: Store chain hashes on-chain for immutable audit trail
- **Hardware security**: Integrate with TPM/HSM for key storage
- **Real-time streaming**: Add WebRTC for live video streaming with provenance
- **Machine learning**: Add AI-based tamper detection beyond hash verification

### Documentation
- **Tutorial videos**: Create setup and demo videos for different platforms
- **API documentation**: Document all endpoints and SSE events
- **Security analysis**: Write whitepaper on cryptographic guarantees
- **Performance benchmarks**: Test and document frame rates, storage usage

**Contributing**: Fork the repo, pick a task, and submit a pull request! For larger features, open an issue first to discuss the approach.

---

Built for audit-proof provenance tracking on Jetson Orin Nano
