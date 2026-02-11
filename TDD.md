# Technical Design Document
## Vehicle Detection Dashboard using YOLO-NAS and Streamlit

**Version**: 1.0  
**Date**: 2026-02-09  
**Status**: Ready for Development  

---

## 1. System Overview

### 1.1 Functional Description

A single-page web dashboard that performs real-time vehicle detection on local MP4 video files. The system uses YOLO-NAS S (pretrained on COCO) for object detection, filtering results to four vehicle classes: car, motorcycle, bus, and truck. Results are displayed as annotated video frames alongside aggregated traffic statistics and time-series charts.

**Target Environment**:
- OS: Windows 10/11
- Hardware: CPU-only (no CUDA)
- Runtime: Python 3.9+, Streamlit server

### 1.2 Execution Flow

```
[User uploads MP4] 
    → [Save to temp file]
    → [Initialize VideoCapture]
    → [Load YOLO-NAS model (cached)]
    → [Frame loop]:
        → Read frame
        → Skip if frame_count % skip_rate != 0
        → Run inference
        → Filter vehicle detections
        → Draw bounding boxes
        → Update counters and timeline
        → Render to Streamlit placeholders
    → [Video ends or user stops]
    → [Display final statistics]
```

---

## 2. Component Breakdown

### 2.1 Video Ingestion Module

**Responsibility**: Handle video file upload, storage, and frame extraction.

| Function | Description |
|----------|-------------|
| File upload handler | Receives MP4/AVI/MOV via Streamlit uploader |
| Temp file writer | Writes uploaded bytes to temporary file on disk |
| VideoCapture wrapper | Opens video, provides frame iterator, exposes metadata (FPS, total frames) |
| Frame reader | Returns BGR numpy array per frame, signals EOF |

**Key Considerations**:
- Streamlit uploads files to memory; must write to disk for OpenCV
- VideoCapture requires file path, not file object
- Must handle codec variations gracefully

### 2.2 Inference Module

**Responsibility**: Load model and execute detection on individual frames.

| Function | Description |
|----------|-------------|
| Model loader | Downloads/caches YOLO-NAS S, sets eval mode |
| Frame preprocessor | Converts BGR→RGB for model input |
| Inference executor | Runs `model.predict()` with confidence threshold |
| Result extractor | Parses prediction object to get bboxes, confidences, class IDs |

**Model Specifications**:
- Architecture: YOLO-NAS Small
- Weights: COCO pretrained (80 classes)
- Input: RGB image (any resolution, internally resized)
- Output: List of (bbox_xyxy, confidence, class_id)

### 2.3 Post-Processing Module

**Responsibility**: Filter detections and aggregate statistics.

| Function | Description |
|----------|-------------|
| Vehicle filter | Keeps only detections where class_id ∈ {2, 3, 5, 7} |
| Class mapper | Maps COCO IDs to human labels (car, motorcycle, bus, truck) |
| Counter updater | Increments per-class dictionaries |
| Timeline appender | Adds per-frame vehicle count to time-series list |
| Speed estimator | Returns mocked/random value (no real computation) |

**COCO Class Mapping**:
| Class | COCO ID |
|-------|---------|
| car | 2 |
| motorcycle | 3 |
| bus | 5 |
| truck | 7 |

### 2.4 Visualization Module

**Responsibility**: Render annotated frames and charts to Streamlit UI.

| Function | Description |
|----------|-------------|
| Bounding box drawer | Draws rectangles and labels on frame using OpenCV |
| Frame displayer | Converts BGR→RGB, renders via `st.image()` |
| Stat card renderer | Generates HTML for styled metric cards |
| Pie chart builder | Creates Plotly donut chart from vehicle counts |
| Timeline chart builder | Creates Plotly line chart from time-series data |
| Layout manager | Arranges columns and placeholders in Streamlit |

---

## 3. Data Flow Diagram

