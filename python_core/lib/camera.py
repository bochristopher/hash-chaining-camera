"""
Camera capture using GStreamer on Jetson Orin Nano
Supports CSI (MIPI) and USB cameras with hardware acceleration
"""

import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class JetsonCamera:
    """
    GStreamer-based camera capture for Jetson Orin Nano
    Supports hardware-accelerated JPEG encoding
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize camera

        Args:
            config: Camera configuration dictionary
        """
        self.camera_type = config.get("camera", "USB")
        self.usb_device = config.get("usb_device", "/dev/video0")
        self.width = config.get("width", 1920)
        self.height = config.get("height", 1080)
        self.framerate = config.get("framerate", 30)
        self.jpeg_quality = config.get("jpeg_quality", 85)

    def build_csi_pipeline(self, output_path: Path) -> list:
        """
        Build GStreamer pipeline for CSI (MIPI) camera

        Args:
            output_path: Output JPEG file path

        Returns:
            Command list for subprocess
        """
        return [
            "gst-launch-1.0", "-e",
            "nvarguscamerasrc", "num-buffers=1", "!",
            f"video/x-raw(memory:NVMM),width={self.width},height={self.height},"
            f"format=NV12,framerate={self.framerate}/1", "!",
            "nvjpegenc", f"quality={self.jpeg_quality}", "!",
            "filesink", f"location={output_path}"
        ]

    def build_usb_mjpeg_pipeline(self, output_path: Path) -> list:
        """
        Build GStreamer pipeline for USB camera (MJPEG fast path)

        Args:
            output_path: Output JPEG file path

        Returns:
            Command list for subprocess
        """
        return [
            "gst-launch-1.0", "-e",
            "v4l2src", f"device={self.usb_device}", "num-buffers=1", "!",
            f"image/jpeg,width={self.width},height={self.height},"
            f"framerate={self.framerate}/1", "!",
            "jpegparse", "!",
            "filesink", f"location={output_path}"
        ]

    def build_usb_raw_pipeline(self, output_path: Path) -> list:
        """
        Build GStreamer pipeline for USB camera (raw conversion)

        Args:
            output_path: Output JPEG file path

        Returns:
            Command list for subprocess
        """
        return [
            "gst-launch-1.0", "-e",
            "v4l2src", f"device={self.usb_device}", "num-buffers=1", "!",
            f"video/x-raw,format=YUY2,width={self.width},height={self.height},"
            f"framerate={self.framerate}/1", "!",
            "nvvidconv", "!",
            "nvjpegenc", f"quality={self.jpeg_quality}", "!",
            "filesink", f"location={output_path}"
        ]

    def capture_frame(self, output_dir: Path) -> Optional[Path]:
        """
        Capture a single frame from camera

        Args:
            output_dir: Directory to save captured frame

        Returns:
            Path to captured frame, or None on failure
        """
        # Generate timestamped filename
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"
        filename = f"frame_{timestamp}.jpg"
        output_path = output_dir / filename

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Select pipeline based on camera type
        if self.camera_type == "CSI":
            pipeline = self.build_csi_pipeline(output_path)
        else:
            # Try MJPEG first, fall back to raw
            pipeline = self.build_usb_mjpeg_pipeline(output_path)

        try:
            # Execute GStreamer pipeline
            result = subprocess.run(
                pipeline,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                # If MJPEG failed for USB, try raw pipeline
                if self.camera_type == "USB":
                    print(f"MJPEG capture failed, trying raw pipeline...")
                    pipeline = self.build_usb_raw_pipeline(output_path)
                    result = subprocess.run(
                        pipeline,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

            if result.returncode != 0:
                print(f"GStreamer error: {result.stderr}")
                return None

            # Verify file was created
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
            else:
                print(f"Frame file not created or empty: {output_path}")
                return None

        except subprocess.TimeoutExpired:
            print("Camera capture timeout")
            return None
        except Exception as e:
            print(f"Camera capture error: {e}")
            return None

    def test_camera(self) -> bool:
        """
        Test camera connectivity and capability

        Returns:
            True if camera is accessible
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir)
            result = self.capture_frame(test_path)
            if result:
                print(f"Camera test successful: {self.camera_type}")
                return True
            else:
                print(f"Camera test failed: {self.camera_type}")
                return False

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get camera device information

        Returns:
            Dictionary with device info
        """
        info = {
            "camera_type": self.camera_type,
            "width": self.width,
            "height": self.height,
            "framerate": self.framerate,
            "jpeg_quality": self.jpeg_quality
        }

        if self.camera_type == "USB":
            info["device"] = self.usb_device

        return info
