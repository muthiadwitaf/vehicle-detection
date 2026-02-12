"""
config.py - Centralized Performance & Application Configuration
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Vehicle Detection API"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")

    # ── Inference ──────────────────────────────────────
    IMGSZ: int = 640               # YOLO input resolution (px)
    CONF_THRESHOLD: float = 0.30   # Low to catch small/distant vehicles
    IOU_THRESHOLD: float = 0.45    # NMS overlap threshold
    MAX_DET: int = 300             # Max detections per frame
    HALF_PRECISION: bool = True    # FP16 on CUDA (2x speedup)
    VEHICLE_CLASSES: list = [2, 3, 5, 7]  # COCO: car, motorcycle, bus, truck
    DEFAULT_PRECISION: str = "low"

    # ── Frame Rate Control ─────────────────────────────
    INFER_FPS: int = 12            # Target inference FPS (adaptive)
    BROADCAST_FPS: int = 15        # WebSocket send rate
    META_EVERY_N: int = 5          # Send metadata every Nth broadcast

    # ── Encoding ───────────────────────────────────────
    JPEG_QUALITY: int = 75         # JPEG encode quality (0-100)
    FRAME_RESIZE_WIDTH: int = 960  # Resize annotated frame before encode

    # ── Persistence ────────────────────────────────────
    DB_SAVE_INTERVAL: int = 60     # Frames between DB writes

    # ── WebSocket ──────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
