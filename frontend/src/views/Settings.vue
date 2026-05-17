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
        <label class="text-xs text-text-muted mb-1 block">Bot Token</label>
        <input v-model="form.tg_bot_token" class="input" placeholder="123456:ABC..." />
      </div>
      <div>
        <label class="text-xs text-text-muted mb-1 block">Chat ID</label>
        <input v-model="form.tg_chat_id" class="input" placeholder="-100..." />
      </div>
      <button @click="testTg" class="btn-ghost text-xs px-3 py-1.5">发送测试消息</button>
    </div>

    <!-- 修改密码 -->
    <div class="card p-5 space-y-4">
      <div class="flex items-center gap-2 mb-2">
        <span class="text-lg">🔒</span>
        <h2 class="font-medium text-text text-sm">修改密码</h2>
      </div>
      <div>
        <label class="text-xs text-text-muted mb-1 block">新密码</label>
        <input v-model="newPassword" type="password" class="input" placeholder="至少8位" />
      </div>
      <button @click="changePassword" class="btn-danger text-xs px-3 py-1.5">更新密码</button>
    </div>

    <!-- 保存 -->
    <div class="flex justify-end">
      <button @click="save" :disabled="saving" class="btn-primary flex items-center gap-2">
        <span v-if="saving" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
        {{ saving ? '保存中...' : '保存设置' }}
      </button>
    </div>

    <div v-if="msg" class="text-xs text-success bg-success/10 border border-success/20 rounded-lg px-3 py-2">
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
  msg.value = '设置已保存'
  saving.value = false
  setTimeout(() => msg.value = '', 3000)
}

async function changePassword() {
  if (!newPassword.value || newPassword.value.length < 8) {
    alert('密码至少8位')
    return
  }
  const token = localStorage.getItem('token')
  await axios.post('/api/settings/change-password',
    { password: newPassword.value },
    { headers: { Authorization: `Bearer ${token}` } }
  )
  newPassword.value = ''
  msg.value = '密码已更新，下次登录生效'
  setTimeout(() => msg.value = '', 3000)
}

async function testTg() {
  await save()
  msg.value = '测试消息已发送（如未收到请检查 Token 和 Chat ID）'
  setTimeout(() => msg.value = '', 4000)
}
</script>
