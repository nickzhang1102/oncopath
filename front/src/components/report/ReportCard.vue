<template>
  <div class="report-card" :class="{ 'has-image': hasImage }">
    <!-- 左侧颜色指示条 -->
    <div class="card-indicator" :style="{ backgroundColor: typeColor }"></div>
    
    <!-- 卡片主体 -->
    <div class="card-body">
      <!-- 头部区域 -->
      <div class="card-header">
        <div class="header-left">
          <span class="type-icon"><van-icon :name="typeIcon" /></span>
          <div class="header-info">
            <div class="report-title">{{ title }}</div>
            <div class="report-meta">
              <span class="meta-item">
                <van-icon name="calendar-o" size="12" />
                {{ formatDate(date) }}
              </span>
              <span v-if="hospital" class="meta-item">
                <van-icon name="location-o" size="12" />
                {{ hospital }}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 内容区域（可展开/收起） -->
      <div v-if="examInfo" class="card-content">
        <div class="content-label">检查所见</div>
        <van-text-ellipsis 
          :content="examInfo" 
          :rows="2" 
          expand-text="展开" 
          collapse-text="收起"
          @click.stop
        />
      </div>
      
      <div v-if="examDiag" class="card-content">
        <div class="content-label">诊断意见</div>
        <van-text-ellipsis 
          :content="examDiag" 
          :rows="2" 
          expand-text="展开" 
          collapse-text="收起"
          @click.stop
        />
      </div>
      
      <!-- 结构化字段标签区域 -->
      <div v-if="structuredTags.length" class="card-structured">
        <span
          v-for="tag in structuredTags"
          :key="tag.label"
          class="structured-tag"
        >
          {{ tag.label }}：{{ tag.value }}
        </span>
      </div>
      
      <div v-if="comment" class="card-content">
        <div class="content-label">备注</div>
        <van-text-ellipsis
          :content="comment"
          :rows="2"
          expand-text="展开"
          collapse-text="收起"
          @click.stop
        />
      </div>

      <!-- AI 解读预览 -->
      <div v-if="interpretation" class="card-ai-interpretation">
        <div class="ai-label">
          <van-icon name="chat-o" style="margin-right: 4px;" />
          AI 解读
        </div>
        <van-text-ellipsis
          :content="interpretation.replace(/^## .+\n\n/, '').replace(/^#+ /gm, '').replace(/\*\*/g, '').substring(0, 80) + '...'"
          :rows="1"
          expand-text=""
          collapse-text=""
          @click.stop="$emit('view-detail')"
        />
      </div>
      
      <!-- 底部操作区域 -->
      <div class="card-footer">
        <div class="footer-view" @click.stop="$emit('view-detail')">
          <van-icon name="eye-o" class="footer-icon" />
          <span class="footer-text">{{ hasImage ? '查看详情' : '查看报告' }}</span>
        </div>
        <div v-if="showActions" class="footer-actions">
          <van-icon name="share-o" class="action-icon" @click.stop="$emit('share')" />
          <van-icon name="edit" class="action-icon" @click.stop="$emit('edit')" />
          <van-icon name="delete-o" class="action-icon action-danger" @click.stop="$emit('delete')" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { EXAM_TYPE_COLORS } from '@/styles/constants'
import { useGeneTesting } from '@/composables/useGeneTesting'

const props = defineProps({
  type: {
    type: String,
    default: ''
  },
  color: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: '检查报告'
  },
  date: {
    type: String,
    default: ''
  },
  hospital: {
    type: String,
    default: ''
  },
  examInfo: {
    type: String,
    default: ''
  },
  examDiag: {
    type: String,
    default: ''
  },
  comment: {
    type: String,
    default: ''
  },
  hasImage: {
    type: Boolean,
    default: false
  },
  showActions: {
    type: Boolean,
    default: true
  },
  diagnosis: {
    type: String,
    default: ''
  },
  cancerType: {
    type: String,
    default: ''
  },
  stage: {
    type: String,
    default: ''
  },
  histologyType: {
    type: String,
    default: ''
  },
  immunohistochemistry: {
    type: String,
    default: ''
  },
  geneTesting: {
    type: String,
    default: ''
  },
  interpretation: {
    type: String,
    default: ''
  }
})

