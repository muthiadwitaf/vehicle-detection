"""
database.py — PostgreSQL Database Module for Counter Persistence

Handles saving and loading vehicle detection counts per camera.
"""
import os
import logging
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration (can be overridden via environment variables)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

_connection = None


def get_connection():
    """Get or create database connection (singleton)."""
    global _connection
    try:
        import psycopg2
        
        if _connection is None or _connection.closed:
            _connection = psycopg2.connect(**DB_CONFIG)
            logger.info(f"Connected to PostgreSQL database: {DB_CONFIG['database']}")
        
        return _connection
    except ImportError:
        logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
        return None
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.info("Counter persistence disabled. Counts will reset on restart.")
        return None


def init_db():
    """Initialize database schema (create tables if not exist)."""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create detection_counts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detection_counts (
                id SERIAL PRIMARY KEY,
                camera_id VARCHAR(100) NOT NULL UNIQUE,
                camera_name VARCHAR(200),
                car_count INTEGER DEFAULT 0,
                motorcycle_count INTEGER DEFAULT 0,
                bus_count INTEGER DEFAULT 0,
                truck_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Migration (removed bicycle_count as it is now being dropped)
        
        # Create index on camera_id for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_camera_id 
            ON detection_counts(camera_id);
        """)
        
        conn.commit()
        cursor.close()
        logger.info("Database schema initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def save_counts(camera_id: str, camera_name: str, counts: Dict[str, int]) -> bool:
    """
    Save or update detection counts for a camera.
    
    Args:
        camera_id: Unique camera identifier
        camera_name: Human-readable camera name
        counts: Dict with keys: car, motorcycle, bus, truck
    
    Returns:
        True if successful, False otherwise
    """
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Upsert (INSERT ... ON CONFLICT UPDATE)
        cursor.execute("""
            INSERT INTO detection_counts 
                (camera_id, camera_name, car_count, motorcycle_count, bus_count, truck_count, last_updated)
            VALUES 
                (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (camera_id) 
            DO UPDATE SET
                camera_name = EXCLUDED.camera_name,
                car_count = EXCLUDED.car_count,
                motorcycle_count = EXCLUDED.motorcycle_count,
                bus_count = EXCLUDED.bus_count,
                truck_count = EXCLUDED.truck_count,
                last_updated = NOW();
        """, (
            camera_id,
            camera_name,
            counts.get("car", 0),
            counts.get("motorcycle", 0),
            counts.get("bus", 0),
            counts.get("truck", 0),
        ))
        
        conn.commit()
        cursor.close()
        logger.debug(f"Saved counts for camera {camera_id}: {counts}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save counts for {camera_id}: {e}")
        conn.rollback()
        return False


def load_counts(camera_id: str) -> Optional[Dict[str, int]]:
    """
    Load saved detection counts for a camera.
    
    Args:
        camera_id: Unique camera identifier
    
    Returns:
        Dict with counts or None if not found
    """
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT car_count, motorcycle_count, bus_count, truck_count
            FROM detection_counts
            WHERE camera_id = %s;
        """, (camera_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            counts = {
                "car": row[0],
                "motorcycle": row[1],
                "bus": row[2],
                "truck": row[3],
            }
            logger.info(f"Loaded counts for camera {camera_id}: {counts}")
            return counts
        else:
            logger.debug(f"No saved counts found for camera {camera_id}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to load counts for {camera_id}: {e}")
        return None


def get_all_counts() -> list:
    """
    Get all saved camera counts.
    
    Returns:
        List of dicts with camera stats
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT camera_id, camera_name, car_count, motorcycle_count, 
                   bus_count, truck_count, last_updated
            FROM detection_counts
            ORDER BY last_updated DESC;
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        
        results = []
        for row in rows:
            results.append({
                "camera_id": row[0],
                "camera_name": row[1],
                "counts": {
                    "car": row[2],
                    "motorcycle": row[3],
                    "bus": row[4],
                    "truck": row[5],
                },
                "total": sum(row[2:6]),
                "last_updated": row[6].isoformat() if row[6] else None,
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to get all counts: {e}")
        return []


def close_connection():
    """Close database connection."""
    global _connection
    if _connection and not _connection.closed:
        _connection.close()
        logger.info("Database connection closed")
