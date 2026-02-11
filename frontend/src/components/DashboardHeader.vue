<template>
  <div class="dashboard-header">
    <h1>Smart Traffic Monitoring</h1>
    <p class="header-subtitle">Real-time Vehicle Detection &bull; YOLOv10 &bull; AI-Powered</p>
    <div class="header-badges">
      <span class="badge badge--active">
        <span class="badge-dot"></span>
        SYSTEM ACTIVE
      </span>
      <span v-if="showCctv" class="badge badge--cctv">
        <span class="badge-dot"></span>
        CCTV LIVE
      </span>

      <!-- Theme Toggle -->
      <button class="theme-toggle" @click="toggleTheme" :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'">
        <span class="theme-toggle__icon">{{ isDark ? '🌙' : '☀️' }}</span>
        {{ isDark ? 'Dark' : 'Light' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { useTheme } from '../composables/useTheme.js'

defineProps({
  showCctv: { type: Boolean, default: false }
})

const { isDark, toggleTheme } = useTheme()
</script>
