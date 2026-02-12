/**
 * useDetection.js — WebSocket + REST API composable for vehicle detection
 */
import { ref, reactive, onUnmounted } from 'vue'

const API_BASE = '' // Uses Vite proxy in dev

export function useDetection() {
    // State
    const isConnected = ref(false)
    const isRunning = ref(false)
    const sourceType = ref(null) // 'file' | 'rtsp' | 'webcam'
    const currentFrame = ref(null)
    const frameCount = ref(0)
    const frameVehicles = ref(0)
    const totalFrames = ref(0)
    const statusMessage = ref('')
    const statusType = ref('info') // 'info' | 'success' | 'error' | 'warning'

    const counts = reactive({
        car: 0,
        motorcycle: 0,
        bus: 0,
        truck: 0
    })

    const timeline = ref([])
    const cameras = ref([]) // Available webcams
    const cameraPresets = ref([]) // Preset RTSP cameras
    const trackingData = ref([])
    const trackingStats = ref({
        active_tracks: 0,
        avg_speed: 0,
        direction_distribution: {}
    })

    let ws = null
    const frameSkip = ref(2)
    const confidence = ref(0.5)
    const precision = ref('low')

    // ======== WebSocket Connection ========

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = window.location.host
        ws = new WebSocket(`${protocol}//${host}/ws/video`)

        ws.onopen = () => {
            isConnected.value = true
            sendConfig()
        }

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)

                if (data.error) {
                    statusMessage.value = data.error
                    statusType.value = 'error'
                    return
                }

                if (data.status === 'stopped') {
                    isRunning.value = false
                    statusMessage.value = 'Processing stopped'
                    statusType.value = 'info'
                    return
                }

                if (data.status === 'complete') {
                    isRunning.value = false
                    statusMessage.value = 'Processing complete!'
                    statusType.value = 'success'
                    if (data.counts) Object.assign(counts, data.counts)
                    return
                }

                // Normal frame update
                if (data.frame) {
                    currentFrame.value = 'data:image/jpeg;base64,' + data.frame
                }
                if (data.counts) Object.assign(counts, data.counts)
                if (data.timeline) timeline.value = data.timeline
                if (data.frame_count !== undefined) frameCount.value = data.frame_count
                if (data.frame_vehicles !== undefined) frameVehicles.value = data.frame_vehicles
                if (data.source_type) sourceType.value = data.source_type

                // Tracking info
                if (data.tracking_data) trackingData.value = data.tracking_data
                if (data.tracking_stats) Object.assign(trackingStats.value, data.tracking_stats)

            } catch (e) {
                console.error('WebSocket message error:', e)
            }
        }

        ws.onclose = () => {
            isConnected.value = false
            // Reconnect after 2 seconds
            setTimeout(() => {
                if (isRunning.value) connectWebSocket()
            }, 2000)
        }

        ws.onerror = () => {
            statusMessage.value = 'WebSocket connection error'
            statusType.value = 'error'
        }
    }

    function sendConfig() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                frame_skip: frameSkip.value,
                confidence: confidence.value,
                precision: precision.value
            }))
        }
    }

    // ======== REST API Calls ========

    async function startFile(file) {
        resetStats()
        const formData = new FormData()
        formData.append('video', file)

        try {
            statusMessage.value = 'Uploading and starting...'
            statusType.value = 'info'

            const res = await fetch(`${API_BASE}/api/start/file`, {
                method: 'POST',
                body: formData
            })
            const data = await res.json()

            if (res.ok) {
                sourceType.value = 'file'
                totalFrames.value = data.total_frames || 0
                isRunning.value = true
                statusMessage.value = 'Processing started!'
                statusType.value = 'success'
                connectWebSocket()
            } else {
                statusMessage.value = data.error || 'Failed to start'
                statusType.value = 'error'
            }
        } catch (err) {
            statusMessage.value = 'Error: ' + err.message
            statusType.value = 'error'
        }
    }

    async function startRtsp(url, cameraId = null, cameraName = null) {
        resetStats()
        const formData = new FormData()
        formData.append('url', url)
        if (cameraId) {
            formData.append('camera_id', cameraId)
            formData.append('camera_name', cameraName || cameraId)
        }

        try {
            statusMessage.value = 'Connecting to camera...'
            statusType.value = 'info'

            const res = await fetch(`${API_BASE}/api/start/rtsp`, {
                method: 'POST',
                body: formData
            })
            const data = await res.json()

            if (res.ok) {
                sourceType.value = 'rtsp'
                isRunning.value = true

                // Apply resumed counts if available
                if (data.resumed && data.counts) {
                    Object.assign(counts, data.counts)
                    statusMessage.value = `Connected (${data.transport}) - Resumed from last session`
                } else {
                    statusMessage.value = `Connected (${data.transport})!`
                }

                statusType.value = 'success'
                connectWebSocket()
            } else {
                statusMessage.value = data.error || 'Failed to connect'
                statusType.value = 'error'
            }
        } catch (err) {
            statusMessage.value = 'Error: ' + err.message
            statusType.value = 'error'
        }
    }

    async function stopProcessing() {
        try {
            await fetch(`${API_BASE}/api/stop`, { method: 'POST' })
            isRunning.value = false
            statusMessage.value = 'Stopped'
            statusType.value = 'info'
            if (ws) {
                ws.send(JSON.stringify({ command: 'stop' }))
            }
        } catch (err) {
            console.error('Stop error:', err)
        }
    }

    async function testRtsp(url) {
        const formData = new FormData()
        formData.append('url', url)

        try {
            statusMessage.value = 'Testing connection...'
            statusType.value = 'info'

            const res = await fetch(`${API_BASE}/api/test-rtsp`, {
                method: 'POST',
                body: formData
            })
            const data = await res.json()

            if (data.success) {
                statusMessage.value = `Connected (${data.transport})!`
                statusType.value = 'success'
                return true
            } else {
                statusMessage.value = data.error || 'Connection failed'
                statusType.value = 'error'
                return false
            }
        } catch (err) {
            statusMessage.value = 'Error: ' + err.message
            statusType.value = 'error'
            return false
        }
    }

    async function scanCameras() {
        try {
            statusMessage.value = 'Scanning cameras...'
            statusType.value = 'info'

            const res = await fetch(`${API_BASE}/api/cameras`)
            const data = await res.json()
            cameras.value = data.cameras || []

            if (cameras.value.length === 0) {
                statusMessage.value = 'No cameras found'
                statusType.value = 'warning'
            } else {
                statusMessage.value = `Found ${cameras.value.length} camera(s)`
                statusType.value = 'success'
            }
            return cameras.value
        } catch (err) {
            statusMessage.value = 'Error scanning: ' + err.message
            statusType.value = 'error'
            return []
        }
    }

    async function startWebcam(cameraIndex) {
        resetStats()
        const formData = new FormData()
        formData.append('index', cameraIndex)

        try {
            statusMessage.value = 'Opening camera...'
            statusType.value = 'info'

            const res = await fetch(`${API_BASE}/api/start/webcam`, {
                method: 'POST',
                body: formData
            })
            const data = await res.json()

            if (res.ok) {
                sourceType.value = 'webcam'
                isRunning.value = true
                statusMessage.value = `Camera ${cameraIndex} active (${data.width}x${data.height})`
                statusType.value = 'success'
                connectWebSocket()
            } else {
                statusMessage.value = data.error || 'Failed to open camera'
                statusType.value = 'error'
            }
        } catch (err) {
            statusMessage.value = 'Error: ' + err.message
            statusType.value = 'error'
        }
    }

    async function loadCameraPresets() {
        try {
            const res = await fetch(`${API_BASE}/api/camera-presets`)
            const data = await res.json()
            cameraPresets.value = data.cameras || []
            return cameraPresets.value
        } catch (err) {
            console.error('Failed to load camera presets:', err)
            return []
        }
    }

    function updateSettings(skip, conf, prec) {
        frameSkip.value = skip
        confidence.value = conf
        if (prec) precision.value = prec
        sendConfig()
    }

    function resetStats() {
        counts.car = 0
        counts.motorcycle = 0
        counts.bus = 0
        counts.truck = 0
        timeline.value = []
        frameCount.value = 0
        frameVehicles.value = 0
        currentFrame.value = null
    }

    // Cleanup
    onUnmounted(() => {
        if (ws) ws.close()
    })

    return {
        // State
        isConnected,
        isRunning,
        sourceType,
        currentFrame,
        frameCount,
        frameVehicles,
        totalFrames,
        statusMessage,
        statusType,
        counts,
        timeline,
        cameras,
        cameraPresets,
        trackingData,
        trackingStats,
        precision, // Added precision to exported state
        // Actions
        startFile,
        startRtsp,
        startWebcam,
        stopProcessing,
        testRtsp,
        scanCameras,
        loadCameraPresets,
        updateSettings,
        resetStats,
    }
}
