const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const { execFile } = require('child_process');
const { ingestFrame } = require('./ingest.js');
const { verifyChain } = require('./verify.js');

const PORT = 8080;
let config;
let captureInterval;
const sseClients = new Set();

// Load configuration
function loadConfig() {
    try {
        const configPath = path.join(__dirname, 'config.json');
        config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        console.log('📁 Configuration loaded:', config);
    } catch (err) {
        console.error('❌ Failed to load config.json:', err.message);
        process.exit(1);
    }
}

// Utility function to execute commands with Promise
function execCapture(command, args = []) {
    return new Promise((resolve, reject) => {
        execFile(command, args, (error, stdout, stderr) => {
            if (error) {
                reject(new Error(`Command failed: ${error.message}\nStderr: ${stderr}`));
            } else {
                resolve({ stdout, stderr });
            }
        });
    });
}

// Try multiple GStreamer pipelines until one succeeds
async function tryPipelines(pipelines) {
    for (const pipeline of pipelines) {
        try {
            console.log(`🎥 Trying pipeline: ${pipeline.join(' ')}`);
            await execCapture('gst-launch-1.0', pipeline);
            return true;
        } catch (err) {
            console.log(`❌ Pipeline failed: ${err.message}`);
            continue;
        }
    }
    throw new Error('All capture pipelines failed');
}

// Capture frame using GStreamer
async function captureFrame() {
    const latestPath = path.join(__dirname, 'images', 'latest.jpg');

    try {
        if (config.camera === 'CSI') {
            // CSI camera pipeline
            const pipeline = [
                '-e', 'nvarguscamerasrc', 'num-buffers=1', '!',
                `video/x-raw(memory:NVMM),width=${config.width},height=${config.height},format=NV12,framerate=30/1`, '!',
                `nvjpegenc`, `quality=${config.jpegQuality}`, '!',
                'filesink', `location=${latestPath}`
            ];

            await execCapture('gst-launch-1.0', pipeline);
        } else if (config.camera === 'USB') {
            // USB camera pipelines - try MJPEG first, then raw fallback
            const mjpegPipeline = [
                '-e', 'v4l2src', `device=${config.usbDevice}`, 'num-buffers=1', '!',
                `image/jpeg,width=${config.width},height=${config.height},framerate=30/1`, '!',
                'jpegparse', '!',
                'filesink', `location=${latestPath}`
            ];

            const rawPipeline = [
                '-e', 'v4l2src', `device=${config.usbDevice}`, 'num-buffers=1', '!',
                `video/x-raw,format=YUY2,width=${config.width},height=${config.height},framerate=30/1`, '!',
                'nvvidconv', '!',
                'nvjpegenc', `quality=${config.jpegQuality}`, '!',
                'filesink', `location=${latestPath}`
            ];

            await tryPipelines([mjpegPipeline, rawPipeline]);
        } else {
            throw new Error(`Unknown camera type: ${config.camera}`);
        }

        return latestPath;
    } catch (err) {
        console.error('📸 Capture failed:', err.message);
        throw err;
    }
}

// Process captured frame
async function processFrame(framePath) {
    // Create timestamped copy
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const timestampedPath = path.join(__dirname, 'images', `frame_${timestamp}.jpg`);

    try {
        fs.copyFileSync(framePath, timestampedPath);

        // Ingest the frame
        const entry = ingestFrame(timestampedPath);

        // Broadcast to SSE clients
        broadcastSSE({
            type: 'chain_head',
            index: entry.index,
            frame: path.basename(timestampedPath),
            hash: entry.hash,
            timestamp: entry.timestamp
        });

        // Verify chain
        const verifyResult = verifyChain(true);
        if (verifyResult.success) {
            broadcastSSE({
                type: 'verify_ok',
                count: verifyResult.count
            });
        } else {
            broadcastSSE({
                type: 'verify_fail',
                atIndex: verifyResult.atIndex,
                reason: verifyResult.reason,
                count: verifyResult.count
            });
        }

        console.log(`✅ Frame processed: ${path.basename(timestampedPath)} (index: ${entry.index})`);

    } catch (err) {
        console.error('❌ Frame processing failed:', err.message);
        broadcastSSE({
            type: 'error',
            message: `Frame processing failed: ${err.message}`
        });
    }
}

// Broadcast message to all SSE clients
function broadcastSSE(data) {
    const message = `data: ${JSON.stringify(data)}\n\n`;
    for (const res of sseClients) {
        try {
            res.write(message);
        } catch (err) {
            sseClients.delete(res);
        }
    }
}

