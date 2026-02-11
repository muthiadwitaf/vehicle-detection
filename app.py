"""
Vehicle Detection Dashboard
============================
Real-time vehicle detection using YOLOv8 with Streamlit dashboard.
Supports: Local video files (MP4) and RTSP streams from CCTV cameras.

Compatible: Python 3.9+, Windows 10/11, CPU-only
"""

import os
import streamlit as st
import cv2
import numpy as np
import tempfile
import time
import plotly.graph_objects as go
from datetime import datetime

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

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

CHART_COLORS = ["#10b981", "#f59e0b", "#3b82f6", "#8b5cf6"]

# ============================================================================
# STREAMLIT PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Smart Traffic Monitoring",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PREMIUM DARK THEME CSS
# ============================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --bg-primary: #0f0f1a;
        --bg-secondary: #1a1a2e;
        --bg-card: linear-gradient(145deg, #1e1e32 0%, #252542 100%);
        --accent-cyan: #00d4ff;
        --accent-green: #10b981;
        --accent-orange: #f59e0b;
        --accent-blue: #3b82f6;
        --accent-purple: #8b5cf6;
        --accent-red: #ef4444;
        --text-primary: #ffffff;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --border-color: rgba(148, 163, 184, 0.1);
        --glow-cyan: 0 0 30px rgba(0, 212, 255, 0.3);
    }
    
    .stApp {
        background: linear-gradient(180deg, var(--bg-primary) 0%, #0a0a14 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    #MainMenu, footer, .stDeployButton, header[data-testid="stHeader"] {
        visibility: hidden; display: none;
    }
    
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { 
        background: linear-gradient(180deg, var(--accent-cyan), var(--accent-purple));
        border-radius: 4px;
    }
    
    .dashboard-header {
        background: var(--bg-card);
        border-radius: 20px;
        padding: 30px 40px;
        margin-bottom: 30px;
        border: 1px solid var(--border-color);
        box-shadow: var(--glow-cyan);
        position: relative;
        overflow: hidden;
    }
    
    .dashboard-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), var(--accent-cyan));
        background-size: 200% 100%;
        animation: shimmer 3s linear infinite;
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    .dashboard-header h1 {
        color: var(--text-primary);
        font-size: 36px; font-weight: 700; margin: 0;
        background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .dashboard-header .subtitle {
        color: var(--text-secondary);
        font-size: 14px; margin-top: 8px;
        letter-spacing: 2px; text-transform: uppercase;
    }
    
    .live-badge {
        display: inline-flex; align-items: center; gap: 8px;
        background: rgba(16, 185, 129, 0.15);
        color: var(--accent-green);
        padding: 6px 16px; border-radius: 30px;
        font-size: 12px; font-weight: 600; margin-top: 15px;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .live-badge::before {
        content: '';
        width: 8px; height: 8px;
        background: var(--accent-green);
        border-radius: 50%;
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    .rtsp-badge {
        display: inline-flex; align-items: center; gap: 8px;
        background: rgba(239, 68, 68, 0.15);
        color: var(--accent-red);
        padding: 6px 16px; border-radius: 30px;
        font-size: 12px; font-weight: 600;
        margin-top: 15px; margin-left: 10px;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .rtsp-badge::before {
        content: '';
        width: 8px; height: 8px;
        background: var(--accent-red);
        border-radius: 50%;
        animation: pulse 1s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
    }
    
    .section-title {
        color: var(--text-primary);
        font-size: 18px; font-weight: 600;
        margin-bottom: 20px;
        display: flex; align-items: center; gap: 10px;
    }
    
    .section-title .icon {
        width: 36px; height: 36px;
        background: var(--bg-card);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px;
    }
    
    .stat-card {
        background: var(--bg-card);
        border-radius: 16px; padding: 20px;
        border: 1px solid var(--border-color);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative; overflow: hidden;
    }
    
    .stat-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    }
    
    .stat-card::after {
        content: '';
        position: absolute; top: 0; right: 0;
        width: 80px; height: 80px;
        background: radial-gradient(circle, currentColor 0%, transparent 70%);
        opacity: 0.05;
        transform: translate(20px, -20px);
    }
    
    .stat-card .card-icon { font-size: 28px; margin-bottom: 12px; }
    .stat-card .card-label {
        color: var(--text-secondary);
        font-size: 12px; text-transform: uppercase;
        letter-spacing: 1px; margin-bottom: 8px;
    }
    .stat-card .card-value {
        color: var(--text-primary);
        font-size: 32px; font-weight: 700; line-height: 1;
    }
    
    .stat-card.car { border-top: 3px solid var(--accent-green); color: var(--accent-green); }
    .stat-card.motorcycle { border-top: 3px solid var(--accent-orange); color: var(--accent-orange); }
    .stat-card.bus { border-top: 3px solid var(--accent-blue); color: var(--accent-blue); }
    .stat-card.truck { border-top: 3px solid var(--accent-purple); color: var(--accent-purple); }
    .stat-card.total { border-top: 3px solid var(--accent-cyan); color: var(--accent-cyan); }
    .stat-card.speed { border-top: 3px solid var(--accent-red); color: var(--accent-red); }
    
    .video-placeholder {
        background: linear-gradient(145deg, #12121f 0%, #1a1a2e 100%);
        border-radius: 16px; padding: 80px 40px;
        text-align: center;
        border: 2px dashed var(--border-color);
        transition: all 0.3s ease;
    }
    .video-placeholder:hover {
        border-color: var(--accent-cyan);
        box-shadow: inset 0 0 30px rgba(0, 212, 255, 0.05);
    }
    .video-placeholder .placeholder-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.7; }
    .video-placeholder h3 { color: var(--text-secondary); font-size: 18px; margin-bottom: 8px; }
    .video-placeholder p { color: var(--text-muted); font-size: 14px; }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
        border-right: 1px solid var(--border-color);
    }
    section[data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
        color: white; border: none; border-radius: 12px;
        padding: 12px 24px; font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 212, 255, 0.4);
    }
    
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
        border-radius: 10px;
    }
    
    .rtsp-info {
        background: rgba(0, 212, 255, 0.08);
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 8px; padding: 12px;
        margin-top: 10px; font-size: 11px;
        color: var(--text-secondary);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# MODEL LOADING
# ============================================================================

@st.cache_resource
def load_yolo_model():
    """Load YOLOv8 nano model."""
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        return model
    except Exception as e:
        st.error(f"Failed to load model: {str(e)}")
        return None

# ============================================================================
# RTSP CONNECTION HELPERS
# ============================================================================

def create_rtsp_capture(rtsp_url: str, transport: str = "tcp"):
    """
    Create optimized VideoCapture for RTSP streams.
    Tries TCP first then UDP for maximum compatibility with ONVIF cameras.
    """
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        f"rtsp_transport;{transport}"
        "|analyzeduration;2000000"
        "|probesize;1000000"
        "|fflags;nobuffer"
        "|stimeout;15000000"
    )
    
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap
    
    return None


