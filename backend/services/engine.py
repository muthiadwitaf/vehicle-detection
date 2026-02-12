"""
engine.py — High-Performance Detection Engine (Singleton)

Pipeline:
  StreamManager (grab thread) → latest_raw_frame
      ↓
  _process_loop (detection thread):
      1. Read frame (skip if already processed)
      2. YOLO inference (adaptive FPS)
      3. Tracker update
      4. Annotate + JPEG encode at reduced resolution
      5. Store in latest_broadcast_data
      ↓
  broadcast_loop (async, main.py):
      Read latest_broadcast_data → send to all WS clients
"""
import time
import cv2
import base64
import threading
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from stream_manager import StreamManager
from detection import load_model, detect_vehicles, draw_boxes
from tracker import VehicleTracker
from database import save_counts, load_counts
from core.config import settings

logger = logging.getLogger(__name__)


class DetectionEngine:
    """
    Singleton engine with adaptive frame rate and decoupled encode.
    - Inference runs at adaptive FPS (backs off under load)
    - Frame encode runs at reduced resolution
    - Metadata (counts/timeline) separated from frame payload
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.stream_mgr = StreamManager()
        self.tracker = None
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()

        # State
        self.stats = {
            "counts": {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0},
            "seen_ids": set(),
            "timeline": [],
            "frame_count": 0,
            "source_type": None,
            "tracking_enabled": True,
            "model_precision": settings.DEFAULT_PRECISION,
            "current_camera_id": None,
            "current_camera_name": None
        }

        # Broadcast data — read by main.py broadcast_loop
        self.latest_broadcast_data = None
        self._broadcast_lock = threading.Lock()
        self._broadcast_seq = 0  # Sequence number for frame/meta separation

        # Performance metrics
        self.actual_fps = 0.0
        self.infer_time_ms = 0.0

        self._initialized = True

        # Pre-load model
        try:
            load_model(self.stats["model_precision"])
        except Exception as e:
            logger.error(f"Failed to load initial model: {e}")

    # ── Lifecycle ──────────────────────────────────────

    def start_processing(self):
        if self.is_running:
            return
        self.is_running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        logger.info("Detection Engine started.")

    def stop_processing(self):
        self.is_running = False
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3.0)
        self.stream_mgr.stop()

        # Save final counts
        if self.stats.get("current_camera_id"):
            save_counts(
                self.stats["current_camera_id"],
                self.stats.get("current_camera_name", ""),
                self.stats["counts"]
            )
        logger.info("Detection Engine stopped.")

    # ── Main Processing Loop ───────────────────────────

    def _process_loop(self):
        """Adaptive-FPS detection loop with frame skipping."""
        target_interval = 1.0 / settings.INFER_FPS
        resize_w = settings.FRAME_RESIZE_WIDTH
        jpeg_quality = settings.JPEG_QUALITY
        db_interval = settings.DB_SAVE_INTERVAL
        meta_every = settings.META_EVERY_N

        if self.tracker is None:
            self.tracker = VehicleTracker()

        fps_counter = 0
        fps_timer = time.time()
        last_frame_id = None

        while not self.stop_event.is_set():
            loop_start = time.time()

            if not self.stream_mgr.is_running:
                time.sleep(0.05)
                continue

            # ── 1. Read Frame ──
            ret, frame = self.stream_mgr.read_frame()
            if not ret or frame is None:
                if self.stats["source_type"] == "file":
                    self._handle_file_end()
                    time.sleep(0.5)
                else:
                    time.sleep(0.01)
                continue

            # Frame skip: don't re-process the exact same frame object
            frame_id = id(frame)
            if frame_id == last_frame_id:
                time.sleep(0.005)
                continue
            last_frame_id = frame_id

            self.stats["frame_count"] += 1

            # ── 2. Inference ──
            infer_start = time.time()
            detections = detect_vehicles(
                frame,
                confidence=settings.CONF_THRESHOLD,
                track=self.stats["tracking_enabled"]
            )
            self.infer_time_ms = (time.time() - infer_start) * 1000

            # ── 3. Tracking ──
            tracking_data = []
            tracking_stats = {}
            if self.stats["tracking_enabled"]:
                tracking_data = self.tracker.update(detections)
                tracking_stats = self.tracker.get_statistics()
                self._update_counts(detections)
            else:
                for det in detections:
                    cls = det["class_name"]
                    self.stats["counts"][cls] = self.stats["counts"].get(cls, 0) + 1

            # ── 4. Timeline ──
            frame_vehicles = len(detections)
            self.stats["timeline"].append(frame_vehicles)
            if len(self.stats["timeline"]) > 100:
                self.stats["timeline"].pop(0)

            # ── 5. DB auto-save ──
            if self.stats["current_camera_id"] and self.stats["frame_count"] % db_interval == 0:
                save_counts(
                    self.stats["current_camera_id"],
                    self.stats.get("current_camera_name", ""),
                    self.stats["counts"]
                )

            # ── 6. Annotate + Encode ──
            annotated = draw_boxes(frame, detections, tracking_data, show_timestamp=True)

            # Resize for bandwidth
            h, w = annotated.shape[:2]
            if w > resize_w:
                scale = resize_w / w
                new_h = int(h * scale)
                annotated = cv2.resize(annotated, (resize_w, new_h), interpolation=cv2.INTER_AREA)

            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
            frame_b64 = base64.b64encode(buffer).decode('utf-8')

            # ── 7. Build Broadcast Payload ──
            self._broadcast_seq += 1

            payload = {
                "frame": frame_b64,
                "is_running": True,
                "seq": self._broadcast_seq,
            }

            # Include metadata every Nth frame (saves bandwidth)
            if self._broadcast_seq % meta_every == 0:
                payload["counts"] = self.stats["counts"]
                payload["timeline"] = self.stats["timeline"]
                payload["frame_count"] = self.stats["frame_count"]
                payload["total_detected"] = sum(self.stats["counts"].values())
                payload["tracking_stats"] = tracking_stats
                payload["source_type"] = self.stats["source_type"]
                payload["perf"] = {
                    "fps": round(self.actual_fps, 1),
                    "infer_ms": round(self.infer_time_ms, 1),
                }

            with self._broadcast_lock:
                self.latest_broadcast_data = payload

            # ── 8. FPS calculation ──
            fps_counter += 1
            now = time.time()
            if now - fps_timer >= 1.0:
                self.actual_fps = fps_counter / (now - fps_timer)
                fps_counter = 0
                fps_timer = now

            # ── 9. Adaptive throttle ──
            elapsed = time.time() - loop_start
            wait = target_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            else:
                # Under load: dynamically back off
                # Log if consistently over budget
                if elapsed > target_interval * 1.5:
                    logger.debug(f"Frame over budget: {elapsed*1000:.0f}ms (target {target_interval*1000:.0f}ms)")

    def get_broadcast_data(self):
        """Thread-safe read of latest broadcast payload."""
        with self._broadcast_lock:
            data = self.latest_broadcast_data
            self.latest_broadcast_data = None  # Consume it
            return data

    # ── Helpers ─────────────────────────────────────────

    def _update_counts(self, detections):
        for det in detections:
            cls = det["class_name"]
            track_id = det.get("track_id")
            if track_id is not None and track_id not in self.stats["seen_ids"]:
                self.stats["seen_ids"].add(track_id)
                self.stats["counts"][cls] = self.stats["counts"].get(cls, 0) + 1

    def _handle_file_end(self):
        self.is_running = False
        with self._broadcast_lock:
            self.latest_broadcast_data = {
                "status": "complete",
                "counts": self.stats["counts"],
                "total_detected": sum(self.stats["counts"].values())
            }
        self.stream_mgr.stop()

    # ── Source Control ──────────────────────────────────

    def set_source_file(self, path):
        self.stop_processing()
        res = self.stream_mgr.open_file(path)
        if res["success"]:
            self._reset_stats()
            self.stats["source_type"] = "file"
            self.start_processing()
        return res

    def set_source_rtsp(self, url, camera_id=None, camera_name=None):
        self.stop_processing()
        res = self.stream_mgr.open_rtsp(url)
        if res["success"]:
            self._reset_stats()
            if camera_id:
                saved = load_counts(camera_id)
                if saved:
                    self.stats["counts"] = saved
            self.stats["source_type"] = "rtsp"
            self.stats["current_camera_id"] = camera_id
            self.stats["current_camera_name"] = camera_name
            self.start_processing()
        return res

    def set_source_webcam(self, index):
        self.stop_processing()
        res = self.stream_mgr.open_webcam(index)
        if res["success"]:
            self._reset_stats()
            self.stats["source_type"] = "webcam"
            self.start_processing()
        return res

    def _reset_stats(self):
        self.stats.update({
            "counts": {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0},
            "seen_ids": set(),
            "timeline": [],
            "frame_count": 0
        })
        self.tracker = VehicleTracker()
        self._broadcast_seq = 0


engine = DetectionEngine()