// Start capture loop
function startCaptureLoop() {
    captureInterval = setInterval(async () => {
        try {
            const framePath = await captureFrame();
            await processFrame(framePath);
        } catch (err) {
            console.error('🔄 Capture loop error:', err.message);
            broadcastSSE({
                type: 'error',
                message: `Capture failed: ${err.message}`
            });
        }
    }, config.captureIntervalMs);

    console.log(`🔄 Capture loop started (interval: ${config.captureIntervalMs}ms)`);
}

// Tamper with a random existing frame
function tamperFrame() {
    const imagesDir = path.join(__dirname, 'images');
    const files = fs.readdirSync(imagesDir).filter(f => f.startsWith('frame_') && f.endsWith('.jpg'));

    if (files.length === 0) {
        throw new Error('No frames to tamper with');
    }

    const randomFile = files[Math.floor(Math.random() * files.length)];
    const filePath = path.join(imagesDir, randomFile);

    // Read file and flip a byte in the middle
    const data = fs.readFileSync(filePath);
    const middleIndex = Math.floor(data.length / 2);
    data[middleIndex] = data[middleIndex] ^ 0xFF; // Flip all bits
    fs.writeFileSync(filePath, data);

    return randomFile;
}

// HTTP server
const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    const pathname = parsedUrl.pathname;

    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // Routes
    if (pathname === '/') {
        // Serve dashboard
        const indexPath = path.join(__dirname, 'public', 'index.html');
        if (fs.existsSync(indexPath)) {
            res.writeHead(200, { 'Content-Type': 'text/html' });
            fs.createReadStream(indexPath).pipe(res);
        } else {
            res.writeHead(404);
            res.end('Dashboard not found');
        }
    } else if (pathname === '/app.js') {
        const appPath = path.join(__dirname, 'public', 'app.js');
        if (fs.existsSync(appPath)) {
            res.writeHead(200, { 'Content-Type': 'application/javascript' });
            fs.createReadStream(appPath).pipe(res);
        } else {
            res.writeHead(404);
            res.end('app.js not found');
        }
    } else if (pathname === '/styles.css') {
        const cssPath = path.join(__dirname, 'public', 'styles.css');
        if (fs.existsSync(cssPath)) {
            res.writeHead(200, { 'Content-Type': 'text/css' });
            fs.createReadStream(cssPath).pipe(res);
        } else {
            res.writeHead(404);
            res.end('styles.css not found');
        }
    } else if (pathname === '/latest.jpg') {
        const latestPath = path.join(__dirname, 'images', 'latest.jpg');
        if (fs.existsSync(latestPath)) {
            res.writeHead(200, { 'Content-Type': 'image/jpeg' });
            fs.createReadStream(latestPath).pipe(res);
        } else {
            res.writeHead(404);
            res.end('No image captured yet');
        }
    } else if (pathname === '/events') {
        // SSE endpoint
        res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        });

        sseClients.add(res);

        // Send initial ping
        res.write('data: {"type":"connected"}\n\n');

        // Keep-alive ping every 20 seconds
        const pingInterval = setInterval(() => {
            try {
                res.write(': ping\n\n');
            } catch (err) {
                clearInterval(pingInterval);
                sseClients.delete(res);
            }
        }, 20000);

        req.on('close', () => {
            clearInterval(pingInterval);
            sseClients.delete(res);
        });
    } else if (pathname === '/tamper' && req.method === 'POST') {
        try {
            const tamperedFile = tamperFrame();
            broadcastSSE({
                type: 'tampered',
                file: tamperedFile
            });
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true, file: tamperedFile }));
        } catch (err) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: false, error: err.message }));
        }
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
});

// Initialize server
function initialize() {
    loadConfig();

    // Ensure directories exist
    const imagesDir = path.join(__dirname, 'images');
    if (!fs.existsSync(imagesDir)) {
        fs.mkdirSync(imagesDir);
    }

    // Start server
    server.listen(PORT, () => {
        console.log(`🚀 Hash-chaining camera server running at http://localhost:${PORT}/`);
        console.log(`📹 Camera type: ${config.camera}`);

        // Start capture loop after a short delay
        setTimeout(startCaptureLoop, 2000);
    });
}

// Cleanup on exit
process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down server...');
    if (captureInterval) {
        clearInterval(captureInterval);
    }
    server.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
    });
});

initialize();