"""
Dashboard UI Components
========================
Streamlit dashboard UI layout and chart components for vehicle detection.
This module provides reusable UI components - backend logic is handled separately.

Usage:
    from ui_components import DashboardUI
    
    ui = DashboardUI()
    ui.render_header()
    placeholders = ui.render_main_layout(vehicle_counts)
    ui.update_charts(placeholders, vehicle_counts, timeline_data)
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# ============================================================================
# CONFIGURATION
# ============================================================================

# Color palette for vehicle types
COLORS = {
    "car": {"hex": "#00ff00", "name": "Green"},
    "motorcycle": {"hex": "#ffa500", "name": "Orange"},
    "bus": {"hex": "#0066ff", "name": "Blue"},
    "truck": {"hex": "#9933ff", "name": "Purple"},
    "total": {"hex": "#00d4ff", "name": "Cyan"},
    "speed": {"hex": "#ff6b6b", "name": "Red"}
}

# ============================================================================
# PAGE SETUP (Call this first in your main app)
# ============================================================================

def setup_page():
    """
    Configure Streamlit page settings.
    Must be called before any other Streamlit commands.
    """
    st.set_page_config(
        page_title="🚗 Traffic Monitoring Dashboard",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )

# ============================================================================
# DARK THEME CSS
# ============================================================================

DARK_THEME_CSS = """
<style>
    /* ===== GLOBAL DARK THEME ===== */
    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #12121a 100%);
    }
    
    /* ===== HEADER STYLES ===== */
    .dashboard-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #1a1a2e 100%);
        padding: 25px 30px;
        border-radius: 16px;
        margin-bottom: 25px;
        text-align: center;
        border: 1px solid rgba(0, 212, 255, 0.2);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4),
                    0 0 60px rgba(0, 212, 255, 0.05);
    }
    
    .dashboard-header h1 {
        color: #00d4ff;
        margin: 0;
        font-size: 32px;
        font-weight: 700;
        letter-spacing: 1px;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
    }
    
    .dashboard-header .subtitle {
        color: #8b9dc3;
        margin: 8px 0 0 0;
        font-size: 14px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    
    .dashboard-header .status-badge {
        display: inline-block;
        background: rgba(0, 255, 136, 0.15);
        color: #00ff88;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        margin-top: 10px;
        border: 1px solid rgba(0, 255, 136, 0.3);
    }
    
    /* ===== STAT CARD STYLES ===== */
    .stat-card {
        background: linear-gradient(145deg, #1e2130 0%, #252a3d 100%);
        border-radius: 14px;
        padding: 18px 15px;
        text-align: center;
        border: 1px solid rgba(61, 68, 102, 0.5);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 12px;
    }
    
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0, 0, 0, 0.4);
    }
    
    .stat-card .icon {
        font-size: 24px;
        margin-bottom: 5px;
    }
    
    .stat-card .label {
        color: #8b9dc3;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 6px;
    }
    
    .stat-card .value {
        color: #ffffff;
        font-size: 28px;
        font-weight: 700;
        line-height: 1;
    }
    
    /* Colored accent borders */
    .stat-card.car { border-left: 4px solid #00ff00; }
    .stat-card.motorcycle { border-left: 4px solid #ffa500; }
    .stat-card.bus { border-left: 4px solid #0066ff; }
    .stat-card.truck { border-left: 4px solid #9933ff; }
    .stat-card.total { border-left: 4px solid #00d4ff; }
    .stat-card.speed { border-left: 4px solid #ff6b6b; }
    
    /* ===== SECTION HEADER STYLES ===== */
    .section-header {
        color: #00d4ff;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(61, 68, 102, 0.5);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* ===== VIDEO CONTAINER STYLES ===== */
    .video-container {
        background: linear-gradient(145deg, #1e2130 0%, #252a3d 100%);
        border-radius: 14px;
        padding: 15px;
        border: 1px solid rgba(61, 68, 102, 0.5);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    
    .video-placeholder {
        background: linear-gradient(135deg, #151820 0%, #1a1f2e 100%);
        border-radius: 10px;
        padding: 100px 40px;
        text-align: center;
        border: 2px dashed rgba(61, 68, 102, 0.5);
    }
    
    .video-placeholder h2 {
        color: #8b9dc3;
        margin-bottom: 10px;
        font-size: 20px;
    }
    
    .video-placeholder p {
        color: #5a6384;
        font-size: 14px;
    }
    
    /* ===== CHART CONTAINER STYLES ===== */
    .chart-container {
        background: linear-gradient(145deg, #1e2130 0%, #252a3d 100%);
        border-radius: 14px;
        padding: 15px;
        border: 1px solid rgba(61, 68, 102, 0.5);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        margin-top: 20px;
    }
    
    /* ===== HIDE STREAMLIT DEFAULTS ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
</style>
"""

def inject_css():
    """Inject custom dark theme CSS into the page."""
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

# ============================================================================
# HEADER COMPONENT
# ============================================================================

def render_header(title: str = "Traffic Monitoring Dashboard", 
                  subtitle: str = "Real-time Vehicle Detection • YOLO-NAS • CPU Inference",
                  show_status: bool = True):
    """
    Render the dashboard header with title, subtitle, and status badge.
    
    Args:
        title: Main dashboard title
        subtitle: Descriptive subtitle text
        show_status: Whether to show the "LIVE" status badge
    """
    status_html = '<span class="status-badge">● LIVE</span>' if show_status else ''
    
    st.markdown(f"""
    <div class="dashboard-header">
        <h1>🚗 {title}</h1>
        <p class="subtitle">{subtitle}</p>
        {status_html}
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# STAT CARD COMPONENT
# ============================================================================

def render_stat_card(icon: str, label: str, value: int, card_type: str = "") -> str:
    """
    Generate HTML for a styled KPI stat card.
    
    Args:
        icon: Emoji icon for the card
        label: Text label (e.g., "Cars")
        value: Numeric value to display
        card_type: CSS class for color accent (car, motorcycle, bus, truck, total, speed)
    
    Returns:
        HTML string for the stat card
    """
    return f"""
    <div class="stat-card {card_type}">
        <div class="icon">{icon}</div>
        <div class="label">{label}</div>
        <div class="value">{value:,}</div>
    </div>
    """

def render_stat_cards_grid(vehicle_counts: Dict[str, int], avg_speed: int = 0):
    """
    Render a 2x3 grid of stat cards for vehicle counts.
    
    Args:
        vehicle_counts: Dict with keys: car, motorcycle, bus, truck
        avg_speed: Mocked average speed value
    """
    total = sum(vehicle_counts.values())
    
    # Row 1: Car and Motorcycle
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(render_stat_card("🚗", "Cars", vehicle_counts.get("car", 0), "car"), unsafe_allow_html=True)
    with col2:
        st.markdown(render_stat_card("🏍️", "Motorcycles", vehicle_counts.get("motorcycle", 0), "motorcycle"), unsafe_allow_html=True)
    
    # Row 2: Bus and Truck
    col3, col4 = st.columns(2)
    with col3:
        st.markdown(render_stat_card("🚌", "Buses", vehicle_counts.get("bus", 0), "bus"), unsafe_allow_html=True)
    with col4:
        st.markdown(render_stat_card("🚚", "Trucks", vehicle_counts.get("truck", 0), "truck"), unsafe_allow_html=True)
    
    # Row 3: Total and Speed
    col5, col6 = st.columns(2)
    with col5:
        st.markdown(render_stat_card("📊", "Total", total, "total"), unsafe_allow_html=True)
    with col6:
        st.markdown(render_stat_card("⚡", "Avg km/h", avg_speed, "speed"), unsafe_allow_html=True)

# ============================================================================
# CHART COMPONENTS
# ============================================================================

def create_distribution_chart(vehicle_counts: Dict[str, int], chart_type: str = "pie") -> go.Figure:
    """
    Create a vehicle distribution chart (pie or bar).
    
    Args:
        vehicle_counts: Dict mapping vehicle type to count
        chart_type: "pie" for donut chart, "bar" for bar chart
    
    Returns:
        Plotly Figure object
    """
    labels = list(vehicle_counts.keys())
    values = list(vehicle_counts.values())
    colors = [COLORS[label]["hex"] for label in labels]
    
    # Use placeholder values if no data
    if sum(values) == 0:
        values = [1] * len(labels)
    
    if chart_type == "bar":
        # Bar chart version
        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=values,
            textposition='outside',
            textfont=dict(color='white', size=12)
        )])
        
        fig.update_layout(
            title=dict(text="Vehicle Distribution", font=dict(color='#8b9dc3', size=14), x=0.5),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,33,48,0.8)',
            margin=dict(l=20, r=20, t=50, b=40),
            height=220,
            xaxis=dict(
                tickfont=dict(color='#8b9dc3'),
                gridcolor='rgba(61,68,102,0.3)'
            ),
            yaxis=dict(
                tickfont=dict(color='#8b9dc3'),
                gridcolor='rgba(61,68,102,0.3)',
                showgrid=True
            )
        )
    else:
        # Pie/Donut chart version
        fig = go.Figure(data=[go.Pie(
            labels=[l.capitalize() for l in labels],
            values=values,
            hole=0.45,
            marker=dict(colors=colors, line=dict(color='#1e2130', width=2)),
            textinfo='label+percent',
            textfont=dict(color='white', size=11),
            hovertemplate='%{label}: %{value}<extra></extra>',
            pull=[0.02] * len(labels)  # Slight pull for 3D effect
        )])
        
        fig.update_layout(
            title=dict(text="Vehicle Distribution", font=dict(color='#8b9dc3', size=14), x=0.5),
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=50, b=10),
            height=220
        )
    
    return fig

def create_timeline_chart(timeline_data: List[int], 
                          title: str = "Traffic Volume Over Time") -> go.Figure:
    """
    Create a line chart showing traffic volume over processed frames.
    
    Args:
        timeline_data: List of vehicle counts per frame
        title: Chart title
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    if timeline_data:
        x_values = list(range(1, len(timeline_data) + 1))
        
        # Main line trace with gradient fill
        fig.add_trace(go.Scatter(
            x=x_values,
            y=timeline_data,
            mode='lines+markers',
            name='Vehicles',
            line=dict(color='#00d4ff', width=2.5, shape='spline'),
            marker=dict(size=5, color='#00d4ff', 
                       line=dict(color='white', width=1)),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.1)',
            hovertemplate='Frame %{x}<br>Vehicles: %{y}<extra></extra>'
        ))
        
        # Add moving average line if enough data
        if len(timeline_data) >= 5:
            window = 5
            moving_avg = []
            for i in range(len(timeline_data)):
                if i < window - 1:
                    moving_avg.append(None)
                else:
                    avg = sum(timeline_data[i-window+1:i+1]) / window
                    moving_avg.append(avg)
            
            fig.add_trace(go.Scatter(
                x=x_values,
                y=moving_avg,
                mode='lines',
                name='5-Frame Avg',
                line=dict(color='#ff6b6b', width=1.5, dash='dot'),
                hovertemplate='Avg: %{y:.1f}<extra></extra>'
            ))
    else:
        # Empty placeholder
        fig.add_trace(go.Scatter(x=[0], y=[0], mode='lines'))
    
    fig.update_layout(
        title=dict(
            text=f"📈 {title}",
            font=dict(color='white', size=16),
            x=0.5
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,33,48,0.8)',
        margin=dict(l=60, r=30, t=60, b=50),
        height=200,
        xaxis=dict(
            title="Processed Frame",
            title_font=dict(color='#8b9dc3', size=12),
            tickfont=dict(color='#8b9dc3'),
            gridcolor='rgba(61,68,102,0.3)',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title="Vehicles Detected",
            title_font=dict(color='#8b9dc3', size=12),
            tickfont=dict(color='#8b9dc3'),
            gridcolor='rgba(61,68,102,0.3)',
            showgrid=True,
            zeroline=False
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(color='#8b9dc3', size=10)
        ),
        hovermode='x unified'
    )
    
    return fig

# ============================================================================
# VIDEO PLACEHOLDER COMPONENT
# ============================================================================

def render_video_placeholder():
    """Render a placeholder UI when no video is loaded."""
    st.markdown("""
    <div class="video-placeholder">
        <h2>📹 No Video Feed</h2>
        <p>Upload a video file to start vehicle detection</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# MAIN LAYOUT COMPONENT
# ============================================================================

@dataclass
class DashboardPlaceholders:
    """Container for Streamlit placeholder elements for dynamic updates."""
    video: Any = None
    status: Any = None
    pie_chart: Any = None
    timeline_chart: Any = None
    stat_cards: Any = None

def render_main_layout(vehicle_counts: Optional[Dict[str, int]] = None,
                       avg_speed: int = 0) -> DashboardPlaceholders:
    """
    Render the complete dashboard layout with placeholders for dynamic content.
    
    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │                      HEADER                                  │
    ├───────────────────────┬─────────────────────────────────────┤
    │  STATS (6 cards)      │  VIDEO FEED                         │
    │  + PIE CHART          │  + STATUS BAR                       │
    ├───────────────────────┴─────────────────────────────────────┤
    │                   TIMELINE CHART                             │
    └─────────────────────────────────────────────────────────────┘
    
    Args:
        vehicle_counts: Initial vehicle counts (or None for zeros)
        avg_speed: Initial average speed value
    
    Returns:
        DashboardPlaceholders object with references to all placeholder elements
    """
    # Default counts if not provided
    if vehicle_counts is None:
        vehicle_counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    
    placeholders = DashboardPlaceholders()
    
    # Two-column layout: Stats (1) | Video (2)
    col_stats, col_video = st.columns([1, 2], gap="large")
    
    # ===== LEFT COLUMN: Statistics =====
    with col_stats:
        st.markdown('<p class="section-header">📊 Traffic Statistics</p>', unsafe_allow_html=True)
        
        # Stat cards section (can be updated via rerun)
        placeholders.stat_cards = st.container()
        with placeholders.stat_cards:
            render_stat_cards_grid(vehicle_counts, avg_speed)
        
        # Pie chart with placeholder for updates
        st.markdown("<br>", unsafe_allow_html=True)
        placeholders.pie_chart = st.empty()
        placeholders.pie_chart.plotly_chart(
            create_distribution_chart(vehicle_counts, chart_type="pie"),
            use_container_width=True,
            config={'displayModeBar': False}
        )
    
    # ===== RIGHT COLUMN: Video Feed =====
    with col_video:
        st.markdown('<p class="section-header">📹 Live Detection Feed</p>', unsafe_allow_html=True)
        
        # Video frame placeholder
        placeholders.video = st.empty()
        render_video_placeholder()
        
        # Status/progress bar placeholder
        placeholders.status = st.empty()
    
    # ===== BOTTOM: Timeline Chart =====
    st.markdown("<br>", unsafe_allow_html=True)
    
    placeholders.timeline_chart = st.empty()
    placeholders.timeline_chart.plotly_chart(
        create_timeline_chart([]),
        use_container_width=True,
        config={'displayModeBar': False}
    )
    
    return placeholders

def update_charts(placeholders: DashboardPlaceholders,
                  vehicle_counts: Dict[str, int],
                  timeline_data: List[int]):
    """
    Update chart placeholders with new data.
    
    Args:
        placeholders: DashboardPlaceholders object from render_main_layout
        vehicle_counts: Updated vehicle counts
        timeline_data: Updated timeline data
    """
    # Update pie chart
    placeholders.pie_chart.plotly_chart(
        create_distribution_chart(vehicle_counts, chart_type="pie"),
        use_container_width=True,
        config={'displayModeBar': False}
    )
    
    # Update timeline chart
    placeholders.timeline_chart.plotly_chart(
        create_timeline_chart(timeline_data),
        use_container_width=True,
        config={'displayModeBar': False}
    )

# ============================================================================
# DEMO / STANDALONE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Demo mode - run this file directly to see the UI without backend.
    Usage: streamlit run ui_components.py
    """
    import random
    import time
    
    # Setup page
    setup_page()
    inject_css()
    
    # Render header
    render_header()
    
    # Demo data
    demo_counts = {"car": 45, "motorcycle": 23, "bus": 8, "truck": 12}
    demo_timeline = [random.randint(0, 5) for _ in range(30)]
    
    # Render layout
    placeholders = render_main_layout(demo_counts, avg_speed=42)
    
    # Simulate updates button
    with st.sidebar:
        st.header("🎮 Demo Controls")
        if st.button("Simulate Detection"):
            for i in range(10):
                # Increment random vehicle type
                vehicle_type = random.choice(list(demo_counts.keys()))
                demo_counts[vehicle_type] += 1
                demo_timeline.append(random.randint(0, 5))
                
                # Update charts
                update_charts(placeholders, demo_counts, demo_timeline[-50:])
                time.sleep(0.3)
            
            st.success("Simulation complete!")
