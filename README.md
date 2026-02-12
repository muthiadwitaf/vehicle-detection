# 🚗 Vehicle Detection Dashboard 2.0

A modern, real-time vehicle detection and tracking dashboard using **YOLOv10**, **FastAPI**, and **Vue.js 3**.

<img width="1722" height="1408" alt="image" src="https://github.com/user-attachments/assets/2b8fc225-e22a-4370-b8fe-f42aa6b1e98f" />


## 🚀 Features

- **🌐 Modern Web UI**: Fast and reactive dashboard built with Vue.js 3 and Vite.
- **⚡ High-Performance Backend**: FastAPI-powered engine for real-time video processing.
- **🏎️ YOLOv10 Detection**: State-of-the-art vehicle detection with adjustable precision (Low, Med, High).
- **🛰️ Multi-Source Support**: Stream from **RTSP (CCTV)**, local video files, or webcams.
- **📊 Advanced Analytics**: Real-time charts for traffic volume and vehicle distribution.
- **🗄️ Database Integration**: PostgreSQL persistence for vehicle counts.
- **📺 Cinematic Mode**: Interactive expanded video view with glassmorphism effects.

## 🏗️ Project Structure

- `backend/`: FastAPI server, YOLOv10 logic, and Database module.
- `frontend/`: Vue.js 3 application (Vite).

## 🛠️ Requirements

- **Python**: 3.9+
- **Node.js**: 18+ (for frontend development)
- **PostgreSQL**: Local or remote instance
- **GPU (Optional)**: CUDA recommended for High Precision mode, otherwise runs on CPU.

## 📦 Installation

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env      # Update with your PostgreSQL credentials
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

## 🚦 Usage

### Running Locally

1. **Start the Backend**:
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open **http://localhost:5173** in your browser.

## 🛠️ Tech Stack

- **Detection**: YOLOv10 (via Ultralytics)
- **Backend**: FastAPI / WebSocket / OpenCV
- **Frontend**: Vue.js 3 / Pinia / Chart.js
- **Database**: PostgreSQL / Psycopg2
- **Styling**: Vanilla CSS (Glassmorphism design)

## 📜 License

MIT License
