<script setup lang="ts">
/**
 * 员工公告页。
 *
 * 公告数量较少时采用“一次加载全部 + 前端标题过滤”的方式，
 * 点击表格行或查看按钮时再请求详情接口。
 */

import { computed, onMounted, ref } from 'vue'
import { Refresh, Search, View } from '@element-plus/icons-vue'

import {
  getNoticeDetail,
  getNotices,
  type NoticeRecord,
} from '@/api/notice'

const notices = ref<NoticeRecord[]>([])
const loading = ref(false)
const keyword = ref('')
const detailVisible = ref(false)
const detailLoading = ref(false)
const selectedNotice = ref<NoticeRecord | null>(null)

const filteredNotices = computed(() => {
  // 统一转成小写后比较，支持不区分大小写的标题搜索。
  const value = keyword.value.trim().toLowerCase()
  if (!value) {
    return notices.value
  }
  return notices.value.filter((notice) =>
    notice.title.toLowerCase().includes(value),
  )
})

function formatDateTime(value: string) {
  return value.replace('T', ' ').slice(0, 16)
}

async function loadNotices() {
  loading.value = true
  try {
    notices.value = await getNotices()
  } finally {
    loading.value = false
  }
}

async function openDetail(row: NoticeRecord) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    // 列表只展示摘要，详情单独请求，保证数据是数据库中的最新内容。
    selectedNotice.value = await getNoticeDetail(row.id)
  } finally {
    detailLoading.value = false
  }
}

onMounted(loadNotices)
</script>

<template>
  <section class="panel">
    <div class="toolbar">
      <div class="search-box">
        <el-input
          v-model="keyword"
          :prefix-icon="Search"
          clearable
          placeholder="搜索公告标题"
        />
      </div>
      <el-button :icon="Refresh" @click="loadNotices">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="filteredNotices"
      @row-click="openDetail"
    >
      <el-table-column
        prop="title"
        label="公告标题"
        min-width="260"
        show-overflow-tooltip
      />
      <el-table-column label="发布人" width="140">
        <template #default="{ row }">
          {{ row.author_name || '管理员' }}
        </template>
      </el-table-column>
      <el-table-column label="发布时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            :icon="View"
            @click.stop="openDetail(row)"
          >
            查看
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无公告" />
      </template>
    </el-table>

    <el-dialog
      v-model="detailVisible"
      :title="selectedNotice?.title || '公告详情'"
      width="680px"
    >
      <div v-loading="detailLoading" class="notice-detail">
        <div class="notice-meta">
          <span>{{ selectedNotice?.author_name || '管理员' }}</span>
          <span>
            {{ selectedNotice ? formatDateTime(selectedNotice.created_at) : '' }}
          </span>
        </div>
        <div class="notice-content">
          {{ selectedNotice?.content }}
        </div>
      </div>
    </el-dialog>
  </section>
</template>

<style scoped>
.panel {
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e5eaf0;
  border-radius: 8px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.search-box {
  width: min(360px, 100%);
}

.notice-detail {
  min-height: 180px;
}

.notice-meta {
  display: flex;
  gap: 18px;
  padding-bottom: 14px;
  color: #94a3b8;
  font-size: 13px;
  border-bottom: 1px solid #edf0f4;
}

.notice-content {
  padding-top: 18px;
  color: #303133;
  font-size: 15px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 700px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .search-box {
    width: 100%;
  }
}
</style>
