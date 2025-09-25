const fs = require('fs');
const path = require('path');

function tamperRandomFrame() {
    const imagesDir = path.join(__dirname, '..', 'images');

    if (!fs.existsSync(imagesDir)) {
        console.error('❌ Images directory not found. Run the camera first to generate frames.');
        process.exit(1);
    }

    const files = fs.readdirSync(imagesDir).filter(f => f.startsWith('frame_') && f.endsWith('.jpg'));

    if (files.length === 0) {
        console.error('❌ No frame files found. Run the camera first to generate frames.');
        process.exit(1);
    }

    const randomFile = files[Math.floor(Math.random() * files.length)];
    const filePath = path.join(imagesDir, randomFile);

    console.log(`🔧 Tampering with frame: ${randomFile}`);

    try {
        // Read the file
        const data = fs.readFileSync(filePath);
        console.log(`📏 Original file size: ${data.length} bytes`);

        // Find a good position to tamper (avoid headers, target middle section)
        const tamperStart = Math.floor(data.length * 0.3);
        const tamperEnd = Math.floor(data.length * 0.7);
        const tamperIndex = tamperStart + Math.floor(Math.random() * (tamperEnd - tamperStart));

        const originalByte = data[tamperIndex];

        // Flip all bits in the byte
        data[tamperIndex] = originalByte ^ 0xFF;

        // Write back
        fs.writeFileSync(filePath, data);

        console.log(`✅ Tampered successfully!`);
        console.log(`   Position: byte ${tamperIndex}`);
        console.log(`   Changed: 0x${originalByte.toString(16).padStart(2, '0')} → 0x${data[tamperIndex].toString(16).padStart(2, '0')}`);
        console.log(`   File: ${filePath}`);

        console.log('\n🔍 Run verification to see the tamper detection:');
        console.log('   npm run verify');
        console.log('   or check the dashboard for real-time detection');

    } catch (error) {
        console.error('❌ Tamper failed:', error.message);
        process.exit(1);
    }
}

if (require.main === module) {
    tamperRandomFrame();
}

module.exports = { tamperRandomFrame };