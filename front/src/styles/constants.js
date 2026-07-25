/**
 * 共享颜色映射常量
 * 供多个组件复用，避免重复定义
 */

// 检查类型颜色映射（供 ReportCard 使用作为回退）
export const EXAM_TYPE_COLORS = {
  'ct': '#3B82F6',
  'mri': '#8B5CF6',
  'ultrasound': '#059669',
  'xray': '#D97706',
  'ecg': '#DC2626',
  'endoscopy': '#EC4899',
  'gastroscopy': '#EC4899',
  'colonoscopy': '#EC4899',
  'pathology': '#F97316',
  'pathology_report': '#F97316'
}

// 检查类型中文标签映射（exam_type -> 中文名）
// 注意: 检验类分类(blood_routine等)已从API动态获取(image_category表)，
// 此处仅映射检查类exam_type，新增检查类型时需同步更新
export const EXAM_TYPE_LABELS = {
  'ct': 'CT',
  'mri': 'MRI',
  'ultrasound': '超声',
  'xray': 'X光',
  'ecg': '心电图',
  'endoscopy': '内镜',
  'gastroscopy': '胃镜',
  'colonoscopy': '肠镜',
  'pathology': '病理',
  'pathology_report': '病理'
}

// 时间线来源类型颜色映射
export const TIMELINE_SOURCE_COLORS = {
  timeline_event: '#0891B2',
  medical_check: '#DC2626',
  medical_exam: '#3B82F6',
  pathology_report: '#F97316',
  medication: '#10B981'
}

// 时间线来源类型图标（Vant icon 名称）
export const TIMELINE_SOURCE_ICONS = {
  timeline_event: 'clock-o',
  medical_check: 'chart-trending-o',
  medical_exam: 'scan',
  pathology_report: 'certificate',
  medication: 'gem-o'
}

// 时间线来源类型标签
export const TIMELINE_SOURCE_LABELS = {
  timeline_event: '时间线',
  medical_check: '检验报告',
  medical_exam: '检查报告',
  pathology_report: '病理报告',
  medication: '用药记录'
}

// 时间线事件 category 配置
export const TIMELINE_CATEGORY_CONFIG = {
  chemotherapy: { icon: 'gem-o', label: '化疗', color: '#8B5CF6' },
  radiation: { icon: 'fire-o', label: '放疗', color: '#D97706' },
  surgery: { icon: 'certificate', label: '手术', color: '#DC2626' },
  targeted: { icon: 'aim', label: '靶向治疗', color: '#059669' },
  immunotherapy: { icon: 'shield-o', label: '免疫治疗', color: '#7C3AED' },
  adc: { icon: 'aim', label: 'ADC治疗', color: '#EC4899' },
  car_t: { icon: 'shield-o', label: 'CAR-T', color: '#F59E0B' },
  diagnosis: { icon: 'hospital', label: '诊断', color: '#0891B2' },
  daily_status: { icon: 'todo-list-o', label: '每日状态', color: '#0891B2' },
  mood: { icon: 'smile-o', label: '心情', color: '#059669' },
  pain: { icon: 'warning-o', label: '疼痛', color: '#DC2626' },
  diet: { icon: 'gift-o', label: '饮食', color: '#D97706' },
  sleep: { icon: 'closed-eye', label: '睡眠', color: '#6366F1' },
  stool: { icon: 'records', label: '排便', color: '#6B7280' },
  life: { icon: 'flower-o', label: '生活', color: '#059669' },
}

// OCR 状态标签类型映射（供 useOCRReview / OCRReviewLayout / ImageTimeline 使用）
export const OCR_STATUS_TAG_TYPE = {
  pending: 'default', processing: 'primary', pending_review: 'warning',
  completed: 'success', failed: 'danger', reviewed: 'success'
}

// OCR 状态中文文字映射
export const OCR_STATUS_TEXT = {
  pending: '待处理', processing: '处理中', pending_review: '待确认',
  completed: '已完成', failed: '处理失败', reviewed: '已审查'
}