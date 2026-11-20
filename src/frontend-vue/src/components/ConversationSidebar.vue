<template>
  <aside class="conversation-sidebar" :class="{ expanded: mobileOpen }">
    <div class="conversation-sidebar-top">
      <span>对话记录</span
      ><el-button :icon="Plus" aria-label="新对话" size="small" :disabled="busy" @click="newChat"
        >新对话</el-button
      ><button
        class="history-toggle icon-button"
        aria-label="切换对话历史"
        :aria-expanded="mobileOpen"
        @click="mobileOpen = !mobileOpen"
      >
        <el-icon><Clock /></el-icon>
      </button>
    </div>
    <div class="conversation-search">
      <el-input
        v-model="search"
        placeholder="查找对话"
        :prefix-icon="Search"
        clearable
        size="small"
      />
    </div>
    <div class="conversation-history">
      <span class="history-label">最近的对话</span>
      <p v-if="!filtered.length" class="history-empty">
        {{ search ? '没有匹配的对话' : '你的对话会保存在这里' }}
      </p>
      <div
        v-for="item in filtered"
        :key="item.id"
        class="history-item"
        :class="{ active: store.currentConversationId === item.id }"
      >
        <button :disabled="busy" @click="select(item.id)">
          <el-icon><ChatLineRound /></el-icon><span>{{ item.title }}</span></button
        ><el-dropdown trigger="click"
          ><button
            class="history-more icon-button"
            :aria-label="`管理对话 ${item.title}`"
            :disabled="busy"
          >
            <el-icon><MoreFilled /></el-icon></button
          ><template #dropdown
            ><el-dropdown-menu
              ><el-dropdown-item @click="rename(item)">重命名</el-dropdown-item
              ><el-dropdown-item @click="remove(item)">删除</el-dropdown-item></el-dropdown-menu
            ></template
          ></el-dropdown
        >
      </div>
    </div>
    <footer>
      <el-icon><Lock /></el-icon>对话记录仅对你可见
    </footer>
  </aside>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, ChatLineRound, MoreFilled, Lock, Clock } from '@element-plus/icons-vue'
import { useConversationStore } from '@/stores/conversation'
import type { Conversation } from '@/types'
defineProps<{ busy: boolean }>()
const emit = defineEmits<{ new: []; select: [id: number] }>()
const store = useConversationStore()
const search = ref('')
const mobileOpen = ref(false)
const newChat = () => {
  mobileOpen.value = false
  emit('new')
}
const select = (id: number) => {
  mobileOpen.value = false
  emit('select', id)
}
const filtered = computed(() =>
  store.conversations.filter((item) =>
    item.title.toLowerCase().includes(search.value.toLowerCase()),
  ),
)
const rename = async (item: Conversation) => {
  try {
    const result = await ElMessageBox.prompt('为这段对话取个名字', '重命名对话', {
      inputValue: item.title,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValidator: (value) =>
        (!!value?.trim() && value.length <= 200) || '请输入 1 到 200 字的标题',
    })
    if (await store.renameConversation(item.id, result.value.trim()))
      ElMessage.success('对话已重命名')
  } catch {
    /* 用户取消 */
  }
}
const remove = async (item: Conversation) => {
  try {
    await ElMessageBox.confirm(`确定删除「${item.title}」及其消息？`, '删除对话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  const wasCurrent = store.currentConversationId === item.id
  if (await store.deleteConversation(item.id)) {
    if (wasCurrent) emit('new')
    ElMessage.success('对话已删除')
  }
}
</script>
<style scoped>
.history-toggle {
  display: none;
}
.conversation-sidebar {
  width: 220px;
  background: #fbfcfd;
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.conversation-sidebar-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 17px 18px;
}
.conversation-sidebar-top > span {
  font-size: 11px;
  color: #788c96;
}
.conversation-sidebar-top .el-button {
  background: white;
  color: #698a7d;
  border-color: #dfe9e3;
  font-size: 9px;
  padding: 0 9px;
  height: 27px;
}
.conversation-search {
  padding: 0 16px 23px;
}
.conversation-search :deep(.el-input__wrapper) {
  background: #f2f5f7;
  box-shadow: none;
  font-size: 10px;
  height: 29px;
}
.history-label {
  font-size: 9px;
  display: block;
  color: #acb8be;
  padding: 0 18px 15px;
}
.conversation-history {
  flex: 1;
  overflow-y: auto;
}
.history-empty {
  font-size: 10px;
  color: #afbbc1;
  padding: 10px 18px;
  line-height: 1.8;
}
.history-item {
  display: flex;
  margin: 3px 10px;
  border-radius: 7px;
  align-items: center;
  padding: 0 5px;
}
.history-item.active {
  background: #eaf2ee;
}
.history-item > button {
  border: none;
  background: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 4px 12px 6px;
  min-width: 0;
  flex: 1;
  color: #8c9ca5;
  font-size: 10px;
  text-align: left;
}
.history-item.active > button {
  color: #5c8a77;
}
.history-item > button span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-more {
  width: 23px;
  font-size: 10px;
  opacity: 0;
}
.history-item:hover .history-more,
.history-item.active .history-more,
.history-more:focus-visible {
  opacity: 1;
}
.conversation-sidebar footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 8px;
  color: #b0bdc3;
  padding: 20px 10px;
  border-top: 1px solid #eff2f4;
}
@media (max-width: 1100px) {
  .conversation-sidebar {
    width: 185px;
  }
  .conversation-sidebar-top {
    padding-left: 14px;
    padding-right: 14px;
  }
}
@media (max-width: 900px) {
  .conversation-sidebar {
    width: 54px;
    align-items: center;
  }
  .conversation-sidebar-top > span,
  .conversation-search,
  .conversation-history,
  .conversation-sidebar footer {
    display: none;
  }
  .conversation-sidebar-top {
    padding: 15px 8px;
  }
  .conversation-sidebar-top :deep(.el-button span) {
    display: none;
  }
  .conversation-sidebar-top :deep(.el-button .el-icon) {
    margin: 0;
  }
  .conversation-sidebar-top .el-button {
    width: 31px;
    height: 31px;
    padding: 7px;
  }
}
@media (max-width: 900px) {
  .history-toggle {
    display: inline-grid;
    margin-top: 8px;
  }
  .conversation-sidebar-top {
    flex-direction: column;
  }
  .conversation-sidebar.expanded {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 230px;
    align-items: stretch;
    z-index: 15;
    box-shadow: 10px 0 30px #20364212;
  }
  .expanded .conversation-sidebar-top {
    flex-direction: row;
    padding: 15px;
    gap: 10px;
  }
  .expanded .conversation-sidebar-top > span {
    display: block;
  }
  .expanded .history-toggle {
    margin-top: 0;
  }
  .expanded .conversation-search,
  .expanded .conversation-history {
    display: block;
  }
  .expanded footer {
    display: flex;
  }
}
</style>
