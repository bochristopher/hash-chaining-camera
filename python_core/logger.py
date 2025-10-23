#!/usr/bin/env python3
"""
Provenance Logger - Main Entry Point
Captures camera frames, sensor data, and builds cryptographic hash chain
"""

import sys
import time
import signal
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from lib.camera import JetsonCamera
from lib.crypto import ProvenanceCrypto
from lib.chain import ProvenanceChain
from lib.sensors import SensorManager


class ProvenanceLogger:
    """
    Main logger application
    Captures frames with sensor context and builds tamper-evident chain
    """

    def __init__(self, config_path: Path, data_dir: Path, keys_dir: Path):
        """
        Initialize logger

        Args:
            config_path: Path to YAML configuration
            data_dir: Data output directory
            keys_dir: Cryptographic keys directory
        """
        self.config_path = Path(config_path)
        self.data_dir = Path(data_dir)
        self.keys_dir = Path(keys_dir)

        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Initialize components
        self.camera = JetsonCamera(self.config.get("camera", {}))
        self.crypto = ProvenanceCrypto(self.keys_dir)
        self.chain = ProvenanceChain(self.data_dir / "chain.db")
        self.sensors = SensorManager(self.config.get("sensors", {}))

        # State
        self.running = False
        self.capture_count = 0

        # Output paths
        self.frames_dir = self.data_dir / "frames"
        self.frames_dir.mkdir(exist_ok=True)

    def setup(self) -> bool:
        """
        Setup logger (keys, camera test, etc.)

        Returns:
            True if setup successful
        """
        print("Provenance Logger - Setup")
        print("=" * 60)

        # Check or generate keys
        if not self.crypto.private_key_path.exists():
            print("No keypair found, generating new Ed25519 keys...")
            self.crypto.generate_keypair()
        else:
            print(f"Using existing keypair: {self.keys_dir}")

        # Load signing key
        try:
            self.crypto.load_signing_key()
            print("Loaded signing key")
        except Exception as e:
            print(f"Failed to load signing key: {e}")
            return False

        # Test camera
        print(f"\nTesting {self.camera.camera_type} camera...")
        if not self.camera.test_camera():
            print("Camera test failed - check configuration")
            return False

        # Connect sensors
        print("\nConnecting to sensors...")
        self.sensors.connect_all()

        print("\nSetup complete!")
        print("=" * 60)
        return True

    def capture_and_log(self) -> bool:
        """
        Capture frame and create chain entry

        Returns:
            True if successful
        """
        # Capture frame
        frame_path = self.camera.capture_frame(self.frames_dir)
        if not frame_path:
            print("Frame capture failed")
            return False

        # Calculate frame hash
        frame_hash = self.crypto.hash_file(frame_path)

        # Get previous chain entry
        latest = self.chain.get_latest_entry()
        if latest:
            index = latest.index + 1
            previous_hash = latest.entry_hash
        else:
            # Genesis entry
            index = 0
            previous_hash = ""

        # Read sensor data
        sensor_data = self.sensors.read_all()

        # Create timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Build metadata
        metadata = {
            "frame_filename": frame_path.name,
            "camera": self.camera.get_device_info(),
            "sensors": sensor_data
        }

        # Create chain entry
        entry = self.crypto.create_chain_entry(
            index=index,
            timestamp=timestamp,
            frame_hash=frame_hash,
            previous_hash=previous_hash,
            metadata=metadata
        )

        # Store in database
        self.chain.add_entry(
            index=entry["index"],
            timestamp=entry["timestamp"],
            frame_path=frame_path,
            frame_hash=entry["frame_hash"],
            previous_hash=entry["previous_hash"],
            entry_hash=entry["entry_hash"],
            signature=entry["signature"],
            metadata=metadata
        )

        self.capture_count += 1
        print(f"[{timestamp}] Entry #{index} - {frame_path.name} - {frame_hash[:16]}...")

        return True

    def run(self) -> None:
        """
        Main logging loop
        """
        # Setup
        if not self.setup():
            print("Setup failed, exiting")
            sys.exit(1)

        # Get capture interval
        interval_ms = self.config.get("capture_interval_ms", 2000)
        interval_sec = interval_ms / 1000.0

        print(f"\nStarting capture loop (interval: {interval_sec}s)")
        print("Press Ctrl+C to stop\n")

        self.running = True

        # Signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print("\n\nShutdown requested...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Main loop
        try:
            while self.running:
                try:
                    self.capture_and_log()
                except Exception as e:
                    print(f"Capture error: {e}")

                # Wait for next interval
                time.sleep(interval_sec)

        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """
        Clean shutdown
        """
        print("\nShutting down...")
        self.sensors.disconnect_all()

        # Export chain to JSON
        export_path = self.data_dir / "chain_export.json"
        self.chain.export_to_json(export_path)

        print(f"Total captures: {self.capture_count}")
        print(f"Chain length: {self.chain.get_chain_length()}")
        print(f"Chain exported to: {export_path}")
        print("Goodbye!")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Provenance Logger for Jetson Orin Nano"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/config/config.yaml"),
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("/data"),
        help="Data output directory"
    )
    parser.add_argument(
        "--keys",
        type=Path,
        default=Path("/keys"),
        help="Keys directory"
    )
    parser.add_argument(
        "--generate-keys",
        action="store_true",
        help="Generate new keypair and exit"
    )

    args = parser.parse_args()

    # Generate keys mode
    if args.generate_keys:
        print("Generating new Ed25519 keypair...")
        crypto = ProvenanceCrypto(args.keys)
        crypto.generate_keypair()
        sys.exit(0)

    # Normal logging mode
    logger = ProvenanceLogger(
        config_path=args.config,
        data_dir=args.data,
        keys_dir=args.keys
    )

    logger.run()


if __name__ == "__main__":
    main()
