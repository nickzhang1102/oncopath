<template>
  <div class="medical-record-container">
    <!-- 动态背景元素 -->
    <background-animation />

    <back-button title="病情记录" />

    <!-- 未选择患者时的空状态 -->
    <div v-if="!currentPatientId" class="empty-patient">
      <van-empty description="请先选择患者" image="search">
        <van-button type="primary" class="bottom-button" @click="router.push('/home/patient-management')">
          选择患者
        </van-button>
      </van-empty>
    </div>

    <template v-else>
    <!-- 报告开关区域 -->
    <div class="switch-section">
      <div class="switch-card">
        <div class="switch-item">
          <span class="switch-label">显示报告</span>
          <van-switch v-model="showReports" size="22px" @change="onSwitchChange" />
        </div>
        <div class="switch-hint">开启后将在记录中显示相关报告</div>
      </div>
    </div>

    <!-- 折叠面板区域 -->
    <div class="collapse-section">
      <van-collapse v-model="activeNames" accordion>
        <van-collapse-item
          v-for="(group, index) in groupedRecords"
          :key="group.key"
          :name="group.key"
          :title="group.title"
        >
          <!-- 混合显示病情记录和报告项 -->
          <div
            v-for="item in group.items"
            :key="item.key"
            :class="item.type === 'record' ? 'record-item' : 'report-item'"
            @click="item.type === 'report' ? navigateToReport(item) : null"
          >
            <div class="item-header">
              <div class="item-title">{{ item.title }}</div>
              <div class="item-date">{{ item.displayDate || item.record_date }}</div>
            </div>

            <!-- 病情记录内容 -->
            <div v-if="item.type === 'record'" class="record-content">
              <div class="record-description">{{ item.description }}</div>
              <div class="record-footer">
                <div class="record-status">
                  {{ item.status }}
                </div>
                <div class="record-actions">
                  <van-button size="mini" type="primary" @click="handleEdit(item)">编辑</van-button>
                  <van-button size="mini" type="danger" @click="handleDelete(item)">删除</van-button>
                </div>
              </div>
            </div>

            <!-- 报告内容 -->
            <div v-else class="report-content">
              <div class="report-type">{{ item.reportType }}</div>
              <div class="report-hint">点击查看详情</div>
            </div>
          </div>
        </van-collapse-item>
      </van-collapse>
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-if="groupedRecords.length === 0">
      <div class="empty-icon"><van-icon name="edit" /></div>
      <div class="empty-title">暂无病情记录</div>
      <div class="empty-subtitle">您还没有任何病情记录</div>
    </div>

    <!-- 添加按钮 -->
    <van-floating-bubble
      v-if="!isDesktop"
      axis="xy"
      icon="plus"
      @click="handleAdd"
      :gap="floatingBubbleGap"
    />

    <!-- 编辑弹窗 -->
    <van-dialog
      v-model:show="showEditDialog"
      :title="editMode === 'add' ? '添加病情记录' : '编辑病情记录'"
      show-cancel-button
      :before-close="beforeDialogClose"
      @confirm="handleSave"
      @cancel="handleCancel"
      :confirm-button-loading="saving"
    >
      <div class="edit-form">
        <van-field
          v-model="editForm.record_name"
          label="记录名称"
          placeholder="请输入记录名称"
          required
        />
        <van-field
          v-model="editForm.record_date"
          label="记录日期"
          placeholder="请选择日期"
          readonly
          clickable
          @click="showDatePicker = true"
          required
        />
        <van-field
          v-model="editForm.record_info"
          label="记录信息"
          type="textarea"
          placeholder="请输入详细信息"
          rows="4"
          required
        />
        <van-field
          v-model="editForm.patient_status"
          label="患者状态"
          placeholder="请输入患者状态"
        />
        <van-field
          v-model="editForm.comment"
          label="备注"
          type="textarea"
          placeholder="请输入备注（可选）"
        />
      </div>
    </van-dialog>

    <!-- 日期选择器 -->
    <van-popup v-model:show="showDatePicker" :position="isDesktop ? 'center' : 'bottom'" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-date-picker
        v-model="currentDate"
        :min-date="minDate"
        :max-date="maxDate"
        title="选择日期"
        @confirm="onDateConfirm(currentDate)"
        @cancel="showDatePicker = false"
      />
    </van-popup>
    </template>
  </div>
