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

    <!-- 实例卡片列表（支持拖拽排序） -->
    <div v-if="sortedInstances.length === 0" class="card p-12 text-center">
      <div class="text-4xl mb-3">🌐</div>
      <div class="text-text-muted text-sm">暂无实例，请先添加账户并同步</div>
    </div>

    <div
      v-else
      class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4"
    >
      <div
        v-for="inst in sortedInstances"
        :key="inst.instance_id"
        draggable="true"
        @dragstart="onDragStart($event, inst.instance_id)"
        @dragover.prevent="onDragOver($event, inst.instance_id)"
        @dragend="onDragEnd"
        @drop.prevent="onDrop($event, inst.instance_id)"
        :class="[
          'transition-all duration-200',
          dragOverId === inst.instance_id && draggingId !== inst.instance_id
            ? 'scale-[1.02] opacity-80'
            : '',
          draggingId === inst.instance_id
            ? 'opacity-40 scale-95'
            : '',
        ]"
      >
        <InstanceCard
          :instance="inst"
          :account="accountMap[inst.account_id]"
          @start="store.controlInstance(inst.instance_id, 'start')"
          @stop="store.controlInstance(inst.instance_id, 'stop')"
          @release="confirmRelease(inst)"
        />
      </div>
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

// 拖拽状态
const draggingId = ref(null)
const dragOverId = ref(null)

// 自定义排序（持久化到 localStorage）
const SORT_KEY = 'instance_sort_order'
const customOrder = ref(JSON.parse(localStorage.getItem(SORT_KEY) || '[]'))

const instances = computed(() => store.instances)
const runningCount = computed(() => instances.value.filter(i => i.status === 'Running').length)
const stoppedCount = computed(() => instances.value.filter(i => i.status === 'Stopped').length)
const keepAliveCount = computed(() => store.accounts.filter(a => a.keep_alive).length)
const accountMap = computed(() => {
  const m = {}
  store.accounts.forEach(a => m[a.id] = a)
  return m
})

// 按自定义顺序排列实例
const sortedInstances = computed(() => {
  const arr = [...instances.value]
  if (customOrder.value.length === 0) return arr
  return arr.sort((a, b) => {
    const ia = customOrder.value.indexOf(a.instance_id)
    const ib = customOrder.value.indexOf(b.instance_id)
    if (ia === -1 && ib === -1) return 0
    if (ia === -1) return 1
    if (ib === -1) return -1
    return ia - ib
  })
})

function saveOrder() {
  const order = sortedInstances.value.map(i => i.instance_id)
  customOrder.value = order
  localStorage.setItem(SORT_KEY, JSON.stringify(order))
}

function onDragStart(e, id) {
  draggingId.value = id
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', id)
}

function onDragOver(e, id) {
  dragOverId.value = id
}

function onDrop(e, targetId) {
  const sourceId = draggingId.value
  if (!sourceId || sourceId === targetId) return

  const order = sortedInstances.value.map(i => i.instance_id)
  const fromIdx = order.indexOf(sourceId)
  const toIdx = order.indexOf(targetId)
  if (fromIdx === -1 || toIdx === -1) return

  // 移动元素
  order.splice(fromIdx, 1)
  order.splice(toIdx, 0, sourceId)

  customOrder.value = order
  localStorage.setItem(SORT_KEY, JSON.stringify(order))
}

function onDragEnd() {
  draggingId.value = null
  dragOverId.value = null
}

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
  // 清理排序中已释放的实例
  customOrder.value = customOrder.value.filter(id => id !== releaseTarget.value?.instance_id)
  localStorage.setItem(SORT_KEY, JSON.stringify(customOrder.value))
}
</script>
