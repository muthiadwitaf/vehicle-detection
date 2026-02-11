"""
main.py — FastAPI Backend for Vehicle Detection Dashboard
Provides REST API + WebSocket for real-time video streaming with detection.
"""
import os
import sys
import cv2
import json
import time
import asyncio
import base64
import tempfile
import logging
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure backend directory is in path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from detection import load_model, detect_vehicles, draw_boxes
from stream_manager import StreamManager
from database import init_db, save_counts, load_counts, get_all_counts
from tracker import VehicleTracker

# ============================================================================
# APP SETUP
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vehicle Detection API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
stream_mgr = StreamManager()
tracker = None  # Will be initialized when stream starts
stats = {
    "counts": {"bicycle": 0, "car": 0, "motorcycle": 0, "bus": 0, "truck": 0},
    "seen_ids": set(),
    "timeline": [],
    "frame_count": 0,
    "is_running": False,
    "source_type": None,
    "tracking_enabled": True,  # Enable tracking by default
    "model_precision": "low", # Initial precision
}

# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/stats")
async def get_stats():
    """Return current detection statistics."""
    return {
        "counts": stats["counts"],
        "timeline": stats["timeline"][-100:],
        "frame_count": stats["frame_count"],
        "is_running": stats["is_running"],
        "source_type": stats["source_type"],
        "total_detected": sum(stats["counts"].values()),
    }


@app.post("/api/stop")
async def stop_processing():
    """Stop video processing and save counts to database."""
    stats["is_running"] = False
    stream_mgr.stop()
    
    # Save final counts to database
    if stats.get("current_camera_id"):
        save_counts(
            camera_id=stats["current_camera_id"],
            camera_name=stats.get("current_camera_name", ""),
            counts=stats["counts"]
        )
        logger.info(f"Saved final counts for {stats['current_camera_id']}")
    
    return {"status": "stopped", "final_counts": stats["counts"]}


@app.post("/api/test-rtsp")
async def test_rtsp(url: str = Form(...)):
    """Test RTSP connection."""
    result = StreamManager.test_rtsp(url)
    return result


