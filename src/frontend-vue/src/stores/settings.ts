import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getModelProfiles, getCookieStatus, type ModelProfiles } from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const profiles = ref<ModelProfiles>({ items: [], active_id: null })
  const model = computed(
    () => profiles.value.items.find((item) => item.id === profiles.value.active_id) || null,
  )
  const cookieReady = ref(false)
  const refreshModels = async () => {
    profiles.value = (await getModelProfiles()).data
  }
  const refresh = async () => {
    const results = await Promise.allSettled([refreshModels(), getCookieStatus()])
    if (results[1].status === 'fulfilled') cookieReady.value = results[1].value.data.has_cookie
  }
  const clear = () => {
    profiles.value = { items: [], active_id: null }
    cookieReady.value = false
  }
  return { profiles, model, cookieReady, refresh, refreshModels, clear }
})
