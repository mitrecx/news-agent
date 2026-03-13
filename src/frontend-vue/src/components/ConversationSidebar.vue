<template>
  <div :class="['conversation-sidebar', { collapsed: isCollapsed }]">
    <div class="sidebar-header">
      <template v-if="!isCollapsed">
        <h3>对话历史</h3>
        <el-button type="primary" size="small" :icon="Plus" @click="handleNewChat">
          新对话
        </el-button>
      </template>
      <template v-else>
        <el-button type="primary" size="small" :icon="Plus" circle @click="handleNewChat" />
      </template>
      <el-button
        class="collapse-btn"
        :icon="isCollapsed ? DArrowRight : DArrowLeft"
        text
        @click="toggleCollapse"
      />
    </div>

    <div class="sidebar-content" v-show="!isCollapsed">
      <el-empty
        v-if="!conversationStore.isLoading && conversationStore.conversations.length === 0"
        description="暂无对话记录"
        :image-size="80"
      />

      <div v-loading="conversationStore.isLoading" class="conversation-list">
        <div
          v-for="conversation in conversationStore.conversations"
          :key="conversation.id"
          :class="[
            'conversation-item',
            { active: conversation.id === conversationStore.currentConversationId }
          ]"
          @click="handleSelectConversation(conversation.id)"
        >
          <div class="conversation-main">
            <el-icon class="conversation-icon"><ChatDotRound /></el-icon>
            <div class="conversation-info">
              <div class="conversation-title">{{ conversation.title }}</div>
              <div class="conversation-time">{{ formatTime(conversation.updated_at) }}</div>
            </div>
          </div>

          <div class="conversation-actions" @click.stop>
            <el-dropdown trigger="click">
              <el-icon :size="16" class="more-icon"><MoreFilled /></el-icon>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="handleRename(conversation)">
                    <el-icon><Edit /></el-icon>
                    重命名
                  </el-dropdown-item>
                  <el-dropdown-item @click="handleDelete(conversation)" divided>
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>

    <!-- 重命名对话框 -->
    <el-dialog v-model="renameDialogVisible" title="重命名对话" width="400px">
      <el-input
        v-model="newTitle"
        placeholder="请输入新的对话标题"
        maxlength="200"
        show-word-limit
      />
      <template #footer>
        <el-button @click="renameDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  ElMessage,
  ElMessageBox,
  ElButton,
  ElEmpty,
  ElIcon,
  ElDropdown,
  ElDropdownMenu,
  ElDropdownItem,
  ElDialog,
  ElInput,
  vLoading
} from 'element-plus'
import { Plus, ChatDotRound, MoreFilled, Edit, Delete, DArrowLeft, DArrowRight } from '@element-plus/icons-vue'
import { useConversationStore } from '@/stores/conversation'
import { useChatStream } from '@/composables/useChatStream'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import type { Conversation } from '@/types'

const conversationStore = useConversationStore()
const { loadConversation, startNewConversation } = useChatStream()

const renameDialogVisible = ref(false)
const newTitle = ref('')
const renamingConversation = ref<Conversation | null>(null)
const isCollapsed = ref(false)

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

onMounted(() => {
  conversationStore.fetchConversations()
})

const handleNewChat = () => {
  startNewConversation()
}

const handleSelectConversation = async (id: number) => {
  if (conversationStore.currentConversationId === id) return
  await loadConversation(id)
}

const handleRename = (conversation: Conversation) => {
  renamingConversation.value = conversation
  newTitle.value = conversation.title
  renameDialogVisible.value = true
}

const confirmRename = async () => {
  if (!renamingConversation.value) return

  const success = await conversationStore.renameConversation(
    renamingConversation.value.id,
    newTitle.value.trim()
  )

  if (success) {
    ElMessage.success('重命名成功')
    renameDialogVisible.value = false
  } else {
    ElMessage.error('重命名失败')
  }
}

const handleDelete = (conversation: Conversation) => {
  ElMessageBox.confirm(
    `确定要删除对话 "${conversation.title}" 吗？此操作不可恢复。`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(async () => {
      const success = await conversationStore.deleteConversation(conversation.id)
      if (success) {
        ElMessage.success('删除成功')
        if (conversationStore.currentConversationId === conversation.id) {
          startNewConversation()
        }
      } else {
        ElMessage.error('删除失败')
      }
    })
    .catch(() => {
      // User cancelled
    })
}

const formatTime = (time: string) => {
  return formatDistanceToNow(new Date(time), { addSuffix: true, locale: zhCN })
}
</script>

<style scoped>
.conversation-sidebar {
  width: 280px;
  height: 100%;
  background: white;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
}

.conversation-sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  position: relative;
}

.conversation-sidebar.collapsed .sidebar-header {
  justify-content: center;
  padding: 20px 12px;
}

.collapse-btn {
  position: absolute;
  right: -12px;
  top: 24px;
  width: 24px;
  height: 24px;
  padding: 0;
  border-radius: 50%;
  background: white;
  border: 1px solid #e5e7eb;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 10;
  transition: all 0.3s ease;
}

.collapse-btn:hover {
  background: #f9fafb;
  border-color: #667eea;
}

.conversation-sidebar.collapsed .collapse-btn {
  right: -12px;
}

.sidebar-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
  transition: opacity 0.3s ease;
}

.conversation-sidebar.collapsed .sidebar-header h3 {
  display: none;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conversation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.conversation-item:hover {
  background: #f3f4f6;
}

.conversation-item.active {
  background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
  border: 1px solid #667eea30;
}

.conversation-main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.conversation-icon {
  color: #667eea;
  flex-shrink: 0;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-title {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-time {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}

.conversation-actions {
  opacity: 0;
  transition: opacity 0.2s;
}

.conversation-item:hover .conversation-actions {
  opacity: 1;
}

.more-icon {
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.more-icon:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #667eea;
}

/* Scrollbar */
.sidebar-content::-webkit-scrollbar {
  width: 6px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 3px;
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