</template>

<script setup>
import BackButton from '@/components/index-detail/BackButton.vue';
import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated, watch, nextTick, defineAsyncComponent } from 'vue';
const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'));
import { useRouter } from 'vue-router';
import { usePatientStore } from '@/stores/patient';
import { showToast, showConfirmDialog } from 'vant';
import { medicalApi } from '@/api/medical';
import { useResponsive } from '@/composables/useResponsive';
import { EXAM_TYPE_LABELS } from '@/styles/constants';

const router = useRouter();
const patientStore = usePatientStore();
const { isDesktop, floatingBubbleGap } = useResponsive();

// 从Pinia获取当前病人信息
const currentPatient = computed(() => patientStore.currentPatient);
const currentPatientId = computed(() => currentPatient.value?.patient_id);

// 响应式数据
const showReports = ref(false);
const reportList = ref([]);
const examList = ref([]);
const loading = ref(false);
const activeNames = ref('');
const minDate = ref(new Date(2000, 0, 1));
const maxDate = ref(new Date());

// 编辑相关数据
const showEditDialog = ref(false);
const showDatePicker = ref(false);
const editMode = ref('add'); // 'add' 或 'edit'
const saving = ref(false);
const currentDate = ref([new Date().getFullYear(), new Date().getMonth() + 1, new Date().getDate()]);
const editForm = ref({
  record_id: null,
  record_name: '',
  record_date: '',
  record_info: '',
  patient_status: '',
  record_type: '1',
  comment: ''
});

// 病情记录数据（从后端获取）
const medicalRecords = ref([]);

// 月份分组辅助函数
function getMonthKey(dateStr) {
  if (!dateStr) return null
  return dateStr.substring(0, 7)
}

function getMonthTitle(monthKey) {
  const [y, m] = monthKey.split('-')
  return `${y}年${parseInt(m)}月`
}

function addToGroup(groups, monthKey, item) {
  if (!groups[monthKey]) {
    groups[monthKey] = { key: monthKey, title: getMonthTitle(monthKey), items: [] }
  }
  groups[monthKey].items.push(item)
}

// 分组数据
const groupedRecords = computed(() => {
  try {
    const groups = {}

    // 按月份分组病情记录
    for (const record of medicalRecords.value || []) {
      const monthKey = getMonthKey(record.record_date)
      if (!monthKey) continue
      addToGroup(groups, monthKey, {
        key: `record-${record.record_id}`,
        type: 'record',
        id: record.record_id,
        title: record.record_name || '未命名记录',
        date: record.record_date,
        displayDate: formatDate(record.record_date),
        description: record.record_info || '',
        status: record.patient_status || '状态未知'
      })
    }

    // 开启报告显示时，合并检验/检查报告
    if (showReports.value) {
      for (const report of reportList.value || []) {
        const monthKey = getMonthKey(report.medical_date)
        if (!monthKey) continue
        addToGroup(groups, monthKey, {
          key: `report-${report.medical_id}`,
          type: 'report',
          id: report.id,
          title: report.hospital || '检验报告',
          date: report.medical_date,
          displayDate: formatDate(report.medical_date),
          reportType: '检验报告',
          routeName: 'reportView',
          data: report
        })
      }

      for (const exam of examList.value || []) {
        const monthKey = getMonthKey(exam.medical_date)
        if (!monthKey) continue
        addToGroup(groups, monthKey, {
          key: `exam-${exam.exam_id}`,
          type: 'report',
          id: exam.id,
          title: exam.exam_type_name || EXAM_TYPE_LABELS[exam.exam_type] || exam.exam_type || '检查报告',
          date: exam.medical_date,
          displayDate: formatDate(exam.medical_date),
          reportType: '检查报告',
          routeName: 'examReportView',
          data: exam
        })
      }
    }

    // 组内按日期倒序，组间按月份倒序
    return Object.values(groups)
      .map(group => ({
        ...group,
        items: group.items.sort((a, b) => new Date(b.date) - new Date(a.date))
      }))
      .sort((a, b) => b.key.localeCompare(a.key))
  } catch (error) {
    console.error('Error in groupedRecords computed:', error)
    return []
  }
})

