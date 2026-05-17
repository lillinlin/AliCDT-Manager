<template>
  <div class="min-h-screen flex items-center justify-center relative overflow-hidden">
    <!-- 背景光晕 -->
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-accent/10 rounded-full blur-3xl"></div>
      <div class="absolute bottom-1/4 left-1/3 w-64 h-64 bg-indigo-900/20 rounded-full blur-3xl"></div>
    </div>

    <div class="card p-8 w-full max-w-sm relative fade-in">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="w-14 h-14 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center text-2xl mx-auto mb-4 glow-pulse">🛡️</div>
        <h1 class="text-xl font-semibold text-text">Aliyun Guard</h1>
        <p class="text-sm text-text-muted mt-1">阿里云流量守护控制台</p>
      </div>

      <!-- 表单 -->
      <div class="space-y-4">
        <div>
          <label class="text-xs text-text-muted mb-1.5 block">用户名</label>
          <input v-model="form.username" class="input" placeholder="admin" @keyup.enter="doLogin" />
        </div>
        <div>
          <label class="text-xs text-text-muted mb-1.5 block">密码</label>
          <input v-model="form.password" type="password" class="input" placeholder="••••••••" @keyup.enter="doLogin" />
        </div>

        <div v-if="error" class="text-xs text-danger bg-danger/10 border border-danger/20 rounded-lg px-3 py-2">
          {{ error }}
        </div>

        <button @click="doLogin" :disabled="loading"
          class="btn-primary w-full flex items-center justify-center gap-2 py-2.5 mt-2">
          <span v-if="loading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          <span>{{ loading ? '登录中...' : '登录' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from '../stores'

const router = useRouter()
const store = useStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

async function doLogin() {
  if (!form.value.username || !form.value.password) return
  loading.value = true
  error.value = ''
  try {
    await store.login(form.value.username, form.value.password)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>