### 3.1 Frame Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRAME LIFECYCLE                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  VideoCapture.read()                                                │
│        │                                                            │
│        ▼                                                            │
│  [BGR Frame: np.ndarray (H, W, 3)]                                  │
│        │                                                            │
│        ▼                                                            │
│  cv2.cvtColor(BGR → RGB)                                            │
│        │                                                            │
│        ▼                                                            │
│  model.predict(RGB frame)                                           │
│        │                                                            │
│        ├──────────────────────────────────────┐                     │
│        ▼                                      ▼                     │
│  [Detection List]                    [Original BGR Frame]           │
│        │                                      │                     │
│        ▼                                      ▼                     │
│  filter_vehicles()                   draw_detections()              │
│        │                                      │                     │
│        ▼                                      ▼                     │
│  [Filtered Detections]               [Annotated BGR Frame]          │
│        │                                      │                     │
│        ▼                                      ▼                     │
│  update_counters()                   cvtColor(BGR → RGB)            │
│  append_timeline()                            │                     │
│                                               ▼                     │
│                                      st.image(RGB frame)            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Detection Output Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DETECTION OUTPUT LIFECYCLE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  model.predict() returns ImageDetectionPrediction                   │
│        │                                                            │
│        ▼                                                            │
│  prediction.bboxes_xyxy  → [N x 4] float array                     │
│  prediction.confidence   → [N] float array                          │
│  prediction.labels       → [N] int array                            │
│        │                                                            │
│        ▼                                                            │
│  for each (bbox, conf, class_id):                                   │
│        │                                                            │
│        ├─── class_id NOT in VEHICLE_CLASSES → discard               │
│        │                                                            │
│        └─── class_id IN VEHICLE_CLASSES →                           │
│                    │                                                │
│                    ▼                                                │
│             (class_name, conf, x1, y1, x2, y2)                      │
│                    │                                                │
│                    ├──→ Draw bounding box on frame                  │
│                    │                                                │
│                    └──→ Increment vehicle_counts[class_name]        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Key Functions

### 4.1 Model Operations

| Function | Input | Output | Responsibility |
|----------|-------|--------|----------------|
| `load_model()` | None | YOLO-NAS model object | Load cached model, set eval mode |
| `detect_vehicles(model, frame)` | model, BGR frame | List[Tuple] | Run inference, filter to vehicles |

### 4.2 Visualization Operations

| Function | Input | Output | Responsibility |
|----------|-------|--------|----------------|
| `draw_detections(frame, detections)` | BGR frame, detection list | Annotated BGR frame | Render boxes and labels |
| `create_pie_chart(vehicle_counts)` | Dict[str, int] | Plotly Figure | Build distribution chart |
| `create_timeline_chart(timeline_data)` | List[int] | Plotly Figure | Build time-series chart |
| `render_stat_card(title, value, css_class)` | str, int, str | HTML string | Generate styled card HTML |

### 4.3 Main Loop

| Function | Input | Output | Responsibility |
|----------|-------|--------|----------------|
| `main()` | None | None | Orchestrate UI layout and frame loop |

---

## 5. State Management

### 5.1 Session State Variables

| Key | Type | Initial Value | Purpose |
|-----|------|---------------|---------|
| `vehicle_counts` | Dict[str, int] | `{car: 0, motorcycle: 0, bus: 0, truck: 0}` | Cumulative per-class counts |
| `timeline_data` | List[int] | `[]` | Per-frame detection counts (max 100 items) |
| `running` | bool | `False` | Controls frame loop execution |
| `total_frames` | int | `0` | Processed frame counter |

### 5.2 Streamlit Placeholders

| Placeholder | Purpose | Update Frequency |
|-------------|---------|------------------|
| `video_placeholder` | Display annotated frame | Every processed frame |
| `pie_placeholder` | Display distribution chart | Every 5 processed frames |
| `timeline_placeholder` | Display traffic timeline | Every 5 processed frames |
| `status_placeholder` | Show progress bar/messages | Every processed frame |

### 5.3 State Reset Triggers

- **Start Detection button**: Resets all counters, clears timeline, sets running=True
- **Stop button**: Sets running=False
- **Video EOF**: Sets running=False

---

## 6. Error Handling Strategy

### 6.1 Video Load Failure

| Condition | Detection | Response |
|-----------|-----------|----------|
| Invalid file format | `cap.isOpened() == False` | Display error message, abort processing |
| Corrupt video | `cap.read()` returns `(False, None)` prematurely | Treat as EOF, complete gracefully |
| File not found | Temp file write failure | Display error, return to upload state |

### 6.2 End-of-Video Handling

```
while st.session_state.running:
    ret, frame = cap.read()
    if not ret:
        # EOF reached
        status_placeholder.success("Video processing complete!")
        st.session_state.running = False
        break
```

- Update charts with final values
- Release VideoCapture
- Display completion message

### 6.3 Model Initialization Failure

| Condition | Detection | Response |
|-----------|-----------|----------|
| Network error (first run) | Exception in `models.get()` | Display error with install instructions |
| Corrupt weights | Model load exception | Display error, suggest cache clear |
| Import error | SuperGradients not installed | Display pip install command |

---

## 7. Performance Considerations

### 7.1 CPU Bottlenecks

| Operation | Typical Time (CPU) | Notes |
|-----------|-------------------|-------|
| YOLO-NAS inference | 200-500ms per frame | Primary bottleneck |
| Bounding box drawing | <5ms | Negligible |
| Chart updates | 10-50ms | Plotly rendering |
| Frame display | 5-10ms | Image encoding for Streamlit |

