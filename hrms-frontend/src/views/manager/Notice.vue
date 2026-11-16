<script setup lang="ts">
/**
 * 经理公告管理页。
 *
 * 经理可以发布、编辑、删除公告，并通过右侧抽屉查看详情。
 * 列表搜索同样在前端完成，适合当前数据规模。
 */

import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import { Delete, Edit, Plus, Refresh, Search, View } from '@element-plus/icons-vue'

import {
  createNotice,
  deleteNotice,
  getNoticeDetail,
  getNotices,
  updateNotice,
  type NoticeRecord,
} from '@/api/notice'

const notices = ref<NoticeRecord[]>([])
const loading = ref(false)
const keyword = ref('')
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const submitting = ref(false)
const detailVisible = ref(false)
const detailLoading = ref(false)
const selectedNotice = ref<NoticeRecord | null>(null)

const form = reactive({
  title: '',
  content: '',
})

const rules: FormRules = {
  title: [
    { required: true, message: '请输入公告标题', trigger: 'blur' },
  ],
  content: [
    { required: true, message: '请输入公告内容', trigger: 'blur' },
  ],
}

const filteredNotices = computed(() => {
  // 关键词为空时返回全部公告，否则按标题包含关系过滤。
  const value = keyword.value.trim().toLowerCase()
  if (!value) {
    return notices.value
  }
  return notices.value.filter((notice) =>
    notice.title.toLowerCase().includes(value),
  )
})

const dialogTitle = computed(() =>
  dialogMode.value === 'create' ? '发布公告' : '编辑公告',
)

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

async function openCreateDialog() {
  dialogMode.value = 'create'
  editingId.value = null
  form.title = ''
  form.content = ''
  dialogVisible.value = true
  // 等弹窗渲染完成后清除上一次校验提示。
  await nextTick()
  formRef.value?.clearValidate()
}

async function openEditDialog(row: NoticeRecord) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  form.title = row.title
  form.content = row.content
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

async function submitNotice() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      // 发布时提交完整标题和内容。
      await createNotice({
        title: form.title.trim(),
        content: form.content.trim(),
      })
      ElMessage.success('公告已发布')
    } else if (editingId.value !== null) {
      // 编辑复用同一表单，只更新当前公告。
      await updateNotice(editingId.value, {
        title: form.title.trim(),
        content: form.content.trim(),
      })
      ElMessage.success('公告已更新')
    }
    dialogVisible.value = false
    await loadNotices()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: NoticeRecord) {
  try {
    await ElMessageBox.confirm(
      `确定删除公告“${row.title}”吗？`,
      '删除公告',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    // 用户取消删除时直接结束。
    return
  }

  const result = await deleteNotice(row.id)
  ElMessage.success(result.message)
  await loadNotices()
}

async function openDetail(row: NoticeRecord) {
  // 详情通过独立接口获取，保证查看的是最新公告内容。
  detailVisible.value = true
  detailLoading.value = true
  try {
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
      <div class="toolbar-actions">
        <el-button :icon="Refresh" @click="loadNotices">刷新</el-button>
        <el-button
          type="primary"
          :icon="Plus"
          @click="openCreateDialog"
        >
          发布公告
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="filteredNotices" height="560">
      <el-table-column
        prop="title"
        label="公告标题"
        min-width="260"
        show-overflow-tooltip
      />
      <el-table-column label="发布人" width="130">
        <template #default="{ row }">
          {{ row.author_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="发布时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            :icon="View"
            @click="openDetail(row)"
          >
            查看
          </el-button>
          <el-button
            type="primary"
            link
            :icon="Edit"
            @click="openEditDialog(row)"
          >
            编辑
          </el-button>
          <el-button
            type="danger"
            link
            :icon="Delete"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无公告" />
      </template>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="680px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
      >
        <el-form-item label="公告标题" prop="title">
          <el-input
            v-model="form.title"
            maxlength="200"
            show-word-limit
            placeholder="请输入公告标题"
          />
        </el-form-item>
        <el-form-item label="公告内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="9"
            maxlength="10000"
            show-word-limit
            placeholder="请输入公告内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="submitNotice"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="detailVisible"
      :title="selectedNotice?.title || '公告详情'"
      size="520px"
    >
      <div v-loading="detailLoading" class="detail-content">
        <div class="detail-meta">
          <span>{{ selectedNotice?.author_name || '-' }}</span>
          <span>
            {{ selectedNotice ? formatDateTime(selectedNotice.created_at) : '' }}
          </span>
        </div>
        <div class="detail-body">
          {{ selectedNotice?.content }}
        </div>
      </div>
    </el-drawer>
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

.toolbar-actions {
  display: flex;
  gap: 10px;
}

.detail-content {
  min-height: 200px;
}

.detail-meta {
  display: flex;
  gap: 18px;
  padding-bottom: 14px;
  color: #94a3b8;
  font-size: 13px;
  border-bottom: 1px solid #edf0f4;
}

.detail-body {
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

  .toolbar-actions {
    justify-content: flex-end;
  }
}
</style>
