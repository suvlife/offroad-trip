<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRouteStore } from '@/stores/route'

const router = useRouter()
const store = useRouteStore()

const vehicleOptions = [
  { value: 'SUV', label: '🚙 SUV', desc: '可走轻度非铺装路' },
  { value: '越野车', label: '🛻 越野车', desc: '可走林道山道' },
  { value: '轿车', label: '🚗 轿车', desc: '只走铺装路面' },
  { value: '新能源', label: '🔋 新能源', desc: '注意续航' },
]

const preferenceOptions = [
  '自然风光', '人文历史', '地方美食', '轻度越野', '摄影打卡', '小众秘境',
]

const today = new Date().toISOString().split('T')[0]

onMounted(() => {
  store.loadForm()
  if (!store.formState.startDate) {
    store.formState.startDate = today
  }
})

function togglePreference(pref) {
  const prefs = store.formState.preferences
  const idx = prefs.indexOf(pref)
  if (idx > -1) {
    prefs.splice(idx, 1)
  } else {
    prefs.push(pref)
  }
  store.saveForm()
}

async function startPlanning() {
  if (!store.formState.departure || !store.formState.destination) {
    alert('请填写出发地和目的地')
    return
  }
  store.saveForm()
  router.push('/planning')
}
</script>

<template>
  <div class="min-h-screen gradient-hero safe-top">
    <!-- Header -->
    <header class="px-5 pt-8 pb-4">
      <div class="flex items-center gap-2 mb-2">
        <span class="text-3xl">🏔️</span>
        <h1 class="text-2xl font-bold text-nature-700">越野智行</h1>
      </div>
      <p class="text-sm text-gray-500">AI驱动的越野自驾游路线规划</p>
    </header>

    <!-- Hero illustration -->
    <div class="px-5 mb-6">
      <div class="rounded-2xl gradient-nature p-6 text-white">
        <p class="text-lg font-semibold mb-1">回归自然 · 轻度越野</p>
        <p class="text-sm text-white/80">
          智能规划越野路线，沿途景点、特色美食、历史故事、抖音视频一站式推荐
        </p>
      </div>
    </div>

    <!-- Form -->
    <div class="px-5 pb-8 space-y-5">
      <!-- Departure & Destination -->
      <div class="card space-y-3">
        <div>
          <label class="text-xs font-medium text-gray-500 mb-1.5 block">出发地</label>
          <input
            v-model="store.formState.departure"
            @change="store.saveForm()"
            type="text"
            placeholder="如：北京"
            class="input-field"
          />
        </div>
        <div class="flex justify-center -my-1">
          <span class="text-nature-500 text-xl">⬇️</span>
        </div>
        <div>
          <label class="text-xs font-medium text-gray-500 mb-1.5 block">目的地</label>
          <input
            v-model="store.formState.destination"
            @change="store.saveForm()"
            type="text"
            placeholder="如：漠河"
            class="input-field"
          />
        </div>
      </div>

      <!-- Date & Days -->
      <div class="card grid grid-cols-2 gap-3">
        <div>
          <label class="text-xs font-medium text-gray-500 mb-1.5 block">出发日期</label>
          <input
            v-model="store.formState.startDate"
            @change="store.saveForm()"
            type="date"
            :min="today"
            class="input-field"
          />
        </div>
        <div>
          <label class="text-xs font-medium text-gray-500 mb-1.5 block">行程天数</label>
          <div class="flex items-center gap-2">
            <button
              @click="store.formState.days = Math.max(1, store.formState.days - 1); store.saveForm()"
              class="w-10 h-10 rounded-lg bg-gray-100 text-lg font-bold text-gray-600 active:bg-gray-200"
            >−</button>
            <span class="flex-1 text-center text-lg font-semibold text-gray-800">{{ store.formState.days }}</span>
            <button
              @click="store.formState.days = Math.min(30, store.formState.days + 1); store.saveForm()"
              class="w-10 h-10 rounded-lg bg-gray-100 text-lg font-bold text-gray-600 active:bg-gray-200"
            >+</button>
          </div>
        </div>
      </div>

      <!-- Vehicle Type -->
      <div class="card">
        <label class="text-xs font-medium text-gray-500 mb-2 block">车辆类型</label>
        <div class="grid grid-cols-2 gap-2">
          <button
            v-for="v in vehicleOptions"
            :key="v.value"
            @click="store.formState.vehicleType = v.value; store.saveForm()"
            :class="[
              'rounded-xl p-3 text-left transition-all border-2',
              store.formState.vehicleType === v.value
                ? 'border-nature-500 bg-nature-50'
                : 'border-gray-100 bg-white'
            ]"
          >
            <div class="font-semibold text-sm text-gray-800">{{ v.label }}</div>
            <div class="text-xs text-gray-400 mt-0.5">{{ v.desc }}</div>
          </button>
        </div>
      </div>

      <!-- People & Budget -->
      <div class="card grid grid-cols-3 gap-3">
        <div>
          <label class="text-xs font-medium text-gray-500 mb-1.5 block">成人</label>
          <input
            v-model.number="store.formState.adults"
            @change="store.saveForm()"
            type="number" min="1" max="20"
            class="input-field text-center"
          />
        </div>
        <div>
          <label class="text-xs font-medium text-gray-500 mb-1.5 block">儿童</label>
          <input
            v-model.number="store.formState.children"
            @change="store.saveForm()"
            type="number" min="0" max="20"
            class="input-field text-center"
          />
        </div>
        <div>
          <label class="text-xs font-medium text-gray-500 mb-1.5 block">预算(元)</label>
          <input
            v-model.number="store.formState.budget"
            @change="store.saveForm()"
            type="number" min="0" step="1000"
            class="input-field text-center"
          />
        </div>
      </div>

      <!-- Preferences -->
      <div class="card">
        <label class="text-xs font-medium text-gray-500 mb-2 block">出行偏好</label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="pref in preferenceOptions"
            :key="pref"
            @click="togglePreference(pref)"
            :class="[
              'tag text-sm px-3 py-1.5 transition-all',
              store.formState.preferences.includes(pref)
                ? 'tag-nature'
                : 'bg-gray-100 text-gray-400'
            ]"
          >
            {{ pref }}
          </button>
        </div>
      </div>

      <!-- Start Button -->
      <button
        @click="startPlanning"
        :disabled="!store.formState.departure || !store.formState.destination"
        class="btn-primary w-full text-lg flex items-center justify-center gap-2"
      >
        <span>🗺️</span>
        <span>开始规划路线</span>
      </button>
    </div>
  </div>
</template>