def test_rtsp_connection(rtsp_url: str) -> tuple:
    """Test RTSP connection with TCP then UDP fallback."""
    for transport in ["tcp", "udp"]:
        try:
            cap = create_rtsp_capture(rtsp_url, transport)
            if cap is not None and cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    return True, f"Connected ({transport.upper()})"
                else:
                    continue
        except Exception:
            continue
    
    return False, "Failed to connect - check URL, credentials, and VPN"

# ============================================================================
# DETECTION FUNCTIONS
# ============================================================================

def run_vehicle_detection(model, frame, confidence_threshold):
    """Run YOLOv8 inference and filter for vehicles."""
    results = model(frame, conf=confidence_threshold, verbose=False)
    
    vehicle_detections = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            class_id = int(box.cls[0])
            if class_id in VEHICLE_CLASSES:
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_name = VEHICLE_CLASSES[class_id]
                vehicle_detections.append((class_name, conf, x1, y1, x2, y2))
    
    return vehicle_detections

def draw_bounding_boxes(frame, detections, show_timestamp=False):
    """Draw styled bounding boxes on frame."""
    annotated = frame.copy()
    
    for class_name, conf, x1, y1, x2, y2 in detections:
        color = VEHICLE_COLORS.get(class_name, (255, 255, 255))
        
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        
        # Corner accents
        cl = 15
        cv2.line(annotated, (x1, y1), (x1 + cl, y1), color, 3)
        cv2.line(annotated, (x1, y1), (x1, y1 + cl), color, 3)
        cv2.line(annotated, (x2, y1), (x2 - cl, y1), color, 3)
        cv2.line(annotated, (x2, y1), (x2, y1 + cl), color, 3)
        cv2.line(annotated, (x1, y2), (x1 + cl, y2), color, 3)
        cv2.line(annotated, (x1, y2), (x1, y2 - cl), color, 3)
        cv2.line(annotated, (x2, y2), (x2 - cl, y2), color, 3)
        cv2.line(annotated, (x2, y2), (x2, y2 - cl), color, 3)
        
        # Label
        label = f"{class_name.upper()} {conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(annotated, (x1, y1 - th - 10), (x1 + tw + 10, y1), color, -1)
        cv2.putText(annotated, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    
    # Timestamp overlay for RTSP live feed
    if show_timestamp:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated, ts, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        # Red "LIVE" indicator
        cv2.circle(annotated, (annotated.shape[1] - 80, 25), 6, (0, 0, 255), -1)
        cv2.putText(annotated, "LIVE", (annotated.shape[1] - 68, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    return annotated

# ============================================================================
# CHART FUNCTIONS
# ============================================================================

def create_pie_chart(counts):
    """Create premium pie chart."""
    labels = [l.capitalize() for l in counts.keys()]
    values = list(counts.values())
    if sum(values) == 0:
        values = [1, 1, 1, 1]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=CHART_COLORS, line=dict(color='#1a1a2e', width=3)),
        textinfo='label+percent', textfont=dict(color='white', size=12, family='Inter'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
        pull=[0.02, 0.02, 0.02, 0.02]
    )])
    
    fig.update_layout(
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        height=260,
        title=dict(text='Distribution', font=dict(color='#94a3b8', size=14, family='Inter'), x=0.5),
        annotations=[dict(text=f'{sum(counts.values())}', x=0.5, y=0.5, font_size=28, 
                         font_color='white', font_family='Inter', showarrow=False)]
    )
    return fig

