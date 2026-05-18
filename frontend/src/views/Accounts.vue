<template>
  <div class="p-6 space-y-6 fade-in">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-text">账户管理</h1>
      <button @click="openAdd" class="btn-primary flex items-center gap-2">
        <span>＋</span> 添加账户
      </button>
    </div>

    <div class="space-y-3">
      <div v-if="store.accounts.length === 0" class="card p-12 text-center text-text-muted text-sm">
        暂无账户，点击右上角添加
      </div>

      <div v-for="acc in store.accounts" :key="acc.id" class="card p-5">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-sm">🔑</div>
            <div>
              <div class="font-medium text-text text-sm">{{ acc.name }}</div>
              <div class="text-xs text-text-muted font-mono mt-0.5">{{ acc.access_key_id }}</div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs px-2 py-0.5 rounded-full bg-surface border border-border text-text-muted">{{ acc.region_id }}</span>
            <span v-if="acc.keep_alive" class="text-xs px-2 py-0.5 rounded-full bg-accent/10 text-accent">保活</span>
            <button @click="openEdit(acc)" class="btn-ghost text-xs px-2 py-1">编辑</button>
            <button @click="confirmDelete(acc)" class="btn-danger text-xs px-2 py-1">删除</button>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-3 mt-4 text-xs">
          <div class="bg-surface rounded-lg px-3 py-2">
            <div class="text-text-muted mb-0.5">流量上限</div>
            <div class="text-text">{{ acc.traffic_limit_gb }} GB</div>
          </div>
          <div class="bg-surface rounded-lg px-3 py-2">
            <div class="text-text-muted mb-0.5">熔断阈值</div>
            <div class="text-text">{{ acc.threshold_percent }}%</div>
          </div>
          <div class="bg-surface rounded-lg px-3 py-2">
            <div class="text-text-muted mb-0.5">停机模式</div>
            <div class="text-text">{{ acc.shutdown_mode === 'StopCharging' ? '节省停机' : '普通停机' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加/编辑弹窗 -->
    <Modal v-if="showForm" @close="showForm = false">
      <div class="space-y-4 max-h-[80vh] overflow-y-auto pr-1">
        <h2 class="font-semibold text-text">{{ editTarget ? '编辑账户' : '添加账户' }}</h2>

        <div class="space-y-3">
          <div>
            <label class="text-xs text-text-muted mb-1 block">备注名 *</label>
            <input v-model="form.name" class="input" placeholder="我的阿里云" />
          </div>
          <div>
            <label class="text-xs text-text-muted mb-1 block">AccessKey ID *</label>
            <input v-model="form.access_key_id" class="input" placeholder="LTAI5t..." />
          </div>
          <div>
            <label class="text-xs text-text-muted mb-1 block">
              AccessKey Secret {{ editTarget ? '（不修改请留空）' : '*' }}
            </label>
            <input v-model="form.access_key_secret" type="password" class="input" placeholder="••••••••" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-xs text-text-muted mb-1 block">地域 ID *</label>
              <input v-model="form.region_id" class="input" placeholder="ap-southeast-1" />
            </div>
            <div>
              <label class="text-xs text-text-muted mb-1 block">站点类型</label>
              <select v-model="form.site_type" class="input">
                <option value="international">国际站</option>
                <option value="china">中国站</option>
              </select>
            </div>
          </div>
          <div>
            <label class="text-xs text-text-muted mb-1 block">实例 ID（用于保活/定时任务）</label>
            <input v-model="form.instance_id" class="input" placeholder="i-..." />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-xs text-text-muted mb-1 block">流量上限 (GB)</label>
              <input v-model.number="form.traffic_limit_gb" type="number" class="input" />
            </div>
            <div>
              <label class="text-xs text-text-muted mb-1 block">熔断阈值 (%)</label>
              <input v-model.number="form.threshold_percent" type="number" class="input" />
            </div>
          </div>
          <div>
            <label class="text-xs text-text-muted mb-1 block">停机模式</label>
            <select v-model="form.shutdown_mode" class="input">
              <option value="StopCharging">节省停机（停止计费）</option>
              <option value="KeepCharging">普通停机（继续计费）</option>
            </select>
          </div>

          <label class="flex items-center gap-2 cursor-pointer">
            <div class="relative">
              <input type="checkbox" v-model="form.keep_alive" class="sr-only" />
              <div :class="form.keep_alive ? 'bg-accent' : 'bg-border'" class="w-9 h-5 rounded-full transition-colors"></div>
              <div :class="form.keep_alive ? 'translate-x-4' : 'translate-x-0.5'" class="absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform"></div>
            </div>
            <span class="text-sm text-text">开启抢占式保活</span>
          </label>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-xs text-text-muted mb-1 block">定时开机</label>
              <input v-model="form.auto_start_time" type="time" class="input" />
            </div>
            <div>
              <label class="text-xs text-text-muted mb-1 block">定时关机</label>
              <input v-model="form.auto_stop_time" type="time" class="input" />
            </div>
          </div>
        </div>

        <div v-if="formError" class="text-xs text-danger bg-danger/10 border border-danger/20 rounded-lg px-3 py-2">
          {{ formError }}
        </div>

        <div class="flex gap-3 pt-2">
          <button @click="showForm = false" class="btn-ghost flex-1">取消</button>
          <button @click="submit" :disabled="submitting" class="btn-primary flex-1">
            {{ submitting ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </Modal>

    <!-- 删除确认 -->
    <Modal v-if="deleteTarget" @close="deleteTarget = null">
      <div class="text-center space-y-4">
        <div class="text-4xl">🗑️</div>
        <div class="font-semibold">确认删除账户？</div>
        <div class="text-sm text-text-muted">{{ deleteTarget.name }}</div>
        <div class="text-xs text-warning bg-warning/10 border border-warning/20 rounded-lg px-3 py-2">
          删除账户后，关联的实例记录也会一并清除
        </div>
        <div class="flex gap-3">
          <button @click="deleteTarget = null" class="btn-ghost flex-1">取消</button>
          <button @click="doDelete" class="btn-danger flex-1">确认删除</button>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useStore } from '../stores'
import Modal from '../components/Modal.vue'

const store = useStore()
const showForm = ref(false)
const editTarget = ref(null)
const deleteTarget = ref(null)
const submitting = ref(false)
const formError = ref('')

const defaultForm = () => ({
  name: '', access_key_id: '', access_key_secret: '',
  region_id: 'ap-southeast-1', site_type: 'international',
  instance_id: '', traffic_limit_gb: 200, threshold_percent: 95,
  shutdown_mode: 'StopCharging', keep_alive: false,
  auto_start_time: null, auto_stop_time: null,
})

const form = ref(defaultForm())

onMounted(() => store.fetchAccounts())

function openAdd() {
  editTarget.value = null
  form.value = defaultForm()
  formError.value = ''
  showForm.value = true
}

function openEdit(acc) {
  editTarget.value = acc
  form.value = { ...acc, access_key_secret: '' }
  formError.value = ''
  showForm.value = true
}

async function submit() {
  formError.value = ''
  if (!form.value.name || !form.value.access_key_id) {
    formError.value = '请填写必填项'
    return
  }
  if (!editTarget.value && !form.value.access_key_secret) {
    formError.value = '请填写 AccessKey Secret'
    return
  }
  submitting.value = true
  try {
    if (editTarget.value) {
      await store.updateAccount(editTarget.value.id, form.value)
    } else {
      await store.createAccount(form.value)
    }
    showForm.value = false
  } catch (e) {
    formError.value = e.response?.data?.detail || '保存失败'
  } finally {
    submitting.value = false
  }
}

function confirmDelete(acc) { deleteTarget.value = acc }
async function doDelete() {
  await store.deleteAccount(deleteTarget.value.id)
  deleteTarget.value = null
}
</script>
