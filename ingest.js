const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function loadPrivateKey() {
    const keyPath = path.join(__dirname, 'keys', 'private_key.pem');
    if (!fs.existsSync(keyPath)) {
        throw new Error('Private key not found. Run generate_keys.js first.');
    }
    return fs.readFileSync(keyPath, 'utf8');
}

function loadChain() {
    const chainPath = path.join(__dirname, 'chain.json');
    if (!fs.existsSync(chainPath)) {
        return [];
    }
    try {
        return JSON.parse(fs.readFileSync(chainPath, 'utf8'));
    } catch (err) {
        return [];
    }
}

function saveChain(chain) {
    const chainPath = path.join(__dirname, 'chain.json');
    fs.writeFileSync(chainPath, JSON.stringify(chain, null, 2));
}

function ingestFrame(framePath) {
    if (!fs.existsSync(framePath)) {
        throw new Error(`Frame file not found: ${framePath}`);
    }

    const frameData = fs.readFileSync(framePath);
    const frameHash = crypto.createHash('sha256').update(frameData).digest('hex');

    const chain = loadChain();
    const previousHash = chain.length > 0 ? chain[chain.length - 1].hash : '0'.repeat(64);

    // Generate single timestamp to use consistently
    const timestamp = new Date().toISOString();
    const index = chain.length;
    const frameFile = path.basename(framePath);

    const chainData = JSON.stringify({
        index: index,
        timestamp: timestamp,
        frameFile: frameFile,
        frameHash: frameHash,
        previousHash: previousHash
    });

    const privateKey = loadPrivateKey();
    const signature = crypto.sign(null, Buffer.from(chainData), privateKey).toString('hex');

    const chainDataHash = crypto.createHash('sha256').update(chainData).digest('hex');

    const entry = {
        index: index,
        timestamp: timestamp,
        frameFile: frameFile,
        frameHash: frameHash,
        previousHash: previousHash,
        signature: signature,
        hash: chainDataHash
    };

    chain.push(entry);
    saveChain(chain);

    return entry;
}

if (require.main === module) {
    const framePath = process.argv[2];
    if (!framePath) {
        console.error('Usage: node ingest.js <frame-path>');
        process.exit(1);
    }

    try {
        const entry = ingestFrame(framePath);
        console.log('Frame ingested successfully:');
        console.log(JSON.stringify(entry, null, 2));
    } catch (err) {
        console.error('Error ingesting frame:', err.message);
        process.exit(1);
    }
}

module.exports = { ingestFrame, loadChain };