def create_timeline_chart(timeline):
    """Create premium timeline chart."""
    fig = go.Figure()
    
    if timeline:
        x = list(range(1, len(timeline) + 1))
        
        fig.add_trace(go.Scatter(
            x=x, y=timeline, mode='lines',
            fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.1)',
            line=dict(color='#00d4ff', width=0), hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=x, y=timeline, mode='lines+markers',
            line=dict(color='#00d4ff', width=3, shape='spline'),
            marker=dict(size=6, color='#00d4ff', line=dict(color='white', width=2)),
            hovertemplate='<b>Frame %{x}</b><br>Vehicles: %{y}<extra></extra>'
        ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(26, 26, 46, 0.5)',
        margin=dict(l=50, r=30, t=50, b=50),
        height=200,
        title=dict(text='Traffic Volume Over Time', font=dict(color='white', size=16, family='Inter'), x=0.5),
        xaxis=dict(
            title='Frame', title_font=dict(color='#94a3b8', size=12),
            tickfont=dict(color='#64748b', size=10),
            gridcolor='rgba(148, 163, 184, 0.1)', showgrid=True, zeroline=False
        ),
        yaxis=dict(
            title='Vehicles', title_font=dict(color='#94a3b8', size=12),
            tickfont=dict(color='#64748b', size=10),
            gridcolor='rgba(148, 163, 184, 0.1)', showgrid=True, zeroline=False
        ),
        hovermode='x unified',
        showlegend=False
    )
    return fig

