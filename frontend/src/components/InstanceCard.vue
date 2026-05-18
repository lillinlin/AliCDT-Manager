<template>
  <div class="card p-5 space-y-4 hover:border-accent/30 transition-all duration-200">
    <!-- 顶部：名称 + 状态 -->
    <div class="flex items-start justify-between">
      <div>
        <div class="font-medium text-text text-sm">{{ instance.instance_name || instance.instance_id }}</div>
        <div class="text-xs text-text-muted font-mono mt-0.5">{{ instance.instance_id }}</div>
      </div>
      <span :class="statusBadge">{{ statusLabel }}</span>
    </div>

    <!-- 流量进度条 -->
    <div>
      <div class="flex justify-between text-xs mb-1.5">
        <span class="text-text-muted">本月流量</span>
        <span :class="trafficColor" class="font-medium font-mono">
          {{ instance.traffic_used_gb?.toFixed(2) || '0.00' }} GB / {{ account?.traffic_limit_gb || 200 }} GB
        </span>
      </div>
      <div class="h-1.5 bg-border rounded-full overflow-hidden">
        <div class="h-full rounded-full transition-all duration-700"
          :class="trafficBarColor"
          :style="{ width: Math.min(instance.traffic_percent || 0, 100) + '%' }">
        </div>
      </div>
      <div class="text-right text-xs mt-1" :class="trafficColor">
        {{ (instance.traffic_percent || 0).toFixed(1) }}%
      </div>
    </div>

    <!-- 信息行 -->
    <div class="grid grid-cols-2 gap-2 text-xs">
      <div class="bg-surface rounded-lg px-3 py-2">
        <div class="text-text-muted mb-0.5">公网 IP</div>
        <div class="font-mono text-text">{{ instance.public_ip || '—' }}</div>
      </div>
      <div class="bg-surface rounded-lg px-3 py-2">
        <div class="text-text-muted mb-0.5">规格</div>
        <div class="text-text truncate">{{ instance.instance_type || '—' }}</div>
      </div>
      <div class="bg-surface rounded-lg px-3 py-2">
        <div class="text-text-muted mb-0.5">带宽</div>
        <div class="text-text">{{ instance.bandwidth_mbps ? instance.bandwidth_mbps + ' Mbps' : '—' }}</div>
      </div>
      <div class="bg-surface rounded-lg px-3 py-2">
        <div class="text-text-muted mb-0.5">类型</div>
        <div :class="instance.is_spot ? 'text-warning' : 'text-text'">
          {{ instance.is_spot ? '⚡ 抢占式' : '按需' }}
        </div>
      </div>
    </div>

    <!-- 账单信息：始终显示 -->
    <div class="bg-surface rounded-lg px-3 py-2.5 text-xs space-y-1.5">
      <div class="text-text-muted font-medium mb-1">账单信息</div>
      <div v-if="billingLoading" class="text-text-muted text-center py-1">加载中...</div>
      <div v-else-if="billingError" class="text-danger text-center py-1">{{ billingError }}</div>
      <template v-else>
        <div class="flex justify-between">
          <span class="text-text-muted">账户余额</span>
          <span class="font-mono"
            :class="(billing?.balance?.available_amount ?? 0) < 1 ? 'text-danger' : 'text-success'">
            {{ billing?.balance?.symbol }}{{ billing?.balance?.available_amount ?? '—' }}
          </span>
        </div>
        <div class="flex justify-between">
          <span class="text-text-muted">本月待还款</span>
          <span class="font-mono text-warning">
            {{ billing?.bill?.symbol }}{{ billing?.bill?.total_outstanding ?? '—' }}
          </span>
        </div>
      </template>
    </div>

    <!-- 账户 + 保活标记 -->
    <div class="flex items-center justify-between text-xs text-text-muted">
      <span>{{ account?.name || '未知账户' }}</span>
      <div class="flex items-center gap-2">
        <span v-if="account?.keep_alive" class="text-accent flex items-center gap-1">
          <span class="w-1.5 h-1.5 bg-accent rounded-full glow-pulse inline-block"></span>保活中
        </span>
        <span v-if="instance.last_synced">{{ formatTime(instance.last_synced) }}</span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="flex gap-2 pt-1 border-t border-border">
      <button v-if="instance.status !== 'Running'" @click="$emit('start')"
        class="flex-1 text-xs py-2 rounded-lg bg-success/10 hover:bg-success/20 text-success transition-all">
        ▶ 开机
      </button>
      <button v-if="instance.status === 'Running'" @click="$emit('stop')"
        class="flex-1 text-xs py-2 rounded-lg bg-warning/10 hover:bg-warning/20 text-warning transition-all">
        ⏹ 停机
      </button>
      <button @click="$emit('release')"
        class="text-xs px-3 py-2 rounded-lg bg-danger/5 hover:bg-danger/15 text-danger transition-all">
        释放
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStore } from '../stores'

const props = defineProps({ instance: Object, account: Object })
defineEmits(['start', 'stop', 'release'])

const store = useStore()
const billing = ref(null)
const billingLoading = ref(false)
const billingError = ref('')

const statusBadge = computed(() => ({
  Running: 'badge-running',
  Stopped: 'badge-stopped',
}[props.instance.status] || 'badge-unknown'))

const statusLabel = computed(() => ({
  Running: '● 运行中',
  Stopped: '● 已停机',
}[props.instance.status] || '● 未知'))

const trafficPct = computed(() => props.instance.traffic_percent || 0)
const trafficColor = computed(() => trafficPct.value >= 90 ? 'text-danger' : trafficPct.value >= 75 ? 'text-warning' : 'text-success')
const trafficBarColor = computed(() => trafficPct.value >= 90 ? 'bg-danger' : trafficPct.value >= 75 ? 'bg-warning' : 'bg-success')

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