**Effective FPS**: 1-3 FPS on typical laptop CPU

### 7.2 Frame Skipping Strategy

```
frame_skip = user_selected_value  # Default: 2 (process 50% of frames)

if frame_count % frame_skip != 0:
    continue  # Skip this frame entirely
```

**Trade-off Matrix**:

| Skip Rate | % Frames Processed | Effective Speed |
|-----------|-------------------|-----------------|
| 1 | 100% | Slowest |
| 2 | 50% | 2x faster |
| 5 | 20% | 5x faster |
| 10 | 10% | 10x faster |

### 7.3 Memory Usage

| Resource | Approximate Size | Management |
|----------|------------------|------------|
| YOLO-NAS model | ~50MB | Loaded once (cached) |
| Frame buffer | ~6MB per 1080p frame | Overwritten each iteration |
| Timeline data | ~800 bytes max | Capped at 100 entries |
| Video file | Varies | Streamed, not fully loaded |

---

## 8. Configuration Parameters

### 8.1 User-Configurable (UI)

| Parameter | UI Element | Range | Default |
|-----------|------------|-------|---------|
| Frame skip rate | Slider | 1-10 | 2 |
| Confidence threshold | Slider | 0.1-0.9 | 0.5 |
| Video file | File uploader | MP4/AVI/MOV | None |

### 8.2 Hardcoded Constants

| Parameter | Value | Location |
|-----------|-------|----------|
| VEHICLE_CLASSES | {2, 3, 5, 7} | Module-level dict |
| VEHICLE_COLORS | BGR tuples | Module-level dict |
| Timeline max length | 100 | Frame loop |
| Chart update frequency | Every 5 frames | Frame loop |

---

## 9. Logging & Debugging

### 9.1 Console Logs

Currently minimal. Recommended additions for debugging:

```python
# Add to detect_vehicles():
logger.debug(f"Frame {frame_id}: {len(detections)} vehicles detected")

# Add to main loop:
logger.info(f"Processing started: {total_video_frames} frames @ {fps} FPS")
logger.warning(f"Model load took {elapsed}s")
```

### 9.2 Streamlit Status Messages

| Location | Message Type | Content |
|----------|--------------|---------|
| Model loading | Spinner | "Loading YOLO-NAS model..." |
| Video processing | Progress bar | "Processing: X% \| Frame N/M" |
| Video complete | Success | "Video processing complete!" |
| Errors | Error | Descriptive failure message |

### 9.3 Debug Mode (Not Implemented)

Suggested toggleable features:
- Show raw detection counts per frame
- Display inference time per frame
- Export detection log to CSV

---

## 10. Known Limitations

### 10.1 No Object Tracking

**Issue**: Each frame is processed independently. The same vehicle crossing multiple frames is counted multiple times.

**Impact**: `vehicle_counts` represents total detections, not unique vehicles.

**Mitigation**: Would require integrating a tracker (SORT, DeepSORT, ByteTrack).

### 10.2 Frame-Based Counting

**Issue**: Statistics are accumulated across all processed frames, not normalized by time.

**Impact**: Longer videos produce higher counts regardless of actual traffic density.

**Solution**: Could add per-second or per-minute normalization.

### 10.3 Non-Calibrated Speed Metric

**Issue**: "Average Speed" is a mocked random value (30-60 km/h).

**Impact**: No real speed estimation is performed.

**Requirements for Real Speed**:
- Camera calibration (focal length, mounting angle)
- Pixel-to-meter mapping
- Object tracking across frames

### 10.4 Single-Threaded Execution

**Issue**: Inference blocks the Streamlit event loop.

**Impact**: UI may feel unresponsive during heavy processing.

**Solution**: Could use threading or asyncio for background inference.

### 10.5 No Video Seek/Pause

**Issue**: Playback is continuous; users cannot jump to specific timestamps.

**Impact**: Must restart from beginning to re-analyze a section.

---

## Appendix A: File Structure

```
vehicle_detection_dashboard/
├── app.py              # 520 lines - Main application
├── requirements.txt    # Dependencies
└── README.md          # User documentation
```

## Appendix B: Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | ≥1.28.0 | Dashboard UI |
| opencv-python | ≥4.8.0 | Video processing |
| super-gradients | ≥3.3.0 | YOLO-NAS model |
| torch | ≥2.0.0 | Deep learning backend |
| plotly | ≥5.18.0 | Charts |
| numpy | ≥1.24.0 | Array operations |
| Pillow | ≥10.0.0 | Image utilities |