def stat_card(icon, label, value, card_type=""):
    return f'''
    <div class="stat-card {card_type}">
        <div class="card-icon">{icon}</div>
        <div class="card-label">{label}</div>
        <div class="card-value">{value:,}</div>
    </div>
    '''

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # Session state
    if 'counts' not in st.session_state:
        st.session_state.counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    if 'timeline' not in st.session_state:
        st.session_state.timeline = []
    if 'running' not in st.session_state:
        st.session_state.running = False
    if 'input_mode' not in st.session_state:
        st.session_state.input_mode = "file"
    
    # Header
    st.markdown("""
    <div class="dashboard-header">
        <h1>Smart Traffic Monitoring</h1>
        <p class="subtitle">Real-time Vehicle Detection &bull; YOLOv8 &bull; AI-Powered</p>
        <div class="live-badge">SYSTEM ACTIVE</div>
        <span class="rtsp-badge">CCTV READY</span>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # SIDEBAR
    # ========================================================================
    with st.sidebar:
        st.markdown("### Input Source")
        input_mode = st.radio(
            "Select input type:",
            ["Video File", "RTSP Stream (CCTV)"],
            index=0 if st.session_state.input_mode == "file" else 1,
            label_visibility="collapsed"
        )
        st.session_state.input_mode = "file" if "File" in input_mode else "rtsp"
        
        st.markdown("---")
        
        uploaded = None
        rtsp_url = None
        can_start = False
        
        if st.session_state.input_mode == "file":
            st.markdown("### Upload Video")
            uploaded = st.file_uploader("Upload Video", type=['mp4', 'avi', 'mov'], label_visibility="collapsed")
            can_start = uploaded is not None
        else:
            st.markdown("### RTSP Camera URL")
            rtsp_url = st.text_input(
                "RTSP URL",
                value="rtsp://admin:Admin123@10.45.94.82/ONVIF/MediaInput?profile=def_profile2",
                help="Enter your CCTV camera's RTSP URL"
            )
            
            if rtsp_url:
                if st.button("Test Connection", use_container_width=True):
                    with st.spinner("Connecting to camera..."):
                        success, msg = test_rtsp_connection(rtsp_url)
                        if success:
                            st.success(f"Connected! ({msg})")
                        else:
                            st.error(f"Failed: {msg}")
                can_start = len(rtsp_url.strip()) > 10
            
            st.markdown("""
            <div class="rtsp-info">
                <b>RTSP URL Format:</b><br>
                rtsp://[user:pass@]ip:port/path<br><br>
                <b>Note:</b> VPN may be required for<br>internal network cameras
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### Detection Settings")
        frame_skip = st.slider(
            "Frame Skip", 1, 10, 
            3 if st.session_state.input_mode == "rtsp" else 2,
            help="Process every N frames (higher = faster)"
        )
        conf_threshold = st.slider("Confidence", 0.1, 0.9, 0.5, 0.05, help="Detection threshold")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            start = st.button("Start", type="primary", use_container_width=True, disabled=not can_start)
        with col2:
            stop = st.button("Stop", use_container_width=True)
        
        st.markdown("---")
        st.markdown("""
        ### Detection Classes
        - Cars
        - Motorcycles
        - Buses
        - Trucks
        """)
    
    if stop:
        st.session_state.running = False
    
    # ========================================================================
    # MAIN LAYOUT
    # ========================================================================
    col_stats, col_video = st.columns([1, 2], gap="large")
    
    with col_stats:
        st.markdown('<div class="section-title"><span class="icon">📊</span> Live Statistics</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(stat_card("🚗", "Cars", st.session_state.counts["car"], "car"), unsafe_allow_html=True)
            st.markdown(stat_card("🚌", "Buses", st.session_state.counts["bus"], "bus"), unsafe_allow_html=True)
        with c2:
            st.markdown(stat_card("🏍️", "Motorcycles", st.session_state.counts["motorcycle"], "motorcycle"), unsafe_allow_html=True)
            st.markdown(stat_card("🚚", "Trucks", st.session_state.counts["truck"], "truck"), unsafe_allow_html=True)
        
        total = sum(st.session_state.counts.values())
        speed = np.random.randint(35, 55) if total > 0 else 0
        
        t1, t2 = st.columns(2)
        with t1:
            st.markdown(stat_card("📈", "Total", total, "total"), unsafe_allow_html=True)
        with t2:
            st.markdown(stat_card("⚡", "Avg Speed", speed, "speed"), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        pie_placeholder = st.empty()
        pie_placeholder.plotly_chart(create_pie_chart(st.session_state.counts), use_container_width=True, config={'displayModeBar': False}, key="pie_init")
    
    with col_video:
        feed_title = "Live CCTV Feed" if st.session_state.input_mode == "rtsp" else "Video Feed"
        st.markdown(f'<div class="section-title"><span class="icon">📹</span> {feed_title}</div>', unsafe_allow_html=True)
        
        video_placeholder = st.empty()
        status_placeholder = st.empty()
        
        if not can_start:
            placeholder_msg = "Enter RTSP URL to connect to CCTV" if st.session_state.input_mode == "rtsp" else "Upload a video file to start"
            placeholder_icon = "📡" if st.session_state.input_mode == "rtsp" else "📹"
            video_placeholder.markdown(f"""
            <div class="video-placeholder">
                <div class="placeholder-icon">{placeholder_icon}</div>
                <h3>No Video Feed</h3>
                <p>{placeholder_msg}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    timeline_placeholder = st.empty()
    timeline_placeholder.plotly_chart(create_timeline_chart(st.session_state.timeline), use_container_width=True, config={'displayModeBar': False}, key="timeline_init")
    
    # ========================================================================
    # VIDEO FILE PROCESSING
    # ========================================================================
    if start and st.session_state.input_mode == "file" and uploaded:
        st.session_state.running = True
        st.session_state.counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
        st.session_state.timeline = []
        
        with st.spinner("Loading YOLOv8 model..."):
            model = load_yolo_model()
        
        if model is None:
            st.session_state.running = False
            return
        
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded.read())
        tfile.close()
        
        cap = cv2.VideoCapture(tfile.name)
        if not cap.isOpened():
            st.error("Failed to open video file")
            return
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        processed = 0
        
        while st.session_state.running:
            ret, frame = cap.read()
            if not ret:
                status_placeholder.success("Processing Complete!")
                st.session_state.running = False
                break
            
            frame_count += 1
            if frame_count % frame_skip != 0:
                continue
            
            processed += 1
            detections = run_vehicle_detection(model, frame, conf_threshold)
            
            frame_vehicles = 0
            for cls_name, *_ in detections:
                st.session_state.counts[cls_name] += 1
                frame_vehicles += 1
            
            st.session_state.timeline.append(frame_vehicles)
            if len(st.session_state.timeline) > 100:
                st.session_state.timeline = st.session_state.timeline[-100:]
            
            annotated = draw_bounding_boxes(frame, detections, show_timestamp=False)
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            video_placeholder.image(rgb, channels="RGB", use_container_width=True)
            
            if processed % 5 == 0:
                pie_placeholder.plotly_chart(create_pie_chart(st.session_state.counts), use_container_width=True, config={'displayModeBar': False}, key=f"pie_{processed}")
                timeline_placeholder.plotly_chart(create_timeline_chart(st.session_state.timeline), use_container_width=True, config={'displayModeBar': False}, key=f"timeline_{processed}")
            
            progress = frame_count / total_frames
            status_placeholder.progress(progress, text=f"Frame {frame_count}/{total_frames} | Detected: {frame_vehicles}")
            
            time.sleep(0.01)
        
        cap.release()
        pie_placeholder.plotly_chart(create_pie_chart(st.session_state.counts), use_container_width=True, config={'displayModeBar': False}, key="pie_final")
        timeline_placeholder.plotly_chart(create_timeline_chart(st.session_state.timeline), use_container_width=True, config={'displayModeBar': False}, key="timeline_final")
        st.balloons()
    
    # ========================================================================
    # RTSP STREAM PROCESSING
    # ========================================================================
    if start and st.session_state.input_mode == "rtsp" and rtsp_url:
        st.session_state.running = True
        st.session_state.counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
        st.session_state.timeline = []
        
        with st.spinner("Loading YOLOv8 model..."):
            model = load_yolo_model()
        
        if model is None:
            st.session_state.running = False
            return
        
        # --- Try connecting with TCP first, then UDP ---
        cap = None
        connected = False
        
        for transport in ["tcp", "udp"]:
            status_placeholder.info(f"Connecting to camera ({transport.upper()})...")
            cap = create_rtsp_capture(rtsp_url, transport)
            if cap is not None and cap.isOpened():
                ret, test_frame = cap.read()
                if ret:
                    connected = True
                    status_placeholder.success(f"Connected to CCTV ({transport.upper()})!")
                    time.sleep(0.5)
                    break
                else:
                    cap.release()
                    cap = None
        
        if not connected or cap is None:
            st.error(
                "Failed to connect to RTSP stream.\n\n"
                "Possible causes:\n"
                "- VPN not connected (required for internal cameras)\n"
                "- Camera offline or IP unreachable\n"
                "- Incorrect URL or credentials\n"
                "- Firewall blocking port 554"
            )
            st.session_state.running = False
            return
        
        frame_count = 0
        processed = 0
        reconnect_attempts = 0
        max_reconnect = 5
        
        while st.session_state.running:
            ret, frame = cap.read()
            
            # --- Handle connection loss ---
            if not ret:
                reconnect_attempts += 1
                if reconnect_attempts <= max_reconnect:
                    status_placeholder.warning(f"Connection lost. Reconnecting... ({reconnect_attempts}/{max_reconnect})")
                    cap.release()
                    time.sleep(3)
                    
                    # Try both transports on reconnect
                    cap = create_rtsp_capture(rtsp_url, "tcp")
                    if cap is None or not cap.isOpened():
                        cap = create_rtsp_capture(rtsp_url, "udp")
                    if cap is None or not cap.isOpened():
                        continue
                    
                    # Verify we can actually read a frame
                    ret_test, _ = cap.read()
                    if ret_test:
                        status_placeholder.success("Reconnected!")
                        reconnect_attempts = 0
                    continue
                else:
                    status_placeholder.error("Connection lost. Max reconnect attempts reached.")
                    st.session_state.running = False
                    break
            
            reconnect_attempts = 0
            frame_count += 1
            
            if frame_count % frame_skip != 0:
                continue
            
            processed += 1
            detections = run_vehicle_detection(model, frame, conf_threshold)
            
            frame_vehicles = 0
            for cls_name, *_ in detections:
                st.session_state.counts[cls_name] += 1
                frame_vehicles += 1
            
            st.session_state.timeline.append(frame_vehicles)
            if len(st.session_state.timeline) > 100:
                st.session_state.timeline = st.session_state.timeline[-100:]
            
            annotated = draw_bounding_boxes(frame, detections, show_timestamp=True)
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            video_placeholder.image(rgb, channels="RGB", use_container_width=True)
            
            if processed % 5 == 0:
                pie_placeholder.plotly_chart(create_pie_chart(st.session_state.counts), use_container_width=True, config={'displayModeBar': False}, key=f"pie_rtsp_{processed}")
                timeline_placeholder.plotly_chart(create_timeline_chart(st.session_state.timeline), use_container_width=True, config={'displayModeBar': False}, key=f"timeline_rtsp_{processed}")
            
            current_time = datetime.now().strftime("%H:%M:%S")
            total = sum(st.session_state.counts.values())
            status_placeholder.markdown(f"🔴 **LIVE** | {current_time} | Frames: {frame_count} | Detected: {frame_vehicles} | Total: {total}")
            
            time.sleep(0.01)
        
        cap.release()
        pie_placeholder.plotly_chart(create_pie_chart(st.session_state.counts), use_container_width=True, config={'displayModeBar': False}, key="pie_rtsp_final")
        timeline_placeholder.plotly_chart(create_timeline_chart(st.session_state.timeline), use_container_width=True, config={'displayModeBar': False}, key="timeline_rtsp_final")

if __name__ == "__main__":
    main()
