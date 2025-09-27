const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function loadPublicKey() {
    const keyPath = path.join(__dirname, 'keys', 'public_key.pem');
    if (!fs.existsSync(keyPath)) {
        throw new Error('Public key not found. Run generate_keys.js first.');
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
        throw new Error('Failed to load chain.json');
    }
}

function verifyChain(outputJson = false) {
    const chain = loadChain();
    if (chain.length === 0) {
        const result = { success: true, count: 0, message: 'Chain is empty' };
        if (outputJson) {
            console.log(JSON.stringify(result));
            return result;
        }
        console.log('Chain is empty - nothing to verify');
        return result;
    }

    const publicKey = loadPublicKey();

    for (let i = 0; i < chain.length; i++) {
        const entry = chain[i];

        // Check index sequence
        if (entry.index !== i) {
            const result = { success: false, atIndex: i, reason: 'index mismatch', count: chain.length };
            if (outputJson) {
                console.log(JSON.stringify(result));
                return result;
            }
            console.error(`Index mismatch at entry ${i}: expected ${i}, got ${entry.index}`);
            return result;
        }

        // Check previous hash linkage
        const expectedPreviousHash = i === 0 ? '0'.repeat(64) : chain[i - 1].hash;
        if (entry.previousHash !== expectedPreviousHash) {
            const result = { success: false, atIndex: i, reason: 'hash mismatch', count: chain.length };
            if (outputJson) {
                console.log(JSON.stringify(result));
                return result;
            }
            console.error(`Hash mismatch at entry ${i}`);
            return result;
        }

        // Verify frame file exists and hash matches
        const framePath = path.join(__dirname, 'images', entry.frameFile);
        if (!fs.existsSync(framePath)) {
            const result = { success: false, atIndex: i, reason: 'frame file missing', count: chain.length };
            if (outputJson) {
                console.log(JSON.stringify(result));
                return result;
            }
            console.error(`Frame file missing at entry ${i}: ${entry.frameFile}`);
            return result;
        }

        const frameData = fs.readFileSync(framePath);
        const computedFrameHash = crypto.createHash('sha256').update(frameData).digest('hex');
        if (entry.frameHash !== computedFrameHash) {
            const result = { success: false, atIndex: i, reason: 'frame hash mismatch', count: chain.length };
            if (outputJson) {
                console.log(JSON.stringify(result));
                return result;
            }
            console.error(`Frame hash mismatch at entry ${i}`);
            return result;
        }

        // Verify signature
        const chainData = JSON.stringify({
            index: entry.index,
            timestamp: entry.timestamp,
            frameFile: entry.frameFile,
            frameHash: entry.frameHash,
            previousHash: entry.previousHash
        });

        try {
            const signatureBuffer = Buffer.from(entry.signature, 'hex');
            const isValid = crypto.verify(null, Buffer.from(chainData), publicKey, signatureBuffer);

            if (!isValid) {
                const result = { success: false, atIndex: i, reason: 'signature verification failed', count: chain.length };
                if (outputJson) {
                    console.log(JSON.stringify(result));
                    return result;
                }
                console.error(`Signature verification failed at entry ${i}`);
                return result;
            }
        } catch (err) {
            const result = { success: false, atIndex: i, reason: 'signature verification error', count: chain.length };
            if (outputJson) {
                console.log(JSON.stringify(result));
                return result;
            }
            console.error(`Signature verification error at entry ${i}: ${err.message}`);
            return result;
        }

        // Verify computed hash
        const computedHash = crypto.createHash('sha256').update(chainData).digest('hex');
        if (entry.hash !== computedHash) {
            const result = { success: false, atIndex: i, reason: 'computed hash mismatch', count: chain.length };
            if (outputJson) {
                console.log(JSON.stringify(result));
                return result;
            }
            console.error(`Computed hash mismatch at entry ${i}`);
            return result;
        }
    }

    const result = { success: true, count: chain.length };
    if (outputJson) {
        console.log(JSON.stringify(result));
        return result;
    }
    console.log(`Chain verification successful! Verified ${chain.length} entries.`);
    return result;
}

if (require.main === module) {
    const outputJson = process.argv.includes('--json');
    try {
        verifyChain(outputJson);
    } catch (err) {
        if (outputJson) {
            console.log(JSON.stringify({ success: false, reason: err.message, count: 0 }));
        } else {
            console.error('Error during verification:', err.message);
        }
        process.exit(1);
    }
}

module.exports = { verifyChain };