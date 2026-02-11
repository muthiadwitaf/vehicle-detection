"""
tracker.py — Multi-Object Tracking Module

Tracks vehicles across frames, calculates direction and speed.
"""
import math
import logging
from typing import Dict, List, Tuple, Optional
from collections import deque

logger = logging.getLogger(__name__)


class Track:
    """Represents a single tracked vehicle."""
    
    def __init__(self, track_id: int, class_name: str, bbox: List[float], frame_number: int):
        self.track_id = track_id
        self.class_name = class_name
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.centroid = self._calculate_centroid(bbox)
        self.trajectory = deque(maxlen=30)  # Store last 30 positions
        self.trajectory.append((self.centroid, frame_number))
        self.frames_tracked = 1
        self.speed_kmh = 0.0
        self.direction = "Unknown"
        self.last_update_frame = frame_number
    
    def _calculate_centroid(self, bbox: List[float]) -> Tuple[float, float]:
        """Calculate center point of bounding box."""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        return (cx, cy)
    
    def update(self, bbox: List[float], frame_number: int):
        """Update track with new detection."""
        self.bbox = bbox
        self.centroid = self._calculate_centroid(bbox)
        self.trajectory.append((self.centroid, frame_number))
        self.frames_tracked += 1
        self.last_update_frame = frame_number
    
    def calculate_direction(self) -> str:
        """Calculate movement direction based on trajectory."""
        if len(self.trajectory) < 5:
            return "Unknown"
        
        # Get first and last positions from trajectory
        start_pos, _ = self.trajectory[0]
        end_pos, _ = self.trajectory[-1]
        
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        
        # Determine Flow (Masuk/Keluar) based on Y axis
        # Increasing Y (moving down) = MASUK (Towards camera)
        # Decreasing Y (moving up) = KELUAR (Away from camera)
        flow = "MASUK" if dy > 0 else "KELUAR"
        
        # Calculate angle in degrees
        angle = math.degrees(math.atan2(-dy, dx))  # Negative dy because y increases downward
        
        # Normalize to 0-360
        if angle < 0:
            angle += 360
        
        # Map to 8 compass directions (Indonesian)
        # E, NE, N, NW, W, SW, S, SE
        directions = ["Timur", "Timur Laut", "Utara", "Barat Laut", "Barat", "Barat Daya", "Selatan", "Tenggara"]
        index = int((angle + 22.5) / 45) % 8
        
        return f"{flow} ({directions[index]})"
    
    def calculate_speed(self, fps: float, pixels_per_meter: float) -> float:
        """
        Calculate speed in km/h.
        
        Args:
            fps: Frames per second of the video stream
            pixels_per_meter: Calibration factor (pixels per meter)
        
        Returns:
            Speed in km/h
        """
        if len(self.trajectory) < 5 or fps <= 0 or pixels_per_meter <= 0:
            return 0.0
        
        # Calculate displacement over last N frames
        window_size = min(10, len(self.trajectory))
        start_pos, start_frame = self.trajectory[-window_size]
        end_pos, end_frame = self.trajectory[-1]
        
        # Calculate pixel distance
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        pixel_distance = math.sqrt(dx**2 + dy**2)
        
        # Convert to meters
        distance_meters = pixel_distance / pixels_per_meter
        
        # Calculate time elapsed
        frames_elapsed = end_frame - start_frame
        if frames_elapsed == 0:
            return 0.0
        
        time_seconds = frames_elapsed / fps
        
        # Calculate speed in m/s, then convert to km/h
        speed_ms = distance_meters / time_seconds
        speed_kmh = speed_ms * 3.6
        
        # Clamp to reasonable values (0-200 km/h)
        speed_kmh = max(0, min(200, speed_kmh))
        
        return round(speed_kmh, 1)
    
    def to_dict(self) -> dict:
        """Convert track to dictionary for JSON serialization."""
        return {
            "track_id": self.track_id,
            "class": self.class_name,
            "bbox": self.bbox,
            "centroid": list(self.centroid),
            "speed_kmh": self.speed_kmh,
            "direction": self.direction,
            "frames_tracked": self.frames_tracked,
            "trajectory": [list(pos) for pos, _ in list(self.trajectory)[-10:]]  # Last 10 points
        }


class VehicleTracker:
    """Manages multiple vehicle tracks."""
    
    def __init__(self, fps: float = 25.0, pixels_per_meter: float = 50.0):
        """
        Initialize tracker.
        
        Args:
            fps: Frames per second of the video stream
            pixels_per_meter: Calibration factor (default: 50 pixels = 1 meter)
        """
        self.tracks: Dict[int, Track] = {}
        self.fps = fps
        self.pixels_per_meter = pixels_per_meter
        self.frame_number = 0
        self.max_age = 30  # Remove tracks not updated for 30 frames
        
        logger.info(f"VehicleTracker initialized: fps={fps}, ppm={pixels_per_meter}")
    
    def update(self, detections: List[dict]) -> List[dict]:
        """
        Update tracker with new detections from YOLO.
        
        Args:
            detections: List of detection dicts with 'track_id', 'class_name', 'bbox'
        
        Returns:
            List of enriched tracking data with speed and direction
        """
        self.frame_number += 1
        current_track_ids = set()
        
        # Update existing tracks or create new ones
        for det in detections:
            track_id = det.get("track_id")
            if track_id is None:
                continue
            
            current_track_ids.add(track_id)
            
            if track_id in self.tracks:
                # Update existing track
                self.tracks[track_id].update(det["bbox"], self.frame_number)
            else:
                # Create new track
                self.tracks[track_id] = Track(
                    track_id=track_id,
                    class_name=det["class_name"],
                    bbox=det["bbox"],
                    frame_number=self.frame_number
                )
        
        # Remove stale tracks
        stale_ids = []
        for track_id, track in self.tracks.items():
            if self.frame_number - track.last_update_frame > self.max_age:
                stale_ids.append(track_id)
        
        for track_id in stale_ids:
            del self.tracks[track_id]
            logger.debug(f"Removed stale track {track_id}")
        
        # Calculate speed and direction for all active tracks
        tracking_data = []
        for track_id in current_track_ids:
            if track_id in self.tracks:
                track = self.tracks[track_id]
                track.direction = track.calculate_direction()
                track.speed_kmh = track.calculate_speed(self.fps, self.pixels_per_meter)
                tracking_data.append(track.to_dict())
        
        return tracking_data
    
    def set_calibration(self, fps: float = None, pixels_per_meter: float = None):
        """Update calibration parameters."""
        if fps is not None:
            self.fps = fps
            logger.info(f"Updated FPS: {fps}")
        
        if pixels_per_meter is not None:
            self.pixels_per_meter = pixels_per_meter
            logger.info(f"Updated pixels_per_meter: {pixels_per_meter}")
    
    def reset(self):
        """Clear all tracks."""
        self.tracks.clear()
        self.frame_number = 0
        logger.info("Tracker reset")
    
    def get_statistics(self) -> dict:
        """Get tracking statistics."""
        if not self.tracks:
            return {
                "active_tracks": 0,
                "avg_speed": 0.0,
                "direction_distribution": {}
            }
        
        speeds = [t.speed_kmh for t in self.tracks.values() if t.speed_kmh > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        
        # Direction distribution
        directions = [t.direction for t in self.tracks.values() if t.direction != "Unknown"]
        direction_dist = {}
        for d in directions:
            direction_dist[d] = direction_dist.get(d, 0) + 1
        
        return {
            "active_tracks": len(self.tracks),
            "avg_speed": round(avg_speed, 1),
            "direction_distribution": direction_dist
        }
