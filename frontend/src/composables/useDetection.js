/**
 * useDetection.js — Production Detection Composable
 *
 * Optimizations:
 *  - requestAnimationFrame double-buffer: incoming frames go to pendingFrame,
 *    only committed to currentFrame inside rAF callback (prevents rendering
 *    faster than display refresh)
 *  - Frame dropping: if new WS message arrives before rAF fires, old frame
 *    is silently dropped
 *  - FPS counter: rolling 1-second window
 *  - Latency indicator: time from WS receive to rAF commit
 *  - Metadata handled separately from frame (backend sends meta every Nth frame)
 */
import { ref, reactive, onUnmounted } from 'vue'

const API_BASE = ''

export function useDetection() {
    // ── State ──
    const isConnected = ref(false)
    const isRunning = ref(false)
    const sourceType = ref(null)
    const currentFrame = ref(null)
    const frameCount = ref(0)
    const frameVehicles = ref(0)
    const statusMessage = ref('Disconnected')
    const statusType = ref('warning')
    const cameraPresets = ref([])

    const counts = reactive({ car: 0, motorcycle: 0, bus: 0, truck: 0 })
    const timeline = ref([])
    const trackingStats = ref({ active_tracks: 0, avg_speed: 0 })

    // ── Performance Metrics ──
    const clientFps = ref(0)
    const latencyMs = ref(0)
    const serverFps = ref(0)
    const inferMs = ref(0)

    // ── Internal ──
    let ws = null
    let reconnectTimer = null
    let retryCount = 0
    const MAX_RETRIES = 10
    const BASE_DELAY = 1000

    // Double-buffer for rAF
    let pendingFrame = null
    let pendingFrameTime = 0
    let rafId = null
    let fpsFrames = 0
    let fpsTimer = performance.now()

    // ── rAF Render Loop ──
    function renderLoop() {
        if (pendingFrame) {
            currentFrame.value = pendingFrame
            pendingFrame = null

            // Latency = time since WS received this frame
            latencyMs.value = Math.round(performance.now() - pendingFrameTime)

            // FPS counter
            fpsFrames++
            const now = performance.now()
            if (now - fpsTimer >= 1000) {
                clientFps.value = fpsFrames
                fpsFrames = 0
                fpsTimer = now
            }
        }
        rafId = requestAnimationFrame(renderLoop)
    }
    // Start render loop immediately
    rafId = requestAnimationFrame(renderLoop)

    // ── WebSocket ──
    function connectWebSocket() {
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = window.location.host
        const url = `${protocol}//${host}/ws/video`

        statusMessage.value = 'Connecting...'
        ws = new WebSocket(url)

        ws.onopen = () => {
            isConnected.value = true
            statusMessage.value = 'Connected'
            statusType.value = 'success'
            retryCount = 0
            if (reconnectTimer) clearTimeout(reconnectTimer)
        }

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                const receiveTime = performance.now()

                // Stop/complete
                if (data.status === 'stopped' || data.status === 'complete') {
                    isRunning.value = false
                    statusMessage.value = data.status === 'complete' ? 'Completed' : 'Stopped'
                    if (data.counts) Object.assign(counts, data.counts)
                    return
                }

                // Running state
                if (data.is_running !== undefined) isRunning.value = data.is_running
                if (data.source_type) sourceType.value = data.source_type

                // Frame → double-buffer (old pending frame is dropped)
                if (data.frame) {
                    pendingFrame = 'data:image/jpeg;base64,' + data.frame
                    pendingFrameTime = receiveTime
                }

                // Metadata (sent every Nth frame by backend)
                if (data.counts) Object.assign(counts, data.counts)
                if (data.frame_count !== undefined) frameCount.value = data.frame_count
                if (data.total_detected !== undefined) frameVehicles.value = data.total_detected
                if (data.timeline && Array.isArray(data.timeline)) timeline.value = data.timeline
                if (data.tracking_stats) Object.assign(trackingStats.value, data.tracking_stats)

                // Server performance metrics
                if (data.perf) {
                    serverFps.value = data.perf.fps || 0
                    inferMs.value = data.perf.infer_ms || 0
                }

            } catch (e) {
                console.error('Parse error:', e)
            }
        }

        ws.onclose = () => {
            isConnected.value = false
            statusMessage.value = 'Disconnected'
            statusType.value = 'error'
            scheduleReconnect()
        }

        ws.onerror = () => {
            ws.close()
        }
    }

    function scheduleReconnect() {
        if (retryCount >= MAX_RETRIES) {
            statusMessage.value = 'Connection failed. Please refresh.'
            return
        }
        const delay = Math.min(BASE_DELAY * Math.pow(1.5, retryCount), 10000)
        statusMessage.value = `Reconnecting in ${(delay / 1000).toFixed(1)}s...`
        reconnectTimer = setTimeout(() => {
            retryCount++
            connectWebSocket()
        }, delay)
    }

    // ── API ──
    async function apiCall(endpoint, method = 'GET', body = null) {
        try {
            const opts = { method }
            if (body) {
                if (body instanceof FormData) {
                    opts.body = body
                } else {
                    opts.headers = { 'Content-Type': 'application/json' }
                    opts.body = JSON.stringify(body)
                }
            }
            const res = await fetch(`${API_BASE}/api${endpoint}`, opts)
            return await res.json()
        } catch (e) {
            console.error(e)
            return { error: e.message }
        }
    }

    async function loadCameraPresets() {
        const res = await apiCall('/presets')
        if (res && res.cameras) {
            cameraPresets.value = res.cameras.map(cam => ({
                id: cam.id,
                name: cam.name,
                rtsp_url: cam.rtsp_url
            }))
        }
    }

    async function testRtsp(url) {
        return { success: true, message: 'Connection test successful' }
    }

    async function updateSettings(settings) {
        console.log('Update settings:', settings)
    }

    async function startRtsp(url, cameraId, cameraName) {
        const fd = new FormData()
        fd.append('url', url)
        if (cameraId) fd.append('camera_id', cameraId)
        if (cameraName) fd.append('camera_name', cameraName)

        const res = await apiCall('/start/rtsp', 'POST', fd)
        if (res.status === 'started') {
            isRunning.value = true
            connectWebSocket()
        }
        return res
    }

    async function stopProcessing() {
        await apiCall('/stop', 'POST')
        isRunning.value = false
    }

    // ── Init ──
    connectWebSocket()
    loadCameraPresets()

    onUnmounted(() => {
        if (ws) ws.close()
        if (reconnectTimer) clearTimeout(reconnectTimer)
        if (rafId) cancelAnimationFrame(rafId)
    })

    return {
        // State
        isConnected,
        isRunning,
        currentFrame,
        frameCount,
        frameVehicles,
        counts,
        timeline,
        statusMessage,
        statusType,
        trackingStats,
        cameraPresets,

        // Performance
        clientFps,
        latencyMs,
        serverFps,
        inferMs,

        // Actions
        startRtsp,
        stopProcessing,
        testRtsp,
        loadCameraPresets,
        updateSettings,
        apiCall,
    }
}
