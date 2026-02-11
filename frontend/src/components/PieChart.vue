<template>
  <div class="chart-wrapper">
    <div class="chart-wrapper__title">📊 Vehicle Composition</div>
    <div class="chart-container">
      <Doughnut :data="chartData" :options="chartOptions" :key="themeKey" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { useTheme } from '../composables/useTheme.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const { isDark } = useTheme()

const props = defineProps({
  counts: { type: Object, required: true }
})

// Force re-render on theme change
const themeKey = computed(() => isDark.value ? 'dark' : 'light')

const chartData = computed(() => ({
  labels: ['Mobil', 'Motor', 'Bus', 'Truk'],
  datasets: [{
    data: [
      props.counts.car || 0,
      props.counts.motorcycle || 0,
      props.counts.bus || 0,
      props.counts.truck || 0
    ],
    backgroundColor: [
      '#10b981', // green
      '#f59e0b', // orange
      '#3b82f6', // blue
      '#8b5cf6'  // purple
    ],
    borderColor: isDark.value ? '#1a1a2e' : '#ffffff',
    borderWidth: 4,
    hoverOffset: 12,
    borderRadius: 6
  }]
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  cutout: '65%',
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        color: isDark.value ? '#94a3b8' : '#475569',
        font: { family: 'Outfit', size: 13, weight: '600' },
        padding: 20,
        usePointStyle: true,
        pointStyle: 'circle'
      }
    },
    tooltip: {
      backgroundColor: isDark.value ? 'rgba(30, 30, 50, 0.9)' : 'rgba(255, 255, 255, 0.9)',
      titleColor: isDark.value ? '#fff' : '#1e293b',
      bodyColor: isDark.value ? '#94a3b8' : '#475569',
      borderColor: isDark.value ? 'rgba(148,163,184,0.3)' : 'rgba(0,0,0,0.1)',
      borderWidth: 1,
      cornerRadius: 12,
      padding: 14,
      displayColors: true,
      callbacks: {
        label: (context) => ` ${context.label}: ${context.raw} unit`
      }
    }
  }
}))
</script>

<style scoped>
.chart-container {
  padding: 10px;
  position: relative;
}
</style>