// 方法
const onSwitchChange = async (value) => {
  if (value) {
    await loadReports();
  }
};

const loadReports = async () => {
  try {
    loading.value = true;

    // 获取检验报告（checks/query）
    const reportResponse = await medicalApi.getMedicalReportList(currentPatientId.value, { limit: 50, offset: 0 });
    if (reportResponse) {
      reportList.value = Array.isArray(reportResponse) ? reportResponse : [];
    }

    // 获取检查报告（exams/query）
    const examResponse = await medicalApi.getExamReports(currentPatientId.value, { limit: 50, offset: 0 });
    if (examResponse) {
      examList.value = Array.isArray(examResponse) ? examResponse : [];
    }
  } catch (error) {
    console.error('获取报告数据失败:', error);
    showToast('获取报告数据失败');
  } finally {
    loading.value = false;
  }
};

const navigateToReport = (report) => {
  if (report.routeName === 'reportView') {
    // 跳转到检验报告并显示详情
    router.push({
      name: report.routeName,
      query: {
        showDetail: 'true',  // 确保是字符串
        medicalId: String(report.data.medical_id)  // 确保是字符串
      }
    });
  } else {
    router.push({ name: report.routeName });
  }
};

// 设置默认展开最新时间
const setDefaultActivePanel = () => {
  try {
    if (groupedRecords.value && groupedRecords.value.length > 0 && groupedRecords.value[0].key) {
      activeNames.value = groupedRecords.value[0].key;
    }
  } catch (error) {
    console.error('Error setting default active panel:', error);
  }
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    return `${date.getMonth() + 1}月${date.getDate()}日`;
  } catch (error) {
    console.error('Date formatting error:', error);
    return dateString;
  }
};

// 格式化日期为 YYYY-MM-DD（用于表单和日期选择器）
const formatDateISO = (date) => {
  if (!date) return '';
  if (typeof date === 'string') {
    date = new Date(date);
  }
  if (!(date instanceof Date) || isNaN(date.getTime())) {
    return '';
  }
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

// 病情记录CRUD方法
const loadMedicalRecords = async () => {
  try {
    loading.value = true;
    // 无患者时跳过请求
    if (!currentPatientId.value) {
      medicalRecords.value = [];
      return;
    }
    const response = await medicalApi.getMedicalRecords(currentPatientId.value);
    if (response && Array.isArray(response)) {
      medicalRecords.value = response;
    } else if (response && response.data) {
      medicalRecords.value = response.data;
    }
  } catch (error) {
    console.error('获取病情记录失败:', error);
    showToast('获取病情记录失败');
  } finally {
    loading.value = false;
  }
};

const handleAdd = () => {
  editMode.value = 'add';

  // 重置表单数据
  editForm.value = {
    record_id: null,
    record_name: '',
    record_date: '',
    record_info: '',
    patient_status: '',
    record_type: '1',
    comment: ''
  };

  // 重置日期选择器为当前日期
  const today = new Date();
  currentDate.value = [today.getFullYear(), today.getMonth() + 1, today.getDate()];

  showEditDialog.value = true;
};

const handleEdit = (item) => {
  editMode.value = 'edit';
  // 从原始记录中获取完整数据
  const originalRecord = medicalRecords.value.find(record => record.record_id === item.id);

  // 设置表单数据
  editForm.value = {
    record_id: item.id,
    record_name: item.title,
    record_date: item.date,
    record_info: item.description,
    patient_status: item.status,
    record_type: originalRecord?.record_type || '1',
    comment: originalRecord?.comment || ''
  };

  // 设置日期选择器的初始值
  if (item.date) {
    try {
      const dateObj = new Date(item.date);
      if (!isNaN(dateObj.getTime())) {
        currentDate.value = [dateObj.getFullYear(), dateObj.getMonth() + 1, dateObj.getDate()];
      }
    } catch (error) {
      console.error('Error parsing date:', error);
    }
  }

  showEditDialog.value = true;
};

const handleDelete = async (item) => {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: '确定要删除这条病情记录吗？'
    });

    loading.value = true;
    await medicalApi.deleteMedicalRecord(item.id);
    showToast('删除成功');

    // 重新加载数据
    await loadMedicalRecords();
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error);
      showToast('删除失败');
    }
  } finally {
    loading.value = false;
  }
};

