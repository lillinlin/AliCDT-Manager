<template>
  <div class="p-6 space-y-6 fade-in">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-text">系统日志</h1>
      <div class="flex items-center gap-2">
        <select v-model="category" @change="load" class="input w-36 py-1.5">
          <option value="">全部分类</option>
          <option value="traffic">流量</option>
          <option value="keepalive">保活</option>
          <option value="scheduler">定时任务</option>
          <option value="ddns">DDNS</option>
          <option value="notify">通知</option>
          <option value="system">系统</option>
        </select>
        <button @click="load" class="btn-ghost text-xs px-3 py-1.5">🔄 刷新</button>
        <button @click="clearLogs" class="btn-danger text-xs px-3 py-1.5">🗑️ 清空</button>
      </div>
    </div>

    <div class="card overflow-hidden">
      <div v-if="store.logs.length === 0" class="p-12 text-center text-text-muted text-sm">暂无日志</div>
      <div v-else class="divide-y divide-border">
        <div v-for="log in store.logs" :key="log.id"
          class="flex items-start gap-3 px-4 py-3 hover:bg-white/2 transition-colors">
          <span class="text-xs mt-0.5 flex-shrink-0" :class="levelColor(log.level)">{{ levelIcon(log.level) }}</span>
          <span class="text-xs px-1.5 py-0.5 rounded bg-surface border border-border text-text-muted flex-shrink-0">
            {{ log.category }}
          </span>
          <span class="text-xs text-text flex-1 font-mono leading-relaxed">{{ log.message }}</span>
          <span class="text-xs text-text-muted flex-shrink-0 font-mono">
            {{ formatTime(log.created_at) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useStore } from '../stores'

const store = useStore()
const category = ref('')

onMounted(load)

async function load() {
  await store.fetchLogs(category.value || null)
}

async function clearLogs() {
  if (confirm('确认清空日志？')) {
    await store.clearLogs(category.value || null)
  }
}

function levelColor(l) {
  return { info: 'text-accent', warning: 'text-warning', error: 'text-danger' }[l] || 'text-text-muted'
}
function levelIcon(l) {
  return { info: 'ℹ', warning: '⚠', error: '✕' }[l] || '•'
}
function formatTime(t) {
  if (!t) return ''
  return new Date(t + 'Z').toLocaleString('zh-CN', { hour12: false })
}
</script>
