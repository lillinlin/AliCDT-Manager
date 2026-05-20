<template>
  <div class="relative flex flex-col p-5 rounded-2xl bg-surface/40 backdrop-blur-lg border border-border/50 shadow-sm hover:shadow-lg hover:-translate-y-0.5 hover:border-accent/40 transition-all duration-300 group/card">

    <!-- 拖拽手柄 -->
    <div class="flex justify-center mb-3 opacity-0 group-hover/card:opacity-100 transition-opacity cursor-grab active:cursor-grabbing">
      <div class="flex gap-0.5 items-center">
        <div v-for="i in 6" :key="i" class="w-0.5 h-3 bg-border rounded-full"></div>
      </div>
    </div>

    <div class="flex items-start justify-between gap-4">
      <div class="flex-1 min-w-0">
        <div v-if="!editingName"
          class="flex items-center gap-2 cursor-pointer group/edit"
          @click="startEditName">
          <h3 class="text-base font-semibold text-text truncate transition-colors group-hover/edit:text-accent">
            {{ instance.instance_name || instance.instance_id }}
          </h3>
          <span class="opacity-0 group-hover/edit:opacity-100 text-text-muted transition-opacity text-xs bg-surface-hover px-1.5 py-0.5 rounded-md border border-border whitespace-nowrap flex-shrink-0">
            编辑
          </span>
        </div>
        <div v-else class="flex items-center gap-2">
          <input v-model="newName" :disabled="isSavingName"
            class="input py-1 px-2 text-sm flex-1 bg-surface border-accent/50 focus:ring-2 focus:ring-accent/20 rounded-lg transition-all disabled:opacity-50"
            @keyup.enter="saveName" @keyup.escape="editingName=false" autofocus
            placeholder="输入新名称" />
          <div class="flex gap-1 flex-shrink-0">
            <button @click="saveName" :disabled="isSavingName"
              class="w-7 h-7 flex items-center justify-center rounded-md bg-success/10 text-success hover:bg-success/20 transition-colors disabled:opacity-50">
              <span v-if="isSavingName" class="w-3 h-3 border-2 border-success border-t-transparent rounded-full animate-spin"></span>
              <span v-else>✓</span>
            </button>
            <button @click="editingName=false" :disabled="isSavingName"
              class="w-7 h-7 flex items-center justify-center rounded-md bg-surface text-text-muted hover:bg-danger/10 hover:text-danger transition-colors disabled:opacity-50">
              ✕
            </button>
          </div>
        </div>
        <div class="text-xs text-text-muted font-mono mt-1 truncate opacity-70">{{ instance.instance_id }}</div>
      </div>

      <div class="flex flex-col items-end gap-1.5 flex-shrink-0">
        <div class="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-surface/50 border border-border/50" :title="regionLabel">
          <span class="text-base leading-none drop-shadow-sm font-emoji">{{ regionFlag }}</span>
          <span class="text-xs text-text font-medium">{{ instance.region_id || '未知' }}</span>
        </div>
        <div class="px-2 py-0.5 rounded-full text-[11px] font-medium tracking-wide flex items-center gap-1.5 border border-transparent shadow-sm" :class="statusBadge">
          <span class="w-1.5 h-1.5 rounded-full animate-pulse" :class="instance.status === 'Running' ? 'bg-current' : 'bg-current opacity-50'"></span>
          {{ statusLabel.replace('● ', '') }}
        </div>
      </div>
    </div>

    <div class="mt-5 p-3 rounded-xl bg-surface-hover/30 border border-border/30">
      <div class="flex justify-between text-xs mb-2">
        <span class="text-text-muted font-medium">本月流量消耗</span>
        <span :class="trafficColor" class="font-bold font-mono tracking-tight">
          {{ instance.traffic_used_gb?.toFixed(2) || '0.00' }} <span class="text-text-muted font-normal">/ {{ account?.traffic_limit_gb || 200 }} GB</span>
        </span>
      </div>
      <div class="h-2 bg-background/50 rounded-full overflow-hidden shadow-inner relative">
        <div class="h-full rounded-full transition-all duration-1000 relative"
          :class="trafficBarColor"
          :style="{ width: Math.min(instance.traffic_percent || 0, 100) + '%' }">
          <div class="absolute inset-0 bg-white/20 w-full animate-pulse"></div>
        </div>
      </div>
      <div class="flex justify-between text-[11px] mt-2">
        <span class="text-text-muted">熔断阈值 <span class="font-medium text-text">{{ account?.threshold_percent || 95 }}%</span></span>
        <span :class="trafficColor" class="font-medium">{{ (instance.traffic_percent || 0).toFixed(1) }}%</span>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-2 mt-4 text-xs">
      <div class="bg-surface-hover/40 border border-border/40 rounded-xl px-3 py-2.5 hover:bg-surface-hover/60 transition-colors">
        <div class="text-text-muted mb-1 text-[11px] uppercase tracking-wider">公网 IP</div>
        <div class="font-mono text-text font-medium">{{ instance.public_ip || '—' }}</div>
      </div>
      <div class="bg-surface-hover/40 border border-border/40 rounded-xl px-3 py-2.5 hover:bg-surface-hover/60 transition-colors">
        <div class="text-text-muted mb-1 text-[11px] uppercase tracking-wider">规格</div>
        <div class="text-text font-medium truncate" :title="instance.instance_type">{{ instance.instance_type || '—' }}</div>
      </div>
    </div>

    <div class="flex flex-wrap gap-2 mt-4 text-[11px]">
      <span v-if="account?.keep_alive"
        class="px-2.5 py-1 rounded-md bg-accent/10 border border-accent/20 text-accent font-medium flex items-center gap-1.5 shadow-sm">
        <span class="w-1.5 h-1.5 bg-accent rounded-full animate-ping inline-block"></span>
        自动保活中
      </span>
      <span v-if="account?.auto_stop_time || account?.auto_start_time"
        class="px-2.5 py-1 rounded-md bg-warning/10 border border-warning/20 text-warning-dark font-medium flex items-center gap-1 shadow-sm">
        ⏰
        <span v-if="account?.auto_stop_time">{{ account.auto_stop_time }} 关</span>
        <span v-if="account?.auto_stop_time && account?.auto_start_time" class="opacity-50 px-0.5">|</span>
        <span v-if="account?.auto_start_time">{{ account.auto_start_time }} 开</span>
      </span>
      <span class="px-2.5 py-1 rounded-md bg-surface border border-border text-text-muted font-medium shadow-sm">
        {{ account?.shutdown_mode === 'StopCharging' ? '节省停机' : '普通停机' }}
      </span>
    </div>

    <div class="mt-4 bg-gradient-to-br from-surface to-surface-hover/50 border border-border/50 rounded-xl px-3.5 py-3 text-xs shadow-sm">
      <div class="flex justify-between items-center mb-2">
        <span class="text-text-muted font-semibold tracking-wide">账单动态</span>
        <span v-if="billingLoading" class="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin"></span>
      </div>
      <div v-if="billingError" class="text-danger text-center py-1 bg-danger/5 rounded-md">{{ billingError }}</div>
      <div v-else-if="!billingLoading" class="space-y-1.5">
        <div class="flex justify-between items-center">
          <span class="text-text-muted">账户余额</span>
          <span class="font-mono text-sm font-semibold"
            :class="(billing?.balance?.available_amount ?? 0) < 1 ? 'text-danger' : 'text-success'">
            {{ billing?.balance?.symbol }}{{ billing?.balance?.available_amount ?? '—' }}
          </span>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-text-muted">本月待还</span>
          <span class="font-mono font-medium" :class="(billing?.bill?.total_outstanding ?? 0) > 0 ? 'text-warning' : 'text-text'">
            {{ billing?.bill?.symbol }}{{ billing?.bill?.total_outstanding ?? '—' }}
          </span>
        </div>
      </div>
    </div>

    <div class="flex-1"></div>

    <div class="flex items-center justify-between text-[11px] text-text-muted mt-5 mb-3 px-1">
      <span class="flex items-center gap-1"><span class="text-xs">🔑</span> {{ account?.name || '未知账户' }}</span>
      <div class="flex items-center gap-2">
        <span v-if="instance.last_synced" class="opacity-70">同步于 {{ formatTime(instance.last_synced) }}</span>
        <button @click="syncThis" :disabled="isSyncing"
          class="flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface border border-border hover:border-accent/40 hover:text-accent transition-all disabled:opacity-50">
          <span :class="isSyncing ? 'animate-spin' : ''" class="text-xs">🔄</span>
          <span class="text-[10px]">{{ isSyncing ? '同步中' : '同步' }}</span>
        </button>
      </div>
    </div>

    <div class="flex gap-2.5 pt-3 border-t border-border/60">
      <button
        v-if="instance.status !== 'Running'"
        @click="handleStart"
        :disabled="isStarting"
        class="flex-1 text-xs font-medium py-2.5 rounded-xl transition-all duration-200 shadow-sm active:scale-95 flex items-center justify-center gap-1.5"
        :class="isStarting
          ? 'bg-surface border border-border text-text-muted cursor-not-allowed'
          : 'bg-success/10 border border-success/20 hover:bg-success hover:text-white text-success hover:shadow-success/30'"
      >
        <span v-if="isStarting" class="w-3 h-3 border-2 border-text-muted border-t-transparent rounded-full animate-spin"></span>
        <span>{{ isStarting ? '启动中...' : '▶ 启动实例' }}</span>
      </button>
      <button
        v-if="instance.status === 'Running'"
        @click="handleStop"
        :disabled="isStopping"
        class="flex-1 text-xs font-medium py-2.5 rounded-xl transition-all duration-200 shadow-sm active:scale-95 flex items-center justify-center gap-1.5"
        :class="isStopping
          ? 'bg-surface border border-border text-text-muted cursor-not-allowed'
          : 'bg-warning/10 border border-warning/20 hover:bg-warning hover:text-white text-warning-dark hover:shadow-warning/30'"
      >
        <span v-if="isStopping" class="w-3 h-3 border-2 border-text-muted border-t-transparent rounded-full animate-spin"></span>
        <span>{{ isStopping ? '停止中...' : '⏹ 停止实例' }}</span>
      </button>
      <button @click="$emit('release')"
        class="text-xs font-medium px-4 py-2.5 rounded-xl bg-danger/5 border border-danger/10 hover:bg-danger hover:text-white text-danger transition-all duration-200 shadow-sm hover:shadow-danger/30 active:scale-95">
        释放
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStore } from '../stores'

