<template>
  <div class="timeline-wrapper">
    <div class="chart-wrapper__title">📈 Traffic Intensity</div>
    <div class="timeline-container">
      <Line :data="chartData" :options="chartOptions" :key="themeKey" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale,
  PointElement, LineElement,
  Filler, Tooltip
} from 'chart.js'
import { useTheme } from '../composables/useTheme.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

const { isDark } = useTheme()

const props = defineProps({
  timeline: { type: Array, default: () => [] }
})

const themeKey = computed(() => isDark.value ? 'dark' : 'light')

const chartData = computed(() => {
  const data = props.timeline || []
  const lineColor = isDark.value ? '#00d4ff' : '#0099cc'
  return {
    labels: data.map((_, i) => i + 1),
    datasets: [{
      label: 'Traffic Volume',
      data: data,
      borderColor: lineColor,
      backgroundColor: isDark.value ? 'rgba(0, 212, 255, 0.12)' : 'rgba(0, 153, 204, 0.12)',
      borderWidth: 3,
      fill: true,
      tension: 0.45,
      pointRadius: data.length > 60 ? 0 : 4,
      pointHoverRadius: 6,
      pointBackgroundColor: lineColor,
      pointBorderColor: isDark.value ? '#1e1e32' : '#fff',
      pointBorderWidth: 2,
    }]
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { intersect: false, mode: 'index' },
  scales: {
    x: {
      display: true,
      grid: {
        display: false
      },
      ticks: {
        color: isDark.value ? '#64748b' : '#94a3b8',
        font: { size: 10, family: 'Inter' },
        maxTicksLimit: 12
      }
    },
    y: {
      display: true,
      beginAtZero: true,
      grid: {
        color: isDark.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
        drawBorder: false
      },
      ticks: {
        color: isDark.value ? '#64748b' : '#94a3b8',
        font: { size: 11, family: 'Inter' },
        stepSize: 1,
        padding: 10
      }
    }
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: isDark.value ? 'rgba(30, 30, 50, 0.9)' : 'rgba(255, 255, 255, 0.9)',
      titleColor: isDark.value ? '#fff' : '#1e293b',
      bodyColor: isDark.value ? '#94a3b8' : '#475569',
      borderColor: isDark.value ? 'rgba(0,212,255,0.3)' : 'rgba(0,153,204,0.2)',
      borderWidth: 1,
      cornerRadius: 12,
      padding: 12,
      titleFont: { family: 'Outfit', weight: '700' },
      bodyFont: { family: 'Inter' },
      callbacks: {
        label: (item) => ` Kendaraan: ${item.raw} unit`
      }
    }
  }
}))
</script>

<style scoped>
.timeline-wrapper {
  height: 280px;
}

.timeline-container {
  height: 200px;
  position: relative;
}
</style>
