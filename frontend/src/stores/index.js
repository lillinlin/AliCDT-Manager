import { defineStore } from 'pinia'
import axios from 'axios'
import { ref } from 'vue'

const api = axios.create({ baseURL: '/api' })
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})
api.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
  }
  return Promise.reject(err)
})

export const useStore = defineStore('main', () => {
  const instances = ref([])
  const accounts = ref([])
  const logs = ref([])
  const settings = ref({})
  const loading = ref(false)

  async function login(username, password) {
    const { data } = await api.post('/auth/login', { username, password })
    localStorage.setItem('token', data.token)
    return data
  }

  async function fetchInstances() {
    const { data } = await api.get('/instances')
    instances.value = data
  }

  async function fetchAccounts() {
    const { data } = await api.get('/accounts')
    accounts.value = data
  }

  async function fetchLogs(category = null) {
    const params = category ? { category } : {}
    const { data } = await api.get('/logs', { params })
    logs.value = data
  }

  async function fetchSettings() {
    const { data } = await api.get('/settings')
    settings.value = data
  }

  async function syncAll() {
    loading.value = true
    await api.post('/instances/sync')
    await fetchInstances()
    loading.value = false
  }

  async function syncSingleInstance(instanceId) {
    await api.post(`/instances/${instanceId}/sync`)
    await fetchInstances()
  }

  async function controlInstance(instanceId, action) {
    await api.post(`/instances/${instanceId}/${action}`)
    await fetchInstances()
    const targetStatus = action === 'start' ? 'Running' : 'Stopped'
    let count = 0
    return new Promise((resolve) => {
      const poll = setInterval(async () => {
        await fetchInstances()
        count++
        const inst = instances.value.find(i => i.instance_id === instanceId)
        if ((inst && inst.status === targetStatus) || count >= 15) {
          clearInterval(poll)
          resolve()
        }
      }, 2000)
    })
  }

  async function releaseInstance(instanceId) {
    await api.delete(`/instances/${instanceId}`)
    await fetchInstances()
  }

  async function getBilling(accountId) {
    const { data } = await api.get(`/billing/${accountId}`)
    return data
  }

  async function createAccount(payload) {
    await api.post('/accounts', payload)
    await fetchAccounts()
    await fetchInstances()
  }

  async function updateAccount(id, payload) {
    await api.put(`/accounts/${id}`, payload)
    await fetchAccounts()
  }

  async function deleteAccount(id) {
    await api.delete(`/accounts/${id}`)
    await fetchAccounts()
    await fetchInstances()
  }

  async function saveSettings(items) {
    await api.post('/settings', items)
    await fetchSettings()
  }

  async function clearLogs(category = null) {
    await api.delete('/logs', { params: category ? { category } : {} })
    await fetchLogs()
  }

  async function renameInstance(instanceId, name) {
    await api.patch(`/instances/${instanceId}/rename`, { name })
    await fetchInstances()
  }

  return {
    instances, accounts, logs, settings, loading,
    login, fetchInstances, fetchAccounts, fetchLogs, fetchSettings,
    syncAll, syncSingleInstance, controlInstance, releaseInstance, getBilling,
    createAccount, updateAccount, deleteAccount, saveSettings, clearLogs,
    renameInstance,
  }
})