const props = defineProps({ instance: Object, account: Object })
defineEmits(['release'])

const store = useStore()
const billing = ref(null)
const billingLoading = ref(false)
const billingError = ref('')
const editingName = ref(false)
const newName = ref('')
const isSavingName = ref(false)
const isStarting = ref(false)
const isStopping = ref(false)
const isSyncing = ref(false)

const REGION_MAP = {
  'cn-hangzhou':     { flag: '🇨🇳', label: '中国 杭州' },
  'cn-shanghai':     { flag: '🇨🇳', label: '中国 上海' },
  'cn-beijing':      { flag: '🇨🇳', label: '中国 北京' },
  'cn-shenzhen':     { flag: '🇨🇳', label: '中国 深圳' },
  'cn-zhangjiakou':  { flag: '🇨🇳', label: '中国 张家口' },
  'cn-huhehaote':    { flag: '🇨🇳', label: '中国 呼和浩特' },
  'cn-wulanchabu':   { flag: '🇨🇳', label: '中国 乌兰察布' },
  'cn-qingdao':      { flag: '🇨🇳', label: '中国 青岛' },
  'cn-heyuan':       { flag: '🇨🇳', label: '中国 河源' },
  'cn-guangzhou':    { flag: '🇨🇳', label: '中国 广州' },
  'cn-chengdu':      { flag: '🇨🇳', label: '中国 成都' },
  'cn-hongkong':     { flag: '🇭🇰', label: '中国 香港' },
  'ap-southeast-1':  { flag: '🇸🇬', label: '新加坡' },
  'ap-southeast-2':  { flag: '🇦🇺', label: '澳大利亚 悉尼' },
  'ap-southeast-3':  { flag: '🇲🇾', label: '马来西亚 吉隆坡' },
  'ap-southeast-5':  { flag: '🇮🇩', label: '印度尼西亚 雅加达' },
  'ap-southeast-6':  { flag: '🇵🇭', label: '菲律宾 马尼拉' },
  'ap-southeast-7':  { flag: '🇹🇭', label: '泰国 曼谷' },
  'ap-northeast-1':  { flag: '🇯🇵', label: '日本 东京' },
  'ap-northeast-2':  { flag: '🇰🇷', label: '韩国 首尔' },
  'ap-south-1':      { flag: '🇮🇳', label: '印度 孟买' },
  'us-west-1':       { flag: '🇺🇸', label: '美国 硅谷' },
  'us-east-1':       { flag: '🇺🇸', label: '美国 弗吉尼亚' },
  'eu-west-1':       { flag: '🇬🇧', label: '英国 伦敦' },
  'eu-central-1':    { flag: '🇩🇪', label: '德国 法兰克福' },
  'me-east-1':       { flag: '🇦🇪', label: '阿联酋 迪拜' },
}

