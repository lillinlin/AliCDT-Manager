<template>
  <div class="p-6 space-y-6 fade-in">
    <h1 class="text-xl font-semibold text-text">系统设置</h1>

    <!-- TG 通知 -->
    <div class="card p-5 space-y-4">
      <div class="flex items-center gap-2 mb-2">
        <span class="text-lg">✈️</span>
        <h2 class="font-medium text-text text-sm">Telegram 通知</h2>
      </div>
      <div>
        <label class="text-xs text-text-muted mb-1.5 block">Bot Token</label>
        <input v-model="form.tg_bot_token" class="input" placeholder="123456:ABC..." />
      </div>
      <div>
        <label class="text-xs text-text-muted mb-1.5 block">Chat ID</label>
        <input v-model="form.tg_chat_id" class="input" placeholder="5412725363" />
      </div>
      <div class="text-xs text-text-muted bg-surface rounded-lg px-3 py-2 space-y-1">
        <div>通知触发条件：</div>
        <div>• 流量熔断自动停机</div>
        <div>• 抢占式实例被回收并拉起</div>
        <div>• 定时开关机执行</div>
        <div>• 每日北京时间 00:00 流量汇报</div>
      </div>
      <div class="flex gap-2">
        <button @click="save" :disabled="saving" class="btn-primary flex items-center gap-2">
          <span v-if="saving" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          {{ saving ? '保存中...' : '保存设置' }}
        </button>
        <button @click="testTg" :disabled="testing"
          class="btn-ghost flex items-center gap-2 border border-border">
          <span v-if="testing" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          {{ testing ? '发送中...' : '📨 发送测试消息' }}
        </button>
      </div>
    </div>

    <!-- 修改密码 -->
    <div class="card p-5 space-y-4">
      <div class="flex items-center gap-2 mb-2">
        <span class="text-lg">🔒</span>
        <h2 class="font-medium text-text text-sm">修改密码</h2>
      </div>
      <div>
        <label class="text-xs text-text-muted mb-1.5 block">新密码（至少6位）</label>
        <input v-model="newPassword" type="password" class="input" placeholder="••••••••" />
      </div>
      <button @click="changePassword" class="btn-danger text-xs px-4 py-2">更新密码</button>
    </div>

    <div v-if="msg" class="text-xs rounded-lg px-3 py-2 border"
      :class="msg.startsWith('❌') ? 'text-danger bg-danger/10 border-danger/20' : 'text-success bg-success/10 border-success/20'">
      {{ msg }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useStore } from '../stores'
import axios from 'axios'

const store = useStore()
const saving = ref(false)
const testing = ref(false)
const msg = ref('')
const newPassword = ref('')
const form = ref({ tg_bot_token: '', tg_chat_id: '' })

onMounted(async () => {
  await store.fetchSettings()
  form.value.tg_bot_token = store.settings.tg_bot_token || ''
  form.value.tg_chat_id = store.settings.tg_chat_id || ''
})

async function save() {
  saving.value = true
  msg.value = ''
  const items = Object.entries(form.value).map(([key, value]) => ({ key, value }))
  await store.saveSettings(items)
  msg.value = '✅ 设置已保存'
  saving.value = false
  setTimeout(() => msg.value = '', 3000)
}

async function testTg() {
  await save()
  testing.value = true
  msg.value = ''
  try {
    const token = localStorage.getItem('token')
    await axios.post('/api/settings/test-tg', {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    msg.value = '✅ 测试消息已发送，请检查 Telegram'
  } catch (e) {
    msg.value = '❌ 发送失败：' + (e.response?.data?.detail || e.message)
  } finally {
    testing.value = false
    setTimeout(() => msg.value = '', 5000)
  }
}

async function changePassword() {
  if (!newPassword.value || newPassword.value.length < 6) {
    msg.value = '❌ 密码至少6位'
    return
  }
  const token = localStorage.getItem('token')
  await axios.post('/api/settings/change-password',
    { password: newPassword.value },
    { headers: { Authorization: `Bearer ${token}` } }
  )
  newPassword.value = ''
  msg.value = '✅ 密码已更新，下次登录生效'
  setTimeout(() => msg.value = '', 3000)
}
</script>
