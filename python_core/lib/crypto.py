"""
Cryptographic utilities for provenance logging
Handles Ed25519 key generation, signing, and hash chaining
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder


class ProvenanceCrypto:
    """
    Handles Ed25519 digital signatures and SHA-256 hash chaining
    """

    def __init__(self, keys_dir: Path):
        """
        Initialize crypto handler

        Args:
            keys_dir: Directory containing private_key.pem and public_key.pem
        """
        self.keys_dir = Path(keys_dir)
        self.private_key_path = self.keys_dir / "private_key.pem"
        self.public_key_path = self.keys_dir / "public_key.pem"

        self.signing_key: Optional[SigningKey] = None
        self.verify_key: Optional[VerifyKey] = None

    def generate_keypair(self) -> Dict[str, str]:
        """
        Generate new Ed25519 keypair and save to files

        Returns:
            Dictionary with public and private key paths
        """
        # Generate new keypair
        signing_key = SigningKey.generate()
        verify_key = signing_key.verify_key

        # Ensure keys directory exists
        self.keys_dir.mkdir(parents=True, exist_ok=True)

        # Save private key
        with open(self.private_key_path, 'wb') as f:
            f.write(signing_key.encode(encoder=HexEncoder))

        # Save public key
        with open(self.public_key_path, 'wb') as f:
            f.write(verify_key.encode(encoder=HexEncoder))

        # Set restrictive permissions
        self.private_key_path.chmod(0o600)
        self.public_key_path.chmod(0o644)

        print(f"Generated Ed25519 keypair:")
        print(f"  Private: {self.private_key_path}")
        print(f"  Public:  {self.public_key_path}")

        return {
            "private_key": str(self.private_key_path),
            "public_key": str(self.public_key_path)
        }

    def load_signing_key(self) -> SigningKey:
        """
        Load private key for signing

        Returns:
            SigningKey instance

        Raises:
            FileNotFoundError: If private key doesn't exist
        """
        if not self.private_key_path.exists():
            raise FileNotFoundError(
                f"Private key not found: {self.private_key_path}\n"
                "Run with --generate-keys first"
            )

        with open(self.private_key_path, 'rb') as f:
            key_data = f.read()

        self.signing_key = SigningKey(key_data, encoder=HexEncoder)
        return self.signing_key

    def load_verify_key(self) -> VerifyKey:
        """
        Load public key for verification

        Returns:
            VerifyKey instance

        Raises:
            FileNotFoundError: If public key doesn't exist
        """
        if not self.public_key_path.exists():
            raise FileNotFoundError(
                f"Public key not found: {self.public_key_path}"
            )

        with open(self.public_key_path, 'rb') as f:
            key_data = f.read()

        self.verify_key = VerifyKey(key_data, encoder=HexEncoder)
        return self.verify_key

    @staticmethod
    def hash_file(file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file

        Args:
            file_path: Path to file

        Returns:
            Hex-encoded SHA-256 hash
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            # Read in chunks for large files
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    @staticmethod
    def hash_data(data: bytes) -> str:
        """
        Calculate SHA-256 hash of raw data

        Args:
            data: Raw bytes to hash

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(data).hexdigest()

    def create_chain_entry(
        self,
        index: int,
        timestamp: str,
        frame_hash: str,
        previous_hash: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new hash chain entry with digital signature

        Args:
            index: Chain index (0 for genesis)
            timestamp: ISO 8601 timestamp
            frame_hash: SHA-256 hash of the frame image
            previous_hash: Hash of previous chain entry (empty for genesis)
            metadata: Optional sensor/context data

        Returns:
            Complete chain entry with signature
        """
        if not self.signing_key:
            self.load_signing_key()

        # Build entry structure
        entry = {
            "index": index,
            "timestamp": timestamp,
            "frame_hash": frame_hash,
            "previous_hash": previous_hash,
            "metadata": metadata or {}
        }

        # Create canonical string for signing
        canonical = json.dumps(entry, sort_keys=True, separators=(',', ':'))

        # Sign the entry
        signed = self.signing_key.sign(canonical.encode('utf-8'))
        signature_hex = signed.signature.hex()

        # Calculate entry hash (includes signature)
        entry_with_sig = canonical + signature_hex
        entry_hash = self.hash_data(entry_with_sig.encode('utf-8'))

        # Complete entry
        entry["signature"] = signature_hex
        entry["entry_hash"] = entry_hash

        return entry

    def verify_entry_signature(self, entry: Dict[str, Any]) -> bool:
        """
        Verify Ed25519 signature of a chain entry

        Args:
            entry: Chain entry dictionary

        Returns:
            True if signature is valid
        """
        if not self.verify_key:
            self.load_verify_key()

        # Extract signature
        signature_hex = entry.get("signature")
        if not signature_hex:
            return False

        # Recreate canonical entry (without signature and entry_hash)
        entry_copy = {k: v for k, v in entry.items()
                      if k not in ["signature", "entry_hash"]}
        canonical = json.dumps(entry_copy, sort_keys=True, separators=(',', ':'))

        try:
            signature_bytes = bytes.fromhex(signature_hex)
            self.verify_key.verify(canonical.encode('utf-8'), signature_bytes)
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False

    def verify_entry_hash(self, entry: Dict[str, Any]) -> bool:
        """
        Verify the entry hash is correct

        Args:
            entry: Chain entry dictionary

        Returns:
            True if entry hash is valid
        """
        stored_hash = entry.get("entry_hash")
        if not stored_hash:
            return False

        # Recreate canonical entry + signature
        entry_copy = {k: v for k, v in entry.items()
                      if k not in ["entry_hash"]}
        canonical = json.dumps({k: v for k, v in entry_copy.items()
                                if k != "signature"},
                               sort_keys=True, separators=(',', ':'))
        signature_hex = entry_copy.get("signature", "")
        entry_with_sig = canonical + signature_hex

        computed_hash = self.hash_data(entry_with_sig.encode('utf-8'))

        return computed_hash == stored_hash
