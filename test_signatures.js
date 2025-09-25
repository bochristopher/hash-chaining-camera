const { ingestFrame } = require('./ingest.js');
const { verifyChain } = require('./verify.js');
const fs = require('fs');
const path = require('path');

console.log('🧪 Running signature verification unit tests...\n');

// Clean up any existing chain for fresh test
const chainPath = path.join(__dirname, 'chain.json');
if (fs.existsSync(chainPath)) {
    fs.unlinkSync(chainPath);
    console.log('🗑️  Cleared existing chain.json for clean test');
}

// Create a test image file
const testImagePath = path.join(__dirname, 'images', 'test_frame.jpg');
const testImageData = Buffer.from('FAKE_JPEG_DATA_FOR_TESTING');
fs.writeFileSync(testImagePath, testImageData);
console.log('📸 Created test image file');

// Test 1: Single frame ingest and verify
console.log('\n🔬 TEST 1: Single frame ingest and verification');
try {
    const entry = ingestFrame(testImagePath);
    console.log('✅ Frame ingested successfully');

    const verifyResult = verifyChain();
    if (verifyResult.success) {
        console.log('✅ Single frame verification PASSED');
    } else {
        console.log('❌ Single frame verification FAILED:', verifyResult);
    }
} catch (err) {
    console.error('❌ Test 1 failed:', err.message);
}

// Test 2: Multiple frame chain
console.log('\n🔬 TEST 2: Multiple frame chain verification');
try {
    // Create additional test images
    for (let i = 2; i <= 5; i++) {
        const testPath = path.join(__dirname, 'images', `test_frame_${i}.jpg`);
        const testData = Buffer.from(`FAKE_JPEG_DATA_FOR_TESTING_${i}`);
        fs.writeFileSync(testPath, testData);

        const entry = ingestFrame(testPath);
        console.log(`  ✅ Frame ${i} ingested (index: ${entry.index})`);
    }

    const verifyResult = verifyChain();
    if (verifyResult.success) {
        console.log(`✅ Multi-frame chain verification PASSED (${verifyResult.count} entries)`);
    } else {
        console.log('❌ Multi-frame chain verification FAILED:', verifyResult);
    }
} catch (err) {
    console.error('❌ Test 2 failed:', err.message);
}

// Test 3: JSON output verification
console.log('\n🔬 TEST 3: JSON output verification');
try {
    const verifyResult = verifyChain(true);  // JSON output
    console.log('JSON verification result:', verifyResult);

    if (typeof verifyResult === 'object' && 'success' in verifyResult) {
        console.log('✅ JSON output format correct');
    } else {
        console.log('❌ JSON output format incorrect');
    }
} catch (err) {
    console.error('❌ Test 3 failed:', err.message);
}

// Test 4: Signature consistency test
console.log('\n🔬 TEST 4: Signature consistency between ingest and verify');
const crypto = require('crypto');

try {
    // Load the current chain
    const chainData = JSON.parse(fs.readFileSync(chainPath, 'utf8'));
    const firstEntry = chainData[0];

    // Reconstruct the signing data manually
    const reconstructed = JSON.stringify({
        index: firstEntry.index,
        timestamp: firstEntry.timestamp,
        frameFile: firstEntry.frameFile,
        frameHash: firstEntry.frameHash,
        previousHash: firstEntry.previousHash
    });

    console.log('   Original entry data reconstruction check:');
    console.log(`   Index: ${firstEntry.index}`);
    console.log(`   Timestamp: ${firstEntry.timestamp}`);
    console.log(`   File: ${firstEntry.frameFile}`);
    console.log(`   Frame hash: ${firstEntry.frameHash.substring(0, 16)}...`);
    console.log(`   Previous hash: ${firstEntry.previousHash.substring(0, 16)}...`);
    console.log(`   Reconstructed: ${reconstructed}`);
    console.log(`   Stored signature: ${firstEntry.signature.substring(0, 32)}...`);

    // Try to verify manually
    const publicKey = fs.readFileSync(path.join(__dirname, 'keys', 'public_key.pem'), 'utf8');
    const signatureBuffer = Buffer.from(firstEntry.signature, 'hex');
    const isValid = crypto.verify(null, Buffer.from(reconstructed), publicKey, signatureBuffer);

    console.log(`   Manual verification result: ${isValid}`);

    if (isValid) {
        console.log('✅ Manual signature verification PASSED');
    } else {
        console.log('❌ Manual signature verification FAILED');
    }

} catch (err) {
    console.error('❌ Test 4 failed:', err.message);
}

console.log('\n🏁 Unit tests completed');

// Cleanup test files
try {
    fs.unlinkSync(testImagePath);
    for (let i = 2; i <= 5; i++) {
        const testPath = path.join(__dirname, 'images', `test_frame_${i}.jpg`);
        if (fs.existsSync(testPath)) {
            fs.unlinkSync(testPath);
        }
    }
    console.log('🧹 Test files cleaned up');
} catch (err) {
    console.log('⚠️  Could not clean up all test files:', err.message);
}