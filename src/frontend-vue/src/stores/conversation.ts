import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Conversation } from '@/types'
import * as conversationApi from '@/api/conversation'

export const useConversationStore = defineStore('conversation', () => {
  /** State */
  const conversations = ref<Conversation[]>([])
  const currentConversationId = ref<number | null>(null)
  const isLoading = ref(false)

  /** Computed */
  const currentConversation = computed(() => {
    if (!currentConversationId.value) return null
    return (
      conversations.value.find((c) => c.id === currentConversationId.value) || null
    )
  })

  /** Actions */
  const fetchConversations = async () => {
    isLoading.value = true
    try {
      const response = await conversationApi.listConversations({ limit: 50 })
      conversations.value = response.data
    } catch (error) {
      console.error('Failed to fetch conversations:', error)
    } finally {
      isLoading.value = false
    }
  }

  const selectConversation = (id: number) => {
    currentConversationId.value = id
  }

  const clearCurrentConversation = () => {
    currentConversationId.value = null
  }

  const renameConversation = async (id: number, title: string) => {
    try {
      const response = await conversationApi.updateConversation(id, title)
      const index = conversations.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        conversations.value[index] = response.data
      }
      return true
    } catch (error) {
      console.error('Failed to rename conversation:', error)
      return false
    }
  }

  const deleteConversation = async (id: number) => {
    try {
      await conversationApi.deleteConversation(id)
      conversations.value = conversations.value.filter((c) => c.id !== id)
      if (currentConversationId.value === id) {
        currentConversationId.value = null
      }
      return true
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      return false
    }
  }

  const addConversation = (conversation: Conversation) => {
    // Check if already exists
    const exists = conversations.value.some((c) => c.id === conversation.id)
    if (!exists) {
      conversations.value.unshift(conversation)
    }
  }

  const updateConversationTimestamp = (id: number) => {
    const index = conversations.value.findIndex((c) => c.id === id)
    if (index !== -1) {
      // Move to top of list
      const [conversation] = conversations.value.splice(index, 1)
      conversation.updated_at = new Date().toISOString()
      conversations.value.unshift(conversation)
    }
  }

  return {
    conversations,
    currentConversationId,
    currentConversation,
    isLoading,
    fetchConversations,
    selectConversation,
    clearCurrentConversation,
    renameConversation,
    deleteConversation,
    addConversation,
    updateConversationTimestamp,
  }
})