@app.get("/api/camera-presets")
async def get_camera_presets():
    """Load RTSP camera presets from config file."""
    try:
        presets_file = Path(__file__).parent / "camera_presets.json"
        if presets_file.exists():
            with open(presets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        return {"cameras": []}
    except Exception as e:
        logger.error(f"Failed to load camera presets: {e}")
        return {"cameras": []}


@app.post("/api/start/file")
async def start_file(video: UploadFile = File(...)):
    """Upload and start processing a video file."""
    # Save uploaded file
    suffix = Path(video.filename).suffix or ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    content = await video.read()
    tmp.write(content)
    tmp.close()

    # Open the file
    result = stream_mgr.open_file(tmp.name)
    if not result["success"]:
        return JSONResponse(status_code=400, content=result)

    # Reset stats
    stats["counts"] = {"bicycle": 0, "car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    stats["seen_ids"] = set()
    stats["timeline"] = []
    stats["frame_count"] = 0
    stats["is_running"] = True
    stats["source_type"] = "file"

    return {
        "status": "started",
        "source": "file",
        "filename": video.filename,
        "total_frames": result.get("total_frames", 0),
        "fps": result.get("fps", 30),
    }


@app.post("/api/start/rtsp")
async def start_rtsp(url: str = Form(...), camera_id: str = Form(None), camera_name: str = Form(None)):
    """Start RTSP stream and load saved counts if available."""
    result = stream_mgr.open_rtsp(url)
    if not result["success"]:
        return JSONResponse(status_code=400, content=result)

    # Try to load saved counts for this camera
    saved_counts = None
    if camera_id:
        saved_counts = load_counts(camera_id)
        stats["current_camera_id"] = camera_id
        stats["current_camera_name"] = camera_name or camera_id
    else:
        stats["current_camera_id"] = None
        stats["current_camera_name"] = None

    # Initialize or resume counts
    if saved_counts:
        stats["counts"] = saved_counts
        logger.info(f"Resumed counts for {camera_id}: {saved_counts}")
    else:
        stats["counts"] = {"bicycle": 0, "car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    
    stats["seen_ids"] = set()
    stats["timeline"] = []
    stats["frame_count"] = 0
    stats["is_running"] = True
    stats["source_type"] = "rtsp"
    
    # Initialize tracker
    global tracker
    tracker = VehicleTracker(fps=25.0, pixels_per_meter=50.0)
    logger.info("Vehicle tracker initialized")

    return {
        "status": "started",
        "source": "rtsp",
        "transport": result.get("transport", "TCP"),
        "counts": stats["counts"],
        "resumed": saved_counts is not None,
    }


@app.get("/api/cameras")
async def list_cameras():
    """Scan and list available local cameras/webcams."""
    cameras = StreamManager.scan_cameras()
    return {"cameras": cameras}


@app.post("/api/start/webcam")
async def start_webcam(index: int = Form(0)):
    """Start a local webcam by index."""
    result = stream_mgr.open_webcam(index)
    if not result["success"]:
        return JSONResponse(status_code=400, content=result)

    # Reset stats
    stats["counts"] = {"bicycle": 0, "car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    stats["seen_ids"] = set()
    stats["timeline"] = []
    stats["frame_count"] = 0
    stats["is_running"] = True
    stats["source_type"] = "webcam"

    return {
        "status": "started",
        "source": "webcam",
        "camera_index": result.get("camera_index", 0),
        "width": result.get("width"),
        "height": result.get("height"),
    }


# ============================================================================
# WEBSOCKET — REAL-TIME VIDEO STREAM
# ============================================================================

@app.websocket("/ws/video")
async def video_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for streaming video frames with detections.
    Client sends JSON config: { "frame_skip": 2, "confidence": 0.5 }
    Server sends JSON: { "frame": base64_jpeg, "detections": [...], "counts": {...}, "frame_count": N }
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    # Default settings
    frame_skip = 2
    confidence = 0.5

    # Pre-load the model
    try:
        load_model()
    except Exception as e:
        await websocket.send_json({"error": f"Model load failed: {str(e)}"})
        await websocket.close()
        return

    try:
        while True:
            # Check for config updates (non-blocking)
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                config = json.loads(msg)
                frame_skip = config.get("frame_skip", frame_skip)
                confidence = config.get("confidence", confidence)
                
                # Dynamic Precision Update
                new_precision = config.get("precision")
                if new_precision and new_precision in ["low", "medium", "high"]:
                    if new_precision != stats["model_precision"]:
                        stats["model_precision"] = new_precision
                        try:
                            load_model(new_precision)
                            logger.info(f"Dynamically switched to {new_precision} precision")
                        except Exception as e:
                            logger.error(f"Precision switch failed: {e}")

                # Handle stop command
                if config.get("command") == "stop":
                    stats["is_running"] = False
                    stream_mgr.stop()
                    await websocket.send_json({"status": "stopped"})
                    continue

            except asyncio.TimeoutError:
                pass

            # Skip if not running
            if not stats["is_running"]:
                await asyncio.sleep(0.1)
                continue

            # Read frame
            ret, frame = stream_mgr.read_frame()
            if not ret:
                if stats["source_type"] == "file":
                    stats["is_running"] = False
                    await websocket.send_json({
                        "status": "complete",
                        "counts": stats["counts"],
                        "total_detected": sum(stats["counts"].values()),
                    })
                    continue
                else:
                    await asyncio.sleep(0.1)
                    continue

            stats["frame_count"] += 1

            # Frame skip
            if stats["frame_count"] % frame_skip != 0:
                continue

            # Run detection with tracking
            tracking_enabled = stats.get("tracking_enabled", True)
            detections = detect_vehicles(frame, confidence, track=tracking_enabled)

            # Update tracker and get tracking data
            tracking_data = []
            tracking_stats = {}
            if tracking_enabled and tracker:
                tracking_data = tracker.update(detections)
                tracking_stats = tracker.get_statistics()

            # Update counts (Cumulative using unique tracking IDs)
            frame_vehicles = 0
            for det in detections:
                cls = det["class_name"]
                track_id = det.get("track_id")
                
                # Only count unique objects if tracking is enabled
                if tracking_enabled and track_id is not None:
                    if track_id not in stats["seen_ids"]:
                        stats["seen_ids"].add(track_id)
                        stats["counts"][cls] = stats["counts"].get(cls, 0) + 1
                elif not tracking_enabled:
                    # Fallback for non-tracking mode (less accurate cumulative)
                    # We increment once per detection in the frame, but it will double count
                    # objects that stay in the frame over time. 
                    # This is why tracking is recommended.
                    stats["counts"][cls] = stats["counts"].get(cls, 0) + 1
                    
                frame_vehicles += 1

            stats["timeline"].append(frame_vehicles)
            if len(stats["timeline"]) > 100:
                stats["timeline"] = stats["timeline"][-100:]

            # Auto-save counts to database every 30 frames
            if stats.get("current_camera_id") and stats["frame_count"] % 30 == 0:
                save_counts(
                    camera_id=stats["current_camera_id"],
                    camera_name=stats.get("current_camera_name", ""),
                    counts=stats["counts"]
                )

            # Draw boxes with tracking info
            is_live = stats["source_type"] in ("rtsp", "webcam")
            annotated = draw_boxes(frame, detections, tracking_data, show_timestamp=is_live)

            # Encode frame to JPEG base64
            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
            frame_b64 = base64.b64encode(buffer).decode('utf-8')

            # Send to client
            await websocket.send_json({
                "frame": frame_b64,
                "detections": detections,
                "counts": stats["counts"],
                "timeline": stats["timeline"][-100:],
                "frame_count": stats["frame_count"],
                "frame_vehicles": frame_vehicles,
                "total_detected": sum(stats["counts"].values()),
                "source_type": stats["source_type"],
                "tracking_data": tracking_data,
                "tracking_stats": tracking_stats,
            })

            await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("WebSocket connection closed")


# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup():
    """Pre-load model and initialize database on startup."""
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Load YOLO model
    logger.info("Loading YOLOv10 model...")
    try:
        load_model()
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Model load failed: {e}")


if __name__ == "__main__":
    import uvicorn
    # Change to backend directory for model downloads
    os.chdir(Path(__file__).parent)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
