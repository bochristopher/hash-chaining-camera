#!/usr/bin/env python3
"""
Flask API Server for Provenance Verification
Exposes chain data and verification results via HTTP
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.crypto import ProvenanceCrypto
from lib.chain import ProvenanceChain
from verifier import ProvenanceVerifier


def create_app(data_dir: Path, keys_dir: Path) -> Flask:
    """
    Create Flask application

    Args:
        data_dir: Data directory
        keys_dir: Keys directory

    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    CORS(app)  # Enable CORS for web dashboard

    # Initialize components
    chain = ProvenanceChain(data_dir / "chain.db")
    verifier = ProvenanceVerifier(data_dir, keys_dir)

    @app.route("/")
    def index():
        """API index"""
        return jsonify({
            "service": "Provenance Logger API",
            "version": "1.0.0",
            "endpoints": [
                "/api/status",
                "/api/chain",
                "/api/chain/<int:index>",
                "/api/verify",
                "/api/latest-frame"
            ]
        })

    @app.route("/api/status")
    def status():
        """Get system status"""
        chain_length = chain.get_chain_length()
        latest = chain.get_latest_entry()

        return jsonify({
            "status": "online",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "chain_length": chain_length,
            "latest_entry": {
                "index": latest.index,
                "timestamp": latest.timestamp,
                "entry_hash": latest.entry_hash
            } if latest else None
        })

    @app.route("/api/chain")
    def get_chain():
        """Get full chain"""
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int, default=0)

        entries = chain.get_all_entries()

        # Apply pagination
        if limit:
            entries = entries[offset:offset + limit]

        chain_data = [entry.to_dict() for entry in entries]

        return jsonify({
            "total": chain.get_chain_length(),
            "offset": offset,
            "limit": limit,
            "entries": chain_data
        })

    @app.route("/api/chain/<int:index>")
    def get_entry(index: int):
        """Get specific chain entry"""
        entry = chain.get_entry_by_index(index)

        if not entry:
            return jsonify({"error": "Entry not found"}), 404

        return jsonify(entry.to_dict())

    @app.route("/api/verify")
    def verify_chain():
        """Verify chain integrity"""
        result = verifier.verify_full_chain(verbose=False)

        return jsonify(result.to_dict())

    @app.route("/api/latest-frame")
    def latest_frame():
        """Get latest frame image"""
        latest = chain.get_latest_entry()

        if not latest:
            return jsonify({"error": "No frames captured yet"}), 404

        frame_path = Path(latest.frame_path)

        if not frame_path.exists():
            return jsonify({"error": "Frame file not found"}), 404

        return send_file(
            frame_path,
            mimetype="image/jpeg"
        )

    @app.route("/api/frame/<int:index>")
    def get_frame(index: int):
        """Get frame by chain index"""
        entry = chain.get_entry_by_index(index)

        if not entry:
            return jsonify({"error": "Entry not found"}), 404

        frame_path = Path(entry.frame_path)

        if not frame_path.exists():
            return jsonify({"error": "Frame file not found"}), 404

        return send_file(
            frame_path,
            mimetype="image/jpeg"
        )

    return app


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Provenance Logger API Server"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("/data"),
        help="Data directory"
    )
    parser.add_argument(
        "--keys",
        type=Path,
        default=Path("/keys"),
        help="Keys directory"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind to"
    )

    args = parser.parse_args()

    print("Starting Provenance Logger API Server")
    print(f"Data directory: {args.data}")
    print(f"Listening on http://{args.host}:{args.port}")

    app = create_app(args.data, args.keys)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
