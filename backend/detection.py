"""
detection.py — Optimized YOLOv10 Vehicle Detection Engine

Inference settings tuned for traffic CCTV:
  - imgsz=640       (speed/accuracy sweet spot)
  - conf=0.30       (catch small/distant motorcycles)
  - iou=0.45        (NMS removes duplicates)
  - max_det=300     (high-density traffic)
  - classes=[2,3,5,7] (filter at model level)
  - half=True       (FP16 on CUDA)
"""
import cv2
import numpy as np
import torch
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# COCO class IDs for vehicles
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

VEHICLE_COLORS = {
    "car": (0, 255, 0),
    "motorcycle": (0, 165, 255),
    "bus": (255, 0, 0),
    "truck": (128, 0, 128)
}

_model = None
_current_precision = None
_device = None

MODELS = {
    "low": "yolov10n.pt",
    "medium": "yolov10s.pt",
    "high": "yolov10m.pt"
}


def load_model(precision: str = None):
    """Load YOLOv10 model (singleton per precision). Applies FP16 on CUDA."""
    global _model, _current_precision, _device

    if precision is None:
        precision = settings.DEFAULT_PRECISION
    if precision not in MODELS:
        precision = "low"

    if _model is not None and _current_precision == precision:
        return _model

    from ultralytics import YOLO

    model_name = MODELS[precision]
    logger.info(f"Loading YOLOv10: {model_name} ({precision})")

    _model = YOLO(model_name)
    _current_precision = precision

    # Determine device
    if torch.cuda.is_available():
        _device = "cuda"
        if settings.HALF_PRECISION:
            _model.model.half()
            logger.info("FP16 half-precision enabled on CUDA")
    else:
        _device = "cpu"
        logger.info("Running on CPU (FP16 disabled)")

    return _model


def detect_vehicles(frame, confidence: float = None, track: bool = False):
    """
    Run YOLO inference with optimized parameters.
    All filtering happens inside the model — no redundant post-filter.
    """
    model = load_model()

    conf = confidence if confidence is not None else settings.CONF_THRESHOLD

    # Common kwargs for both detect and track modes
    kwargs = dict(
        conf=conf,
        iou=settings.IOU_THRESHOLD,
        imgsz=settings.IMGSZ,
        max_det=settings.MAX_DET,
        classes=settings.VEHICLE_CLASSES,
        verbose=False,
        device=_device,
    )

    # Only use half on CUDA
    if _device == "cuda" and settings.HALF_PRECISION:
        kwargs["half"] = True

    if track:
        kwargs["persist"] = True
        results = model.track(frame, **kwargs)
    else:
        results = model(frame, **kwargs)

    detections = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            if class_id not in VEHICLE_CLASSES:
                continue

            conf_val = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            detection = {
                "class_name": VEHICLE_CLASSES[class_id],
                "confidence": round(conf_val, 3),
                "bbox": [x1, y1, x2, y2],
                "x1": x1, "y1": y1,
                "x2": x2, "y2": y2
            }

            if track and hasattr(box, 'id') and box.id is not None:
                detection["track_id"] = int(box.id[0])

            detections.append(detection)

    return detections


def draw_boxes(frame, detections, tracking_data=None, show_timestamp: bool = False):
    """Draw styled bounding boxes with tracking overlays."""
    from datetime import datetime
    annotated = frame.copy()

    # Build tracking lookup
    tracking_lookup = {}
    if tracking_data:
        for track in tracking_data:
            tracking_lookup[track["track_id"]] = track

    # ── Stats HUD (top-left) ──
    overlay = annotated.copy()
    cv2.rectangle(overlay, (5, 5), (220, 110), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, annotated, 0.5, 0, annotated)

    cv2.putText(annotated, "VMS ACCURACY MONITOR", (15, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    active = len(tracking_data) if tracking_data else 0
    cv2.putText(annotated, f"Active Tracks: {active}", (15, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(annotated, f"Detections: {len(detections)}", (15, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    prec = _current_precision or "unknown"
    status_color = {
        "high": (0, 255, 0), "medium": (0, 255, 255), "low": (100, 100, 255)
    }.get(prec, (180, 180, 180))
    cv2.putText(annotated, f"Status: {prec.upper()} PRECISION", (15, 95),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, status_color, 1)

    # ── Draw each detection ──
    for det in detections:
        cls = det["class_name"]
        conf = det["confidence"]
        x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
        color = VEHICLE_COLORS.get(cls, (255, 255, 255))
        track_id = det.get("track_id")

        # Box + corner accents
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cl = 15
        for (px, py, dx, dy) in [
            (x1, y1, 1, 1), (x2, y1, -1, 1),
            (x1, y2, 1, -1), (x2, y2, -1, -1)
        ]:
            cv2.line(annotated, (px, py), (px + cl * dx, py), color, 3)
            cv2.line(annotated, (px, py), (px, py + cl * dy), color, 3)

        # Label
        label = f"{cls.upper()} {conf:.0%}"

        if track_id is not None and track_id in tracking_lookup:
            track = tracking_lookup[track_id]
            speed = track.get("speed_kmh", 0)
            direction = track.get("direction", "")
            age = track.get("frames_tracked", 0)
            centroid = track.get("centroid", [0, 0])
            cx, cy = int(centroid[0]), int(centroid[1])

            # Centroid dot
            cv2.circle(annotated, (cx, cy), 4, color, -1)
            cv2.circle(annotated, (cx, cy), 6, (255, 255, 255), 1)

            # Velocity arrow
            trajectory = track.get("trajectory", [])
            if len(trajectory) > 2:
                p1, p2 = trajectory[-2], trajectory[-1]
                v_dx = int((p2[0] - p1[0]) * 5)
                v_dy = int((p2[1] - p1[1]) * 5)
                cv2.arrowedLine(annotated, (cx, cy), (cx + v_dx, cy + v_dy),
                                (255, 255, 255), 2, tipLength=0.3)

            if age > 10:
                label += " [STABLE]"
            if speed > 0:
                label += f" | {speed}km/h"

            cv2.putText(annotated, direction, (x1, y1 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # Label background
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(annotated, (x1, y1 - th - 10), (x1 + tw + 10, y1), color, -1)
        cv2.putText(annotated, label, (x1 + 5, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        # Trajectory trail
        if track_id and track_id in tracking_lookup:
            trajectory = tracking_lookup[track_id].get("trajectory", [])
            if len(trajectory) > 1:
                points = np.array(trajectory, dtype=np.int32)
                cv2.polylines(annotated, [points], False, color, 1)

    # ── Timestamp overlay ──
    if show_timestamp:
        h, w = annotated.shape[:2]
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated, ts, (w - 200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.circle(annotated, (w - 220, 25), 5, (0, 0, 255), -1)
        cv2.putText(annotated, "LIVE", (w - 210, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    return annotated
