<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <Sidebar
      ref="sidebarRef"
      :is-running="detection.isRunning.value"
      :status-message="detection.statusMessage.value"
      :status-type="detection.statusType.value"
      :camera-presets="detection.cameraPresets.value"
      @start-rtsp="detection.startRtsp"
      @stop="detection.stopProcessing"
      @test-rtsp="detection.testRtsp"
      @load-presets="detection.loadCameraPresets"
      @settings-change="detection.updateSettings"
    />

    <!-- Main Content -->
    <main class="main-content">
      <DashboardHeader :show-cctv="detection.isRunning.value" />

      <!-- Stat Cards -->
      <div class="stats-grid">
        <StatCard icon="🚗" label="Cars" :value="detection.counts.car" type="car" />
        <StatCard icon="🏍️" label="Motorcycles" :value="detection.counts.motorcycle" type="motorcycle" />
        <StatCard icon="🚌" label="Buses" :value="detection.counts.bus" type="bus" />
        <StatCard icon="🚚" label="Trucks" :value="detection.counts.truck" type="truck" />
        <StatCard icon="📈" label="Total" :value="totalDetected" type="total" />
        <StatCard icon="📊" label="Frames" :value="detection.frameCount.value" type="fps" />
        <StatCard icon="⚡" label="Avg Speed" :value="detection.trackingStats.value.avg_speed" suffix=" km/h" type="speed" />
        <StatCard icon="🎯" label="Active" :value="detection.trackingStats.value.active_tracks" type="active" />
      </div>

      <!-- Video + Chart Grid -->
      <div class="content-grid">
        <VideoFeed
          :frame="detection.currentFrame.value"
          source-type="rtsp"
          :status-msg="videoStatus"
          :status-class="detection.statusType.value"
          :is-live="detection.isRunning.value"
        />

        <PieChart :counts="detection.counts" />
      </div>

      <!-- Timeline -->
      <TimelineChart :timeline="detection.timeline.value" />
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useDetection } from './composables/useDetection.js'
import DashboardHeader from './components/DashboardHeader.vue'
import StatCard from './components/StatCard.vue'
import VideoFeed from './components/VideoFeed.vue'
import PieChart from './components/PieChart.vue'
import TimelineChart from './components/TimelineChart.vue'
import Sidebar from './components/Sidebar.vue'

const detection = useDetection()
const sidebarRef = ref(null)

const totalDetected = computed(() => {
  return (detection.counts.car || 0) + (detection.counts.motorcycle || 0) +
         (detection.counts.bus || 0) + (detection.counts.truck || 0)
})

const videoStatus = computed(() => {
  if (detection.isRunning.value) {
    const now = new Date().toLocaleTimeString()
    return `${now} | Frames: ${detection.frameCount.value} | Detected: ${detection.frameVehicles.value}`
  }
  return detection.statusMessage.value
})
</script>
