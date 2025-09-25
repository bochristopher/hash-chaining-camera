const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function generateKeys() {
    const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519', {
        publicKeyEncoding: {
            type: 'spki',
            format: 'pem'
        },
        privateKeyEncoding: {
            type: 'pkcs8',
            format: 'pem'
        }
    });

    const keysDir = path.join(__dirname, 'keys');
    if (!fs.existsSync(keysDir)) {
        fs.mkdirSync(keysDir);
    }

    fs.writeFileSync(path.join(keysDir, 'private_key.pem'), privateKey);
    fs.writeFileSync(path.join(keysDir, 'public_key.pem'), publicKey);

    console.log('Ed25519 keypair generated successfully!');
    console.log('Private key saved to keys/private_key.pem');
    console.log('Public key saved to keys/public_key.pem');
}

if (require.main === module) {
    generateKeys();
}

module.exports = { generateKeys };