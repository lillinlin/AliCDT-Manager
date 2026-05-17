<template>
  <div class="card p-5 flex items-center gap-4">
    <div class="text-2xl">{{ icon }}</div>
    <div>
      <div class="text-2xl font-bold" :class="colorClass">{{ value }}</div>
      <div class="text-xs text-text-muted mt-0.5">{{ label }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ icon: String, label: String, value: [Number, String], color: String })
const colorClass = computed(() => ({
  success: 'text-success',
  danger: 'text-danger',
  accent: 'text-accent',
  warning: 'text-warning',
}[props.color] || 'text-text'))
</script>
