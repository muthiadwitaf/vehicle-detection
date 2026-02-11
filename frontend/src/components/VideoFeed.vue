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
  progress: { type: Number, default: 0 }
})

const isExpanded = ref(false)

function toggleExpand() {
  isExpanded.value = !isExpanded.value
  if (isExpanded.value) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
}
</script>
