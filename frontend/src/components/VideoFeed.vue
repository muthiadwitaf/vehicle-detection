<template>
  <div :class="['video-wrapper', { 'video-wrapper--expanded': isExpanded }]">
    <div class="video-wrapper__header">
      <div class="video-wrapper__title">
        <span class="video-icon">{{ sourceType === 'rtsp' ? '📡' : '📹' }}</span>
        {{ sourceType === 'rtsp' ? 'Live CCTV Stream' : 'Video Analysis' }}
      </div>
      <button class="video-expand-btn" @click="toggleExpand" :title="isExpanded ? 'Minimize' : 'Expand'">
        {{ isExpanded ? '✕' : '⛶' }}
      </button>
    </div>

    <div class="video-feed">
      <img v-if="frame" :src="frame" alt="Video Feed" />
      <div v-else class="video-placeholder">
        <div class="video-placeholder__icon">{{ sourceType === 'rtsp' ? '📡' : '📹' }}</div>
        <h3>Feed Disconnected</h3>
        <p>{{ sourceType === 'rtsp' ? 'Attempting to establish RTSP link...' : 'Waiting for video file input' }}</p>
      </div>

      <!-- FPS / Latency Overlay -->
      <div v-if="isLive && frame" class="perf-overlay">
        <span class="perf-badge perf-badge--fps">{{ clientFps }} FPS</span>
        <span class="perf-badge perf-badge--server">Engine {{ serverFps }} FPS</span>
        <span class="perf-badge perf-badge--latency">{{ latencyMs }}ms</span>
        <span class="perf-badge perf-badge--infer">YOLO {{ inferMs }}ms</span>
      </div>

      <!-- Close button overlay for expanded mode -->
      <button v-if="isExpanded" class="video-close-overlay" @click="toggleExpand">
        Back to Dashboard ✕
      </button>
    </div>

    <!-- Status bar -->
    <div v-if="statusMsg && !isExpanded" :class="['video-status', `video-status--${statusClass}`]">
      <span v-if="isLive" class="live-dot"></span>
      {{ statusMsg }}
    </div>

    <!-- Progress bar -->
    <div v-if="progress > 0 && progress < 1" class="progress-bar-container">
      <div class="progress-bar__fill" :style="{ width: (progress * 100) + '%' }"></div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  frame: { type: String, default: null },
  sourceType: { type: String, default: null },
  statusMsg: { type: String, default: '' },
  statusClass: { type: String, default: 'info' },
  isLive: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  clientFps: { type: Number, default: 0 },
  serverFps: { type: Number, default: 0 },
  latencyMs: { type: Number, default: 0 },
  inferMs: { type: Number, default: 0 },
})

const isExpanded = ref(false)

function toggleExpand() {
  isExpanded.value = !isExpanded.value
  document.body.style.overflow = isExpanded.value ? 'hidden' : ''
}
</script>

<style scoped>
.perf-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
  z-index: 10;
  pointer-events: none;
}

.perf-badge {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  font-family: 'Inter', monospace;
  backdrop-filter: blur(8px);
  line-height: 1.2;
}

.perf-badge--fps {
  background: rgba(16, 185, 129, 0.85);
  color: #fff;
}

.perf-badge--server {
  background: rgba(59, 130, 246, 0.85);
  color: #fff;
}

.perf-badge--latency {
  background: rgba(245, 158, 11, 0.85);
  color: #fff;
}

.perf-badge--infer {
  background: rgba(139, 92, 246, 0.85);
  color: #fff;
}
</style>