const handleSave = async () => {
  if (!editForm.value.record_name || !editForm.value.record_date || !editForm.value.record_info) {
    showToast('请填写完整信息');
    return;
  }

  try {
    saving.value = true;

    const recordData = {
      patient_id: currentPatientId.value,
      record_name: editForm.value.record_name,
      record_date: editForm.value.record_date,
      record_info: editForm.value.record_info,
      record_type: editForm.value.record_type,
      patient_status: editForm.value.patient_status,
      comment: editForm.value.comment
    };

    if (editMode.value === 'add') {
      const response = await medicalApi.createMedicalRecord(recordData);
      if (response) {
        showToast('添加成功');
        // 重新加载数据
        await loadMedicalRecords();
      }
    } else {
      await medicalApi.updateMedicalRecord(editForm.value.record_id, recordData);
      showToast('修改成功');
      // 重新加载数据
      await loadMedicalRecords();
    }

    showEditDialog.value = false;
  } catch (error) {
    console.error('保存失败:', error);
    showToast('保存失败');
  } finally {
    saving.value = false;
  }
};

const beforeDialogClose = (action) => {
  if (action === 'confirm') {
    // 验证失败时不关闭 dialog
    if (!editForm.value.record_name || !editForm.value.record_date || !editForm.value.record_info) {
      showToast('请填写完整信息');
      return false;
    }
  }
  return true;
};

const handleCancel = () => {
  showEditDialog.value = false;
  editForm.value = {
    record_id: null,
    record_name: '',
    record_date: '',
    record_info: '',
    patient_status: '',
    record_type: '1',
    comment: ''
  };
};

const onDateConfirm = (value) => {
  try {
    let dateValues;

    // Handle object format from Vant date picker
    if (value && typeof value === 'object' && value.selectedValues) {
      dateValues = value.selectedValues;
    } else if (Array.isArray(value)) {
      dateValues = value;
    } else if (value instanceof Date) {
      editForm.value.record_date = formatDateISO(value);
      showDatePicker.value = false;
      return;
    } else {
      console.error('Unexpected date format:', value);
      editForm.value.record_date = formatDateISO(new Date());
      showDatePicker.value = false;
      return;
    }

    // Convert array values to numbers and create Date object
    if (Array.isArray(dateValues) && dateValues.length >= 3) {
      const year = parseInt(dateValues[0]);
      // Month is already correct in the selectedValues array (1-12)
      // But JavaScript Date expects 0-11, so we subtract 1
      const month = parseInt(dateValues[1]) - 1;
      const day = parseInt(dateValues[2]);

      if (!isNaN(year) && !isNaN(month) && !isNaN(day)) {
        const date = new Date(year, month, day);
        editForm.value.record_date = formatDateISO(date);
      } else {
        console.error('Invalid date values:', dateValues);
        editForm.value.record_date = formatDateISO(new Date());
      }
    }
  } catch (error) {
    console.error('Error processing date:', error);
    editForm.value.record_date = formatDateISO(new Date());
  }

  showDatePicker.value = false;
};

// 监听分组数据变化，设置默认展开
let watchStopHandle = null;

onMounted(async () => {
  // 加载病情记录数据
  await loadMedicalRecords();

  // 页面加载时设置默认展开最新时间
  setDefaultActivePanel();

  // 设置监听器
  watchStopHandle = watch(groupedRecords, (newVal) => {
    if (newVal && newVal.length > 0) {
      nextTick(() => {
        setDefaultActivePanel();
      });
    }
  }, { immediate: false });
});

// 监听病人切换事件
watch(() => currentPatient.value?.patient_id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    await loadMedicalRecords();
    // 重新设置默认展开面板
    nextTick(() => {
      setDefaultActivePanel();
    });
  }
});

// keepAlive激活时
onActivated(() => {
  // 重新设置默认展开面板
  nextTick(() => {
    setDefaultActivePanel();
  });
});