defineEmits(['view-detail', 'share', 'edit', 'delete'])

// 报告类型图标映射
const typeIconMap = {
  'ct': 'search',
  'mri': 'microscope-o',
  'ultrasound': 'wave',
  'xray': 'photo-o',
  'ecg': 'like-o',
  'endoscopy': 'aim',
  'gastroscopy': 'gift-o',
  'colonoscopy': 'scan',
  'pathology': 'fire-o',
  'pathology_report': 'fire-o'
}

// 报告类型颜色映射
const typeColorMap = EXAM_TYPE_COLORS

const typeIcon = computed(() => {
  if (!props.type) return 'description'
  const key = props.type.toLowerCase()
  return typeIconMap[key] || 'description'
})

const typeColor = computed(() => {
  if (props.color) return props.color
  if (!props.type) return 'var(--primary-color)'
  const key = props.type.toLowerCase()
  return typeColorMap[key] || 'var(--primary-color)'
})

function formatDate(date) {
  if (!date) return ''
  return date.split('T')[0]
}

const geneTestingRaw = computed(() => props.geneTesting || null)
const { cardDisplay: geneTestingDisplay } = useGeneTesting(geneTestingRaw)

const structuredTags = computed(() => {
  const tags = [
    { label: '诊断', value: props.diagnosis },
    { label: '癌种', value: props.cancerType },
    { label: '分期', value: props.stage },
    { label: '组织学类型', value: props.histologyType },
    { label: '免疫组化', value: props.immunohistochemistry },
    { label: '基因检测', value: geneTestingDisplay.value },
  ]
  return tags.filter(t => t.value)
})
</script>

<style scoped>
.report-card {
  background: var(--bg-surface);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px var(--primary-alpha-8);
  transition: all 0.3s ease;
  position: relative;
  display: flex;
}

.report-card:hover {
  box-shadow: 0 4px 16px var(--primary-alpha-12);
}

/* 左侧指示条 */
.card-indicator {
  width: 4px;
  flex-shrink: 0;
}

/* 卡片主体 */
.card-body {
  flex: 1;
  padding: 16px;
  min-width: 0;
}

/* 头部区域 */
.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.type-icon {
  font-size: 28px;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-alpha-8);
  border-radius: 12px;
}

.header-info {
  flex: 1;
  min-width: 0;
}

.report-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

/* 内容区域 */
.card-content {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--primary-alpha-10);
}

.content-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--primary-color);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-content :deep(.van-text-ellipsis) {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* AI 解读预览 */
.card-ai-interpretation {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--primary-alpha-10);
  cursor: pointer;
}

.card-ai-interpretation .ai-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--primary-color);
  margin-bottom: 6px;
}

.card-ai-interpretation :deep(.van-text-ellipsis) {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.card-ai-interpretation:hover :deep(.van-text-ellipsis) {
  color: var(--primary-color);
}

/* 结构化字段标签 */
.card-structured {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--primary-alpha-10);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.structured-tag {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 1px 8px;
  border-radius: 4px;
  line-height: 1.6;
}

/* 底部操作区域 */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--primary-alpha-10);
}

.footer-view {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.footer-icon {
  font-size: 14px;
  color: var(--text-tertiary);
}

.footer-text {
  font-size: 13px;
  color: var(--text-tertiary);
}

.footer-view:hover .footer-text,
.footer-view:hover .footer-icon {
  color: var(--text-secondary);
}

.footer-actions {
  display: flex;
  gap: 12px;
}

.action-icon {
  font-size: 16px;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 4px;
}

.action-icon:hover {
  color: var(--primary-color);
}

.action-danger:hover {
  color: var(--van-danger-color);
}

/* 响应式调整 */
@media (max-width: 360px) {
  .card-body {
    padding: 12px;
  }
  
  .type-icon {
    font-size: 24px;
    width: 36px;
    height: 36px;
  }
  
  .report-title {
    font-size: 15px;
  }
}
</style>