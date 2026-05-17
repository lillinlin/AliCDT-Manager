<template>
  <div class="p-6 space-y-6 fade-in">
    <!-- 顶部栏 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-text">总览</h1>
        <p class="text-sm text-text-muted mt-0.5">{{ now }}</p>
      </div>
      <button @click="sync" :disabled="store.loading"
        class="btn-primary flex items-center gap-2">
        <span :class="store.loading ? 'animate-spin' : ''">🔄</span>
        {{ store.loading ? '同步中...' : '立即同步' }}
      </button>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard icon="🖥️" label="实例总数" :value="instances.length" />
      <StatCard icon="✅" label="运行中" :value="runningCount" color="success" />
      <StatCard icon="⏹️" label="已停机" :value="stoppedCount" color="danger" />
      <StatCard icon="🛡️" label="保活中" :value="keepAliveCount" color="accent" />
    </div>

    <!-- 实例卡片列表 -->
    <div v-if="instances.length === 0" class="card p-12 text-center">
      <div class="text-4xl mb-3">🌐</div>
      <div class="text-text-muted text-sm">暂无实例，请先添加账户并同步</div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
      <InstanceCard
        v-for="inst in instances"
        :key="inst.instance_id"
        :instance="inst"
        :account="accountMap[inst.account_id]"
        @start="store.controlInstance(inst.instance_id, 'start')"
        @stop="store.controlInstance(inst.instance_id, 'stop')"
        @release="confirmRelease(inst)"
      />
    </div>

    <!-- 释放确认弹窗 -->
    <Modal v-if="releaseTarget" @close="releaseTarget = null">
      <div class="text-center space-y-4">
        <div class="text-4xl">⚠️</div>
        <div class="font-semibold">确认释放实例？</div>
        <div class="text-sm text-text-muted">{{ releaseTarget.instance_id }}</div>
        <div class="text-xs text-danger bg-danger/10 border border-danger/20 rounded-lg px-3 py-2">
          此操作不可撤销，实例将被永久删除
        </div>
        <div class="flex gap-3">
          <button @click="releaseTarget = null" class="btn-ghost flex-1">取消</button>
          <button @click="doRelease" class="btn-danger flex-1">确认释放</button>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useStore } from '../stores'
import StatCard from '../components/StatCard.vue'
import InstanceCard from '../components/InstanceCard.vue'
import Modal from '../components/Modal.vue'

const store = useStore()
const releaseTarget = ref(null)
const now = ref('')

const instances = computed(() => store.instances)
const runningCount = computed(() => instances.value.filter(i => i.status === 'Running').length)
const stoppedCount = computed(() => instances.value.filter(i => i.status === 'Stopped').length)
const keepAliveCount = computed(() => {
  return store.accounts.filter(a => a.keep_alive).length
})
const accountMap = computed(() => {
  const m = {}
  store.accounts.forEach(a => m[a.id] = a)
  return m
})

function updateTime() {
  now.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

let timer
onMounted(async () => {
  await store.fetchAccounts()
  await store.fetchInstances()
  updateTime()
  timer = setInterval(updateTime, 1000)
})
onUnmounted(() => clearInterval(timer))

async function sync() {
  await store.syncAll()
}

function confirmRelease(inst) {
  releaseTarget.value = inst
}

async function doRelease() {
  await store.releaseInstance(releaseTarget.value.instance_id)
  releaseTarget.value = null
}
</script>
