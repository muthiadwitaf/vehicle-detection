<template>
  <div :class="['stat-card', `stat-card--${type}`]">
    <div class="stat-card__icon">{{ icon }}</div>
    <div class="stat-card__content">
      <div class="stat-card__label">{{ label }}</div>
      <div class="stat-card__value">{{ formattedValue }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  value: { type: Number, default: 0 },
  type: { type: String, default: '' },
  suffix: { type: String, default: '' }
})

const formattedValue = computed(() => {
  return props.value.toLocaleString() + props.suffix
})
</script>
