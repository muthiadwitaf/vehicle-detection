<template>
  <aside class="sidebar">
    <!-- RTSP URL (Manual or Preset) -->
    <div class="sidebar__section">
      <div class="sidebar__title">📹 RTSP Camera</div>

      <!-- Preset Camera Dropdown -->
      <div v-if="cameraPresets.length > 0">
        <label class="sidebar__label">Select Preset Camera:</label>
        <div class="dropdown-wrapper">
          <select v-model="selectedPreset" class="camera-select" @change="handlePresetSelect">
            <option value="">-- Manual URL --</option>
            <option v-for="cam in cameraPresets" :key="cam.id" :value="cam.id">
              {{ cam.name }}
            </option>
          </select>
        </div>
      </div>

      <!-- Manual URL Input -->
      <label class="sidebar__label" style="margin-top: 12px;">
        {{ selectedPreset ? 'Selected URL:' : 'RTSP URL:' }}
      </label>
      <input
        v-model="rtspUrl"
        class="input-field"
        :placeholder="selectedPreset ? 'From preset' : 'rtsp://admin:pass@ip:port/stream'"
        :disabled="!!selectedPreset"
      />

      <button
        class="btn btn--outline"
        style="margin-top: 10px"
        :disabled="!rtspUrl || isRunning"
        @click="$emit('test-rtsp', rtspUrl)"
      >
        🔗 Test Connection
      </button>

      <!-- <div class="info-box" style="margin-top: 12px">
        <strong>RTSP URL Format:</strong><br />
        rtsp://[user:pass@]ip:port/path<br /><br />
        <strong>Note:</strong> VPN may be required for internal cameras
      </div> -->
    </div>

    <!-- Detection Settings -->
    <div class="sidebar__section">
      <div class="sidebar__title">⚙️ Detection Settings</div>

      <label class="sidebar__label">Detection Precision:</label>
      <div class="radio-group" style="margin-bottom: 16px">
        <input type="radio" id="prec_low" value="low" v-model="precision" @change="emitSettings" style="display: none" />
        <label for="prec_low">Low</label>
        
        <input type="radio" id="prec_medium" value="medium" v-model="precision" @change="emitSettings" style="display: none" />
        <label for="prec_medium">Med</label>
        
        <input type="radio" id="prec_high" value="high" v-model="precision" @change="emitSettings" style="display: none" />
        <label for="prec_high">High</label>
      </div>

      <label class="sidebar__label">Frame Skip: {{ frameSkip }}</label>
      <div class="slider-container">
        <input type="range" v-model.number="frameSkip" min="1" max="10" @change="emitSettings" />
      </div>

      <label class="sidebar__label" style="margin-top: 12px">Confidence: {{ confidence.toFixed(2) }}</label>
      <div class="slider-container">
        <input type="range" v-model.number="confidence" min="0.1" max="0.9" step="0.05" @change="emitSettings" />
      </div>
    </div>

    <!-- Controls -->
    <div class="sidebar__section">
      <div class="btn-group">
        <button class="btn btn--primary" :disabled="!canStart || isRunning" @click="handleStart">
          ▶️ Start
        </button>
        <button class="btn btn--danger" :disabled="!isRunning" @click="$emit('stop')">
          ⏹️ Stop
        </button>
      </div>
    </div>

    <!-- Status -->
    <div v-if="statusMessage" :class="['status-msg', `status-msg--${statusType}`]">
      {{ statusMessage }}
    </div>

    <!-- Detection Classes -->
    <!-- <div class="sidebar__section">
      <div class="sidebar__title">🎯 Detection Classes</div>
      <div class="detection-classes">
        <div class="detection-class">
          <span class="detection-class__dot" style="background: #10b981"></span> Cars
        </div>
        <div class="detection-class">
          <span class="detection-class__dot" style="background: #f59e0b"></span> Motorcycles
        </div>
        <div class="detection-class">
          <span class="detection-class__dot" style="background: #3b82f6"></span> Buses
        </div>
        <div class="detection-class">
          <span class="detection-class__dot" style="background: #8b5cf6"></span> Trucks
        </div>
      </div>
    </div> -->
  </aside>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  isRunning: { type: Boolean, default: false },
  statusMessage: { type: String, default: '' },
  statusType: { type: String, default: 'info' },
  cameras: { type: Array, default: () => [] },
  cameraPresets: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'start-file', 'start-rtsp', 'start-webcam',
  'stop', 'test-rtsp', 'scan-cameras', 'load-presets', 'settings-change'
])

const inputMode = ref('rtsp')
const rtspUrl = ref('')
const selectedPreset = ref('')
const frameSkip = ref(2)
const confidence = ref(0.5)
const precision = ref('low')

const canStart = computed(() => {
  return rtspUrl.value && rtspUrl.value.length > 10
})

onMounted(() => {
  // Load camera presets on mount
  emit('load-presets')
})

function handlePresetSelect() {
  if (selectedPreset.value) {
    const preset = props.cameraPresets.find(c => c.id === selectedPreset.value)
    if (preset) {
      rtspUrl.value = preset.rtsp_url
      // Auto-start when a preset is selected
      handleStart()
    }
  } else {
    rtspUrl.value = ''
  }
}

function handleStart() {
  if (rtspUrl.value) {
    // Find the selected preset to get camera metadata
    const preset = props.cameraPresets.find(c => c.id === selectedPreset.value)
    if (preset) {
      // Pass camera_id and camera_name for database persistence
      emit('start-rtsp', rtspUrl.value, preset.id, preset.name)
    } else {
      // Manual URL entry - no camera_id
      emit('start-rtsp', rtspUrl.value)
    }
  }
}

function emitSettings() {
  emit('settings-change', frameSkip.value, confidence.value, precision.value)
}

defineExpose({ inputMode })
</script>

<style scoped>
.camera-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.camera-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  transition: all 0.2s ease;
}

.camera-item:hover {
  background: var(--bg-input-hover);
}

.camera-item.active {
  border-color: var(--accent-cyan);
  background: var(--bg-radio-active);
}

.camera-item__icon {
  font-size: 20px;
}

.camera-item__info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.camera-item__info strong {
  font-size: 13px;
  color: var(--text-primary);
}

.camera-item__info small {
  font-size: 11px;
  color: var(--text-muted);
}

.camera-item__check {
  color: var(--accent-cyan);
  font-weight: 700;
  font-size: 16px;
}

/* Dropdown Styles */
.dropdown-wrapper {
  position: relative;
}

.camera-select {
  width: 100%;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  outline: none;
  cursor: pointer;
  transition: all 0.2s;
  appearance: none;
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2394a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>');
  background-repeat: no-repeat;
  background-position: right 10px center;
  background-size: 16px;
  padding-right: 36px;
}

.camera-select:hover {
  border-color: var(--accent-cyan);
}

.camera-select:focus {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.1);
}

.camera-select option {
  background: var(--bg-card-solid);
  color: var(--text-primary);
  padding: 8px;
}
</style>
