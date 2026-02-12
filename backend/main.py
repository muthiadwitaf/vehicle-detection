"""
main.py — Production Entry Point

Broadcast loop consumes frames from engine at BROADCAST_FPS rate.
Engine runs detection independently at INFER_FPS rate.
"""
import asyncio
import json
import logging
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from services.websocket import manager
from services.engine import engine
from database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


# ── Broadcast Loop ─────────────────────────────────

async def broadcast_loop():
    """Consume latest frame from engine and broadcast to all clients."""
    interval = 1.0 / settings.BROADCAST_FPS
    logger.info(f"Broadcast loop started (target {settings.BROADCAST_FPS} FPS)")

    while True:
        try:
            data = engine.get_broadcast_data()
            if data and manager.clients:
                await manager.broadcast(data)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await asyncio.sleep(0.5)


# ── App Lifespan ───────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    init_db()
    task = asyncio.create_task(broadcast_loop())
    yield
    logger.info("Shutting down...")
    task.cancel()
    engine.stop_processing()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST Endpoints ─────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "engine_running": engine.is_running,
        "clients": len(manager.clients),
        "fps": round(engine.actual_fps, 1),
        "infer_ms": round(engine.infer_time_ms, 1),
    }

@app.get("/api/presets")
async def get_presets():
    preset_path = Path(__file__).parent / "camera_presets.json"
    if preset_path.exists():
        with open(preset_path, "r") as f:
            return json.load(f)
    return {"cameras": []}

@app.get("/api/stats")
async def get_stats():
    return {
        "counts": engine.stats["counts"],
        "timeline": engine.stats["timeline"][-20:],
        "is_running": engine.is_running,
        "source_type": engine.stats["source_type"],
        "fps": round(engine.actual_fps, 1),
    }

@app.post("/api/stop")
async def stop_processing():
    engine.stop_processing()
    await manager.broadcast({"status": "stopped"})
    return {"status": "stopped"}

@app.post("/api/start/rtsp")
async def start_rtsp(url: str = Form(...), camera_id: str = Form(None), camera_name: str = Form(None)):
    result = engine.set_source_rtsp(url, camera_id, camera_name)
    if not result["success"]:
        return JSONResponse(status_code=400, content=result)
    return {"status": "started", "source": "rtsp", "details": result}

@app.post("/api/start/file")
async def start_file(video: UploadFile = File(...)):
    import tempfile
    import shutil

    suffix = Path(video.filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video.file, tmp)
        tmp_path = tmp.name

    result = engine.set_source_file(tmp_path)
    if not result["success"]:
        return JSONResponse(status_code=400, content=result)
    return {"status": "started", "source": "file", "details": result}

@app.post("/api/start/webcam")
async def start_webcam(index: int = Form(0)):
    result = engine.set_source_webcam(index)
    if not result["success"]:
        return JSONResponse(status_code=400, content=result)
    return {"status": "started", "source": "webcam", "details": result}


# ── WebSocket ──────────────────────────────────────

@app.websocket("/ws/video")
async def video_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if "confidence" in data:
                pass  # Future: dynamic config updates
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WS Error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT,
                log_level="info", reload=settings.DEBUG)
