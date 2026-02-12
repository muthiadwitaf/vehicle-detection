"""
detection.py — YOLOv10 Vehicle Detection Engine
"""
import cv2
import numpy as np
import torch

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

MODELS = {
    "low": "yolov10n.pt",
    "medium": "yolov10s.pt",
    "high": "yolov10m.pt"  # Medium as High for balance, or yolov10l.pt for true high
}

def load_model(precision: str = "low"):
    """Load YOLOv10 model based on precision (singleton per precision)."""
    global _model, _current_precision
    
    # Validation
    if precision not in MODELS:
        precision = "low"
        
    if _model is None or _current_precision != precision:
        from ultralytics import YOLO
        import logging
        logger = logging.getLogger(__name__)
        
        model_name = MODELS[precision]
        logger.info(f"Loading YOLOv10 model: {model_name} ({precision} precision)")
        _model = YOLO(model_name)
        _current_precision = precision
        
    return _model


def calculate_ioa(box_a, box_b):
    """
    Calculate Intersection over Area of Box A relative to Box B.
    Used to see how much of Box A is contained inside Box B.
    """
    x1_a, y1_a, x2_a, y2_a = box_a
    x1_b, y1_b, x2_b, y2_b = box_b

    # Intersection coordinates
    xi1 = max(x1_a, x1_b)
    yi1 = max(y1_a, y1_b)
    xi2 = min(x2_a, x2_b)
    yi2 = min(y2_a, y2_b)

    if xi2 <= xi1 or yi2 <= yi1:
        return 0.0

    inter_area = (xi2 - xi1) * (yi2 - yi1)
    area_a = (x2_a - x1_a) * (y2_a - y1_a)

    return inter_area / area_a if area_a > 0 else 0.0


def detect_vehicles(frame, confidence: float = 0.5, track: bool = False):
    """
    Run YOLOv10 inference and return vehicle detections.
    """
    model = load_model()
    
    # Use tracking or detection mode
    if track:
        results = model.track(frame, conf=confidence, persist=True, verbose=False)
    else:
        results = model(frame, conf=confidence, verbose=False)

    detections = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            if class_id in VEHICLE_CLASSES:
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                detection = {
                    "class_name": VEHICLE_CLASSES[class_id],
                    "confidence": round(conf, 3),
                    "bbox": [x1, y1, x2, y2],
                    "x1": x1, "y1": y1,
                    "x2": x2, "y2": y2
                }
                
                # Add track_id if tracking is enabled
                if track and hasattr(box, 'id') and box.id is not None:
                    detection["track_id"] = int(box.id[0])
                
                detections.append(detection)
    
    return detections



def draw_boxes(frame, detections, tracking_data=None, show_timestamp: bool = False):
    """
    Draw styled bounding boxes with corner accents and tracking info.
    
    Args:
        frame: Input frame
        detections: List of detection dicts
        tracking_data: Optional list of tracking dicts with speed/direction
        show_timestamp: Whether to show timestamp overlay
    """
    from datetime import datetime
    annotated = frame.copy()
    
    # Create lookup for tracking data by track_id
    tracking_lookup = {}
    if tracking_data:
        for track in tracking_data:
            tracking_lookup[track["track_id"]] = track

    # Draw Statistics Board (Top Left)
    overlay = annotated.copy()
    cv2.rectangle(overlay, (5, 5), (220, 110), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, annotated, 0.5, 0, annotated)
    
    cv2.putText(annotated, "VMS ACCURACY MONITOR", (15, 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    # Calculate global flow if tracking stats are available
    active = 0
    if tracking_data:
        active = len(tracking_data)
    
    cv2.putText(annotated, f"Active Tracks: {active}", (15, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(annotated, f"Detections: {len(detections)}", (15, 70), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    # Dynamic Status Label
    status_text = f"Status: {_current_precision.upper()} PRECISION" if _current_precision else "Status: UNKNOWN"
    status_color = (0, 255, 0) if _current_precision == "high" else (0, 255, 255) if _current_precision == "medium" else (100, 100, 255)
    
    cv2.putText(annotated, status_text, (15, 95), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, status_color, 1)

    for det in detections:
        cls = det["class_name"]
        conf = det["confidence"]
        x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
        color = VEHICLE_COLORS.get(cls, (255, 255, 255))
        track_id = det.get("track_id")

        # Rectangle + corner accents
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cl = 15
        for (px, py, dx, dy) in [
            (x1, y1, 1, 1), (x2, y1, -1, 1),
            (x1, y2, 1, -1), (x2, y2, -1, -1)
        ]:
            cv2.line(annotated, (px, py), (px + cl * dx, py), color, 3)
            cv2.line(annotated, (px, py), (px, py + cl * dy), color, 3)

        # Build label with tracking info
        label = f"{cls.upper()} {conf:.0%}"
        
        # Stability / Accuracy Markers
        if track_id is not None and track_id in tracking_lookup:
            track = tracking_lookup[track_id]
            speed = track.get("speed_kmh", 0)
            direction = track.get("direction", "")
            age = track.get("frames_tracked", 0)
            centroid = track.get("centroid", [0, 0])
            cx, cy = int(centroid[0]), int(centroid[1])
            
            # 1. Draw Centroid (Target Lock)
            cv2.circle(annotated, (cx, cy), 4, color, -1)
            cv2.circle(annotated, (cx, cy), 6, (255, 255, 255), 1)
            
            # 2. Draw Movement Vector (Velocity Arrow)
            trajectory = track.get("trajectory", [])
            if len(trajectory) > 2:
                # Get last vector
                p1 = trajectory[-2]
                p2 = trajectory[-1]
                v_dx = int((p2[0] - p1[0]) * 5) # Scale for visibility
                v_dy = int((p2[1] - p1[1]) * 5)
                cv2.arrowedLine(annotated, (cx, cy), (cx + v_dx, cy + v_dy), (255, 255, 255), 2, tipLength=0.3)

            # 3. Enhanced Label
            # Label prefix '#track_id' removed as per user request
            if age > 10: # Only show stability info after 10 frames
                label += f" [STABLE]"
            
            if speed > 0:
                label += f" | {speed}km/h"
            
            # Show Direction above the box if active
            cv2.putText(annotated, direction, (x1, y1 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # Draw label background and text
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(annotated, (x1, y1 - th - 10), (x1 + tw + 10, y1), color, -1)
        cv2.putText(annotated, label, (x1 + 5, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        # Draw trajectory
        if track_id and track_id in tracking_lookup:
            trajectory = tracking_lookup[track_id].get("trajectory", [])
            if len(trajectory) > 1:
                points = np.array(trajectory, dtype=np.int32)
                cv2.polylines(annotated, [points], False, color, 1) # Thin trail

    if show_timestamp:
        h, w = annotated.shape[:2]
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated, ts, (w - 200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.circle(annotated, (w - 220, 25), 5, (0, 0, 255), -1)
        cv2.putText(annotated, "LIVE", (w - 210, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    return annotated
