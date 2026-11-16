<script setup lang="ts">
/**
 * 经理请假审批页。
 *
 * 使用 Tab 区分“待审批”和“审批历史”，通过同一个弹窗完成通过和驳回，
 * 审批后同时刷新两组列表，保证状态立即一致。
 */

import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Close, Refresh } from '@element-plus/icons-vue'

import {
  approveLeave,
  getLeaveHistory,
  getPendingLeaves,
  rejectLeave,
  type LeaveRecord,
  type LeaveStatus,
} from '@/api/leave'

const activeTab = ref('pending')
const pendingLeaves = ref<LeaveRecord[]>([])
const historyLeaves = ref<LeaveRecord[]>([])
const loading = ref(false)

const reviewVisible = ref(false)
// reviewAction 决定弹窗标题、按钮颜色以及最终调用的审批接口。
const reviewAction = ref<'approve' | 'reject'>('approve')
const reviewComment = ref('')
const currentLeave = ref<LeaveRecord | null>(null)
const submitting = ref(false)

const statusText: Record<LeaveStatus, string> = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已驳回',
  cancelled: '已撤销',
}

const statusType: Record<
  LeaveStatus,
  'success' | 'warning' | 'danger' | 'info'
> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  cancelled: 'info',
}

function formatDateTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '-'
}

async function loadData() {
  loading.value = true
  try {
    // 待审批和历史列表在用户切换 Tab 时都应保持最新。
    const [pending, history] = await Promise.all([
      getPendingLeaves(),
      getLeaveHistory(),
    ])
    pendingLeaves.value = pending
    historyLeaves.value = history
  } finally {
    loading.value = false
  }
}

function openReview(row: LeaveRecord, action: 'approve' | 'reject') {
  // 每次打开审批弹窗都清空上一次的审批意见。
  currentLeave.value = row
  reviewAction.value = action
  reviewComment.value = ''
  reviewVisible.value = true
}

async function submitReview() {
  if (!currentLeave.value) {
    return
  }

  submitting.value = true
  try {
    // 审批意见不是必填项，空内容统一提交 null。
    const payload = {
      comment: reviewComment.value.trim() || null,
    }
    if (reviewAction.value === 'approve') {
      await approveLeave(currentLeave.value.id, payload)
      ElMessage.success('请假申请已通过')
    } else {
      await rejectLeave(currentLeave.value.id, payload)
      ElMessage.success('请假申请已驳回')
    }
    // 审批成功后重新加载两个列表。
    reviewVisible.value = false
    await loadData()
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="panel" v-loading="loading">
    <div class="panel-heading">
      <div>
        <h2>请假审批</h2>
        <span>待审批 {{ pendingLeaves.length }} 条</span>
      </div>
      <el-button :icon="Refresh" @click="loadData">刷新</el-button>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane :label="`待审批 ${pendingLeaves.length}`" name="pending">
        <el-table :data="pendingLeaves" height="520">
          <el-table-column prop="user_name" label="申请人" width="110" />
          <el-table-column prop="department" label="部门" width="130">
            <template #default="{ row }">
              {{ row.department || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="请假类型" width="110">
            <template #default="{ row }">
              {{ row.leave_type_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="请假日期" min-width="200">
            <template #default="{ row }">
              {{ row.start_date }} 至 {{ row.end_date }}
            </template>
          </el-table-column>
          <el-table-column
            prop="reason"
            label="请假原因"
            min-width="240"
            show-overflow-tooltip
          />
          <el-table-column label="申请时间" width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="170" fixed="right">
            <template #default="{ row }">
              <el-button
                type="success"
                link
                :icon="Check"
                @click="openReview(row, 'approve')"
              >
                通过
              </el-button>
              <el-button
                type="danger"
                link
                :icon="Close"
                @click="openReview(row, 'reject')"
              >
                驳回
              </el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无待审批申请" />
          </template>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="审批历史" name="history">
        <el-table :data="historyLeaves" height="520">
          <el-table-column prop="user_name" label="申请人" width="110" />
          <el-table-column prop="department" label="部门" width="130">
            <template #default="{ row }">
              {{ row.department || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="请假类型" width="110">
            <template #default="{ row }">
              {{ row.leave_type_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="请假日期" min-width="190">
            <template #default="{ row }">
              {{ row.start_date }} 至 {{ row.end_date }}
            </template>
          </el-table-column>
          <el-table-column label="审批状态" width="110">
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="statusType[row.status as LeaveStatus]"
              >
                {{ statusText[row.status as LeaveStatus] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="审批人" width="110">
            <template #default="{ row }">
              {{ row.approver_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="审批意见" min-width="180">
            <template #default="{ row }">
              {{ row.approve_comment || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="审批时间" width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.approve_time) }}
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无审批历史" />
          </template>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="reviewVisible"
      :title="reviewAction === 'approve' ? '通过请假申请' : '驳回请假申请'"
      width="520px"
      destroy-on-close
    >
      <div v-if="currentLeave" class="review-summary">
        <span>
          {{ currentLeave.user_name }} ·
          {{ currentLeave.leave_type_name || '未分类' }}
        </span>
        <span>
          {{ currentLeave.start_date }} 至 {{ currentLeave.end_date }}
        </span>
      </div>
      <el-input
        v-model="reviewComment"
        type="textarea"
        :rows="4"
        maxlength="1000"
        show-word-limit
        :placeholder="
          reviewAction === 'approve'
            ? '可填写审批意见'
            : '可填写驳回原因'
        "
      />
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button
          :type="reviewAction === 'approve' ? 'success' : 'danger'"
          :loading="submitting"
          @click="submitReview"
        >
          {{ reviewAction === 'approve' ? '确认通过' : '确认驳回' }}
        </el-button>
      </template>
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

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.panel-heading h2 {
  margin: 0;
  color: #172033;
  font-size: 18px;
}

.panel-heading span {
  display: block;
  margin-top: 5px;
  color: #64748b;
  font-size: 13px;
}

.review-summary {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
  padding: 12px 14px;
  color: #475569;
  background: #f8fafc;
  border-radius: 6px;
}
</style>