// keepAlive失活时
onDeactivated(() => {
  // 可以在这里保存一些状态，但不清理数据
});

onUnmounted(() => {
  // 清理监听器
  if (watchStopHandle) {
    watchStopHandle();
    watchStopHandle = null;
  }

  // 清理数据
  activeNames.value = '';
  reportList.value = [];
  examList.value = [];
});
</script>

<style scoped>
.medical-record-container {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-primary) 0%, var(--border-color) 100%);
  padding: 20px;
  padding-bottom: var(--safe-bottom);
  position: relative;
}

/* 开关区域 */
.switch-section {
  position: relative;
  z-index: 2;
  margin-bottom: 20px;
}

.switch-card {
  background: var(--bg-surface-alpha);
  padding: 10px 15px;
  border-radius: 8px;
  box-shadow: 0 4px 10px var(--primary-alpha-8);
  backdrop-filter: blur(10px);
}

.switch-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.switch-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--primary-color);
}

.switch-hint {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 折叠面板区域 */
.collapse-section {
  position: relative;
  z-index: 2;
  height: calc(100vh - 200px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

/* 通用项目样式 */
.record-item, .report-item {
  background: var(--bg-surface-alpha);
  margin-bottom: 12px;
  padding: 15px;
  border-radius: 12px;
  box-shadow: 0 4px 12px var(--primary-alpha-8);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.record-item {
  border-left: 4px solid var(--primary-color);
}

.report-item {
  border-left: 3px solid var(--primary-dark);
  cursor: pointer;
  padding: 10px 12px;
  margin-bottom: 8px;
  opacity: 0.85;
}

.report-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px var(--primary-alpha-12);
  opacity: 1;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.item-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
}

.item-date {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 报告项标题样式调整 */
.report-item .item-title {
  font-size: 13px;
  font-weight: 500;
}

.report-item .item-date {
  font-size: 12px;
}

.record-content {
  margin-top: 8px;
}

.record-description {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.5;
  margin-bottom: 8px;
}

.record-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.record-status {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.record-actions {
  display: flex;
  gap: 8px;
}


/* 报告内容样式 */
.report-content {
  margin-top: 6px;
}

.report-type {
  font-size: 12px;
  color: var(--primary-dark);
  margin-bottom: 2px;
}

.report-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* 空状态 */
/* 患者未选择空状态 */
.empty-patient {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.bottom-button {
  min-width: 160px;
  padding: 12px 24px;
}

.empty-state {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 60px 20px;
  color: var(--primary-alpha-80);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon .van-icon {
  font-size: 48px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.empty-subtitle {
  font-size: 14px;
  opacity: 0.7;
}

/* 折叠面板样式覆盖 */
:deep(.van-collapse-item__title) {
  background: var(--bg-surface-alpha);
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
}

:deep(.van-collapse-item__wrapper) {
  background: transparent;
}

:deep(.van-collapse-item__content) {
  padding: 0;
  background: transparent;
}

:deep(.van-collapse-item) {
  background: var(--bg-surface-alpha);
  margin-bottom: 15px;
  border-radius: 12px;
  box-shadow: 0 4px 12px var(--primary-alpha-8);
  backdrop-filter: blur(10px);
  overflow: hidden;
}

/* 编辑表单样式 */
.edit-form {
  padding: 20px 0;
}

.edit-form .van-field {
  margin-bottom: 16px;
}

/* 浮动按钮样式覆盖 */
:deep(.van-floating-bubble) {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  box-shadow: 0 4px 12px var(--primary-alpha-40);
}

:deep(.van-floating-bubble:hover) {
  transform: scale(1.1);
  box-shadow: 0 6px 16px var(--primary-alpha-60);
}

/* 按钮主题色覆盖 */
:deep(.van-button--primary) {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

:deep(.van-button--danger) {
  background: var(--danger-color);
  border-color: var(--danger-color);
}

/* 开关主题色 */
:deep(.van-switch--on) {
  background: var(--primary-color);
}

/* 桌面端侧边栏适配 + 居中限宽 */
@media (min-width: 768px) {
  .medical-record-container {
    padding: 0 var(--space-6) var(--space-6);
    max-width: 1000px;
    margin: 0 auto;
  }

}
</style>
