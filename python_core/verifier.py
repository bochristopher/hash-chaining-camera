#!/usr/bin/env python3
"""
Provenance Verifier - Chain Integrity Verification
Verifies cryptographic integrity of the hash chain
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

from lib.crypto import ProvenanceCrypto
from lib.chain import ProvenanceChain, ChainEntry


class VerificationResult:
    """Container for verification results"""

    def __init__(self):
        self.total_entries = 0
        self.verified_entries = 0
        self.failed_entries = 0
        self.failures = []
        self.start_time = datetime.utcnow()
        self.end_time = None

    def add_failure(self, entry_index: int, reason: str, details: str = ""):
        """Record a verification failure"""
        self.failed_entries += 1
        self.failures.append({
            "entry_index": entry_index,
            "reason": reason,
            "details": details
        })

    def finalize(self):
        """Finalize verification"""
        self.end_time = datetime.utcnow()

    def is_valid(self) -> bool:
        """Check if chain is valid"""
        return self.failed_entries == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "valid": self.is_valid(),
            "total_entries": self.total_entries,
            "verified_entries": self.verified_entries,
            "failed_entries": self.failed_entries,
            "failures": self.failures,
            "verification_time": str(self.end_time - self.start_time) if self.end_time else None
        }


class ProvenanceVerifier:
    """
    Verifies the cryptographic integrity of the provenance chain
    """

    def __init__(self, data_dir: Path, keys_dir: Path):
        """
        Initialize verifier

        Args:
            data_dir: Data directory containing chain database
            keys_dir: Keys directory with public key
        """
        self.data_dir = Path(data_dir)
        self.keys_dir = Path(keys_dir)

        # Initialize components
        self.crypto = ProvenanceCrypto(self.keys_dir)
        self.chain = ProvenanceChain(self.data_dir / "chain.db")

    def verify_entry(self, entry: ChainEntry) -> Tuple[bool, str]:
        """
        Verify a single chain entry

        Args:
            entry: ChainEntry to verify

        Returns:
            Tuple of (is_valid, error_message)
        """
        entry_dict = entry.to_dict()

        # 1. Verify frame file exists
        frame_path = Path(entry.frame_path)
        if not frame_path.exists():
            return False, f"Frame file not found: {frame_path}"

        # 2. Verify frame hash
        actual_frame_hash = self.crypto.hash_file(frame_path)
        if actual_frame_hash != entry.frame_hash:
            return False, f"Frame hash mismatch: expected {entry.frame_hash[:16]}..., got {actual_frame_hash[:16]}..."

        # 3. Verify entry signature
        if not self.crypto.verify_entry_signature(entry_dict):
            return False, "Invalid Ed25519 signature"

        # 4. Verify entry hash
        if not self.crypto.verify_entry_hash(entry_dict):
            return False, "Invalid entry hash"

        return True, ""

    def verify_chain_linkage(self, entries: List[ChainEntry]) -> VerificationResult:
        """
        Verify hash chain linkage

        Args:
            entries: List of chain entries in order

        Returns:
            VerificationResult
        """
        result = VerificationResult()

        if not entries:
            return result

        # Check genesis entry
        if entries[0].previous_hash != "":
            result.add_failure(
                0,
                "Invalid genesis entry",
                f"Genesis previous_hash should be empty, got: {entries[0].previous_hash}"
            )

        # Check linkage
        for i in range(1, len(entries)):
            prev_entry = entries[i - 1]
            curr_entry = entries[i]

            if curr_entry.previous_hash != prev_entry.entry_hash:
                result.add_failure(
                    curr_entry.index,
                    "Broken chain linkage",
                    f"Expected previous_hash {prev_entry.entry_hash[:16]}..., got {curr_entry.previous_hash[:16]}..."
                )

        return result

    def verify_full_chain(self, verbose: bool = True) -> VerificationResult:
        """
        Verify entire chain

        Args:
            verbose: Print progress to console

        Returns:
            VerificationResult
        """
        result = VerificationResult()

        # Load public key
        try:
            self.crypto.load_verify_key()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)

        # Get all entries
        entries = self.chain.get_all_entries()
        result.total_entries = len(entries)

        if verbose:
            print("Provenance Chain Verification")
            print("=" * 60)
            print(f"Total entries: {result.total_entries}")
            print()

        # Verify each entry
        for entry in entries:
            is_valid, error_msg = self.verify_entry(entry)

            if is_valid:
                result.verified_entries += 1
                if verbose:
                    print(f"Entry #{entry.index:04d} - OK - {entry.timestamp}")
            else:
                result.add_failure(entry.index, "Entry verification failed", error_msg)
                if verbose:
                    print(f"Entry #{entry.index:04d} - FAIL - {error_msg}")

        # Verify chain linkage
        linkage_result = self.verify_chain_linkage(entries)
        result.failures.extend(linkage_result.failures)
        result.failed_entries += linkage_result.failed_entries

        result.finalize()

        if verbose:
            print()
            print("=" * 60)
            if result.is_valid():
                print("VERIFICATION PASSED")
                print(f"All {result.verified_entries} entries verified successfully")
            else:
                print("VERIFICATION FAILED")
                print(f"Failed: {result.failed_entries}/{result.total_entries} entries")
                print()
                print("Failures:")
                for failure in result.failures:
                    print(f"  Entry #{failure['entry_index']}: {failure['reason']}")
                    if failure['details']:
                        print(f"    {failure['details']}")

        return result

    def export_verification_report(self, output_path: Path) -> None:
        """
        Export verification report to JSON

        Args:
            output_path: Output file path
        """
        result = self.verify_full_chain(verbose=False)

        report = {
            "verification_timestamp": datetime.utcnow().isoformat() + "Z",
            "data_directory": str(self.data_dir),
            "result": result.to_dict()
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Verification report exported to: {output_path}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Provenance Chain Verifier"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("/data"),
        help="Data directory containing chain database"
    )
    parser.add_argument(
        "--keys",
        type=Path,
        default=Path("/keys"),
        help="Keys directory with public key"
    )
    parser.add_argument(
        "--export",
        type=Path,
        help="Export verification report to JSON file"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    verifier = ProvenanceVerifier(
        data_dir=args.data,
        keys_dir=args.keys
    )

    # Export mode
    if args.export:
        verifier.export_verification_report(args.export)
        sys.exit(0)

    # Normal verification
    result = verifier.verify_full_chain(verbose=not args.quiet)

    # JSON output
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))

    # Exit code
    sys.exit(0 if result.is_valid() else 1)


if __name__ == "__main__":
    main()
