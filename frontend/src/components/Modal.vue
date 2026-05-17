<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')"></div>
    <div class="card p-6 w-full max-w-sm relative z-10 fade-in">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineEmits(['close'])
</script>
