"""
stream_manager.py — Video Stream Manager for RTSP and File Sources
"""
import os
import cv2
import time
import threading
import logging

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages video capture from RTSP streams, local files, or webcams."""

    def __init__(self):
        self.cap = None
        self.is_running = False
        self.source_type = None  # "rtsp", "file", or "webcam"
        self.source_url = None
        self.lock = threading.Lock()
        
        # Zero-buffer components
        self.latest_frame = None
        self.update_thread = None
        self._stop_thread = threading.Event()

    def _update_loop(self):
        """Continuously grab frames in the background with error handling and auto-reconnect."""
        retry_count = 0
        max_retries = 5
        
        while not self._stop_thread.is_set():
            if self.cap is not None and self.is_running:
                try:
                    ret, frame = self.cap.read()
                    if ret:
                        with self.lock:
                            self.latest_frame = frame
                        retry_count = 0  # Reset on success
                    else:
                        logger.warning("Stream read failed (empty frame)")
                        if self.source_type == "rtsp":
                            self._handle_reconnect()
                        time.sleep(0.1)
                except Exception as e:
                    logger.error(f"OpenCV Error in update loop: {e}")
                    if self.source_type == "rtsp":
                        self._handle_reconnect()
                    time.sleep(0.5)
            else:
                time.sleep(0.1)

    def _handle_reconnect(self):
        """Attempt to reconnect to the RTSP source if it fails."""
        if self.source_type != "rtsp" or not self.source_url:
            return
            
        logger.info(f"Attempting to reconnect to RTSP: {self.source_url}...")
        if self.cap:
            self.cap.release()
            
        # Use simple reconn for now (will reuse existing open_rtsp logic if it was easier but we are inside thread)
        # To avoid complex recursion, we just try to recreate the capture here
        cap = self._create_rtsp_capture(self.source_url, "tcp") # Default to TCP
        if cap and cap.isOpened():
            with self.lock:
                self.cap = cap
                logger.info("Reconnection successful!")
        else:
            logger.error("Reconnection failed.")

    def _start_thread(self):
        """Start the background grabbing thread."""
        self._stop_thread.clear()
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def _stop_thread_internal(self):
        """Signal and stop the background thread."""
        self._stop_thread.set()
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
            self.update_thread = None

    def _create_rtsp_capture(self, url: str, transport: str = "tcp"):
        """Create RTSP capture with specified transport."""
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            f"rtsp_transport;{transport}"
            "|analyzeduration;1000000"
            "|probesize;500000"
            "|fflags;nobuffer"
            "|flags;low_delay"
            "|stimeout;15000000"
        )
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if cap.isOpened():
            # Minimal buffer for live streams
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap
        return None

    def open_rtsp(self, url: str) -> dict:
        """Open RTSP stream with TCP/UDP fallback."""
        self.stop()

        for transport in ["tcp", "udp"]:
            logger.info(f"Trying RTSP with {transport.upper()}...")
            cap = self._create_rtsp_capture(url, transport)
            if cap is not None and cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    with self.lock:
                        self.cap = cap
                        self.source_type = "rtsp"
                        self.source_url = url
                        self.is_running = True
                        self.latest_frame = None
                    self._start_thread()
                    return {"success": True, "transport": transport.upper()}
                cap.release()

        return {"success": False, "error": "Failed to connect — check URL, credentials, and VPN"}

    def open_file(self, file_path: str) -> dict:
        """Open a local video file."""
        self.stop()

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return {"success": False, "error": "Failed to open video file"}

        with self.lock:
            self.cap = cap
            self.source_type = "file"
            self.source_url = file_path
            self.is_running = True
            self.latest_frame = None
        
        # Files don't necessarily need the thread, but for consistency:
        self._start_thread()

        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        return {"success": True, "total_frames": total, "fps": fps}

    def open_webcam(self, camera_index: int = 0) -> dict:
        """Open a local webcam/camera by index."""
        self.stop()

        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)

        if not cap.isOpened():
            return {"success": False, "error": f"Failed to open camera {camera_index}"}

        # Set reasonable resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ret, _ = cap.read()
        if not ret:
            cap.release()
            return {"success": False, "error": f"Camera {camera_index} opened but no frames"}

        with self.lock:
            self.cap = cap
            self.source_type = "webcam"
            self.source_url = str(camera_index)
            self.is_running = True
            self.latest_frame = None
        
        self._start_thread()

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        return {"success": True, "camera_index": camera_index, "width": w, "height": h, "fps": fps}

    @staticmethod
    def scan_cameras(max_count: int = 5) -> list:
        """Scan for available local cameras. Returns list of {index, name, width, height}."""
        cameras = []
        for i in range(max_count):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cameras.append({
                        "index": i,
                        "name": f"Camera {i}",
                        "width": w,
                        "height": h
                    })
                cap.release()
        return cameras

    def read_frame(self):
        """Read the latest frame from the background thread."""
        with self.lock:
            if not self.is_running or self.latest_frame is None:
                return False, None
            
            frame = self.latest_frame.copy()
            # If it's a file, we might want to keep frames to show everything,
            # but for Live RTSP, we want to clear it so we don't process the same frame twice
            # if processing is faster than the stream. 
            # Actually, for RTSP, latest_frame will be overwritten anyway.
            return True, frame

    def stop(self):
        """Stop and release the capture and background thread."""
        self._stop_thread_internal()
        with self.lock:
            self.is_running = False
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            self.latest_frame = None

    def get_info(self) -> dict:
        """Get stream info."""
        with self.lock:
            if self.cap is None:
                return {"active": False}
            return {
                "active": self.is_running,
                "type": self.source_type,
                "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": self.cap.get(cv2.CAP_PROP_FPS),
                "total_frames": int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) if self.source_type == "file" else None
            }

    @staticmethod
    def test_rtsp(url: str) -> dict:
        """Test RTSP connection without keeping it open."""
        for transport in ["tcp", "udp"]:
            try:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                    f"rtsp_transport;{transport}"
                    "|analyzeduration;2000000"
                    "|stimeout;10000000"
                )
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                if cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        return {"success": True, "transport": transport.upper()}
            except Exception:
                continue

        return {"success": False, "error": "Connection failed — check URL, credentials, and VPN"}