const regionInfo = computed(() => {
  const region = props.instance?.region_id || ''
  return REGION_MAP[region] || { flag: '🌐', label: region }
})
const regionFlag = computed(() => regionInfo.value.flag)
const regionLabel = computed(() => regionInfo.value.label)

const statusBadge = computed(() => ({
  Running: 'badge-running text-success bg-success/10 border-success/20',
  Stopped: 'badge-stopped text-text-muted bg-surface-hover border-border',
}[props.instance.status] || 'badge-unknown text-warning bg-warning/10 border-warning/20'))

const statusLabel = computed(() => ({
  Running: '● 运行中',
  Stopped: '● 已停机',
}[props.instance.status] || '● 未知'))

const trafficPct = computed(() => props.instance.traffic_percent || 0)
const trafficColor = computed(() => trafficPct.value >= 90 ? 'text-danger' : trafficPct.value >= 75 ? 'text-warning' : 'text-success')
const trafficBarColor = computed(() => trafficPct.value >= 90 ? 'bg-danger' : trafficPct.value >= 75 ? 'bg-warning' : 'bg-success')

function startEditName() {
  newName.value = props.instance.instance_name || ''
  editingName.value = true
}

async function saveName() {
  const val = newName.value.trim()
  if (!val || val === props.instance.instance_name) {
    editingName.value = false
    return
  }
  isSavingName.value = true
  try {
    await store.renameInstance(props.instance.instance_id, val)
    editingName.value = false
  } catch (error) {
    alert('名称修改失败: ' + (error.message || '请检查后端日志或网络状态'))
  } finally {
    isSavingName.value = false
  }
}

async function handleStart() {
  if (isStarting.value) return
  isStarting.value = true
  try {
    await store.controlInstance(props.instance.instance_id, 'start')
  } finally {
    isStarting.value = false
  }
}

async function handleStop() {
  if (isStopping.value) return
  isStopping.value = true
  try {
    await store.controlInstance(props.instance.instance_id, 'stop')
  } finally {
    isStopping.value = false
  }
}

async function syncThis() {
  if (isSyncing.value) return
  isSyncing.value = true
  try {
    await store.syncSingleInstance(props.instance.instance_id)
  } finally {
    isSyncing.value = false
  }
}

async function loadBilling() {
  if (!props.account) return
  billingLoading.value = true
  billingError.value = ''
  try {
    billing.value = await store.getBilling(props.account.id)
  } catch (e) {
    billingError.value = '账单获取失败'
  } finally {
    billingLoading.value = false
  }
}

onMounted(() => loadBilling())

function formatTime(t) {
  if (!t) return ''
  return new Date(t + 'Z').toLocaleTimeString('zh-CN', { hour12: false })
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');

.font-emoji {
  font-family: "Apple Color Emoji", "Noto Color Emoji", "Twemoji Mozilla", "Segoe UI Emoji", sans-serif;
}
</style>
