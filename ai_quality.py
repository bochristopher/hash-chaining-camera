#!/usr/bin/env python3
"""
Optional AI quality assessment module for hash-chaining camera
This is a placeholder for future AI-powered frame quality analysis
"""

import sys
import json
from pathlib import Path

def assess_frame_quality(frame_path):
    """
    Assess the quality of a captured frame
    Returns a quality score and analysis
    """

    frame_file = Path(frame_path)

    if not frame_file.exists():
        return {
            "error": f"Frame file not found: {frame_path}",
            "quality_score": 0
        }

    # Get basic file statistics
    file_size = frame_file.stat().st_size

    # Simple quality heuristics based on file size
    # (In a real implementation, this would use computer vision)
    if file_size < 50000:  # Less than 50KB
        quality = "low"
        score = 0.3
        reason = "File size too small, possibly corrupted or low quality"
    elif file_size > 5000000:  # Greater than 5MB
        quality = "high"
        score = 0.9
        reason = "Large file size indicates high resolution/quality"
    else:
        quality = "medium"
        score = 0.6 + (file_size / 10000000) * 0.3  # Scale based on size
        reason = "Medium file size indicates acceptable quality"

    return {
        "frame_path": str(frame_path),
        "file_size_bytes": file_size,
        "quality_score": round(score, 2),
        "quality_level": quality,
        "analysis": reason,
        "timestamp": frame_file.stat().st_mtime,
        "recommendations": get_recommendations(score)
    }

def get_recommendations(score):
    """Get improvement recommendations based on quality score"""
    if score < 0.4:
        return [
            "Check camera lens for dirt or obstruction",
            "Verify adequate lighting conditions",
            "Check GStreamer pipeline configuration",
            "Consider increasing JPEG quality setting"
        ]
    elif score < 0.7:
        return [
            "Consider increasing capture resolution",
            "Check for optimal lighting conditions",
            "Fine-tune JPEG quality vs file size balance"
        ]
    else:
        return [
            "Quality appears good",
            "Monitor for consistency across captures"
        ]

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 ai_quality.py <frame_path>", file=sys.stderr)
        sys.exit(1)

    frame_path = sys.argv[1]
    result = assess_frame_quality(frame_path)

    # Output JSON for programmatic use
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            sys.exit(1)

        print(f"🖼️  Frame Quality Assessment")
        print(f"   File: {result['frame_path']}")
        print(f"   Size: {result['file_size_bytes']:,} bytes")
        print(f"   Quality Score: {result['quality_score']}/1.0 ({result['quality_level']})")
        print(f"   Analysis: {result['analysis']}")

        if result['recommendations']:
            print(f"   Recommendations:")
            for rec in result['recommendations']:
                print(f"   • {rec}")

if __name__ == "__main__":
    main()