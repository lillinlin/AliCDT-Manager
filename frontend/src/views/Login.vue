<template>
  <div class="min-h-screen flex items-center justify-center relative overflow-hidden">
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-accent/10 rounded-full blur-3xl"></div>
      <div class="absolute bottom-1/4 left-1/3 w-64 h-64 bg-indigo-900/20 rounded-full blur-3xl"></div>
    </div>

    <div class="card p-8 w-full max-w-sm relative fade-in">
      <div class="text-center mb-8">
        <div class="w-14 h-14 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center text-2xl mx-auto mb-4 glow-pulse">🛡️</div>
        <h1 class="text-xl font-semibold text-text">AliCDT Manager</h1>
        <p class="text-sm text-text-muted mt-1">
          {{ isInit ? '创建管理员账号' : '登录控制台' }}
        </p>
      </div>

      <div class="space-y-4">
        <div>
          <label class="text-xs text-text-muted mb-1.5 block">用户名</label>
          <input v-model="form.username" class="input" placeholder="admin" @keyup.enter="submit" />
        </div>
        <div>
          <label class="text-xs text-text-muted mb-1.5 block">密码</label>
          <input v-model="form.password" type="password" class="input"
            :placeholder="isInit ? '至少6位' : '••••••••'" @keyup.enter="submit" />
        </div>
        <div v-if="isInit">
          <label class="text-xs text-text-muted mb-1.5 block">确认密码</label>
          <input v-model="form.confirm" type="password" class="input" placeholder="再次输入密码" @keyup.enter="submit" />
        </div>

        <div v-if="error" class="text-xs text-danger bg-danger/10 border border-danger/20 rounded-lg px-3 py-2">
          {{ error }}
        </div>

        <button @click="submit" :disabled="loading"
          class="btn-primary w-full flex items-center justify-center gap-2 py-2.5 mt-2">
          <span v-if="loading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          <span>{{ loading ? '请稍候...' : (isInit ? '创建账号并登录' : '登录') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from '../stores'
import axios from 'axios'

const router = useRouter()
const store = useStore()
const isInit = ref(false)
const loading = ref(false)
const error = ref('')
const form = ref({ username: '', password: '', confirm: '' })

onMounted(async () => {
  const { data } = await axios.get('/api/auth/initialized')
  isInit.value = !data.initialized
})

async function submit() {
  error.value = ''
  if (!form.value.username || !form.value.password) {
    error.value = '请填写用户名和密码'
    return
  }
  if (isInit.value) {
    if (form.value.password.length < 6) {
      error.value = '密码至少6位'
      return
    }
    if (form.value.password !== form.value.confirm) {
      error.value = '两次密码不一致'
      return
    }
  }
  loading.value = true
  try {
    if (isInit.value) {
      const { data } = await axios.post('/api/auth/init', {
        username: form.value.username,
        password: form.value.password,
      })
      localStorage.setItem('token', data.token)
    } else {
      await store.login(form.value.username, form.value.password)
    }
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '操作失败'
  } finally {
    loading.value = false
  }
}
</script>
