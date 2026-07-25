<template>
  <FeatureGridPage
    title="病情管理"
    subtitle="查看最新病情"
    :items="medicalItems"
  />
</template>

<script setup>
import FeatureGridPage from '@/components/common/FeatureGridPage.vue'

const medicalItems = [
  { path: '/home/reports', icon: 'records', label: '检验报告', description: '查看历史检验报告' },
  { path: '/home/exam-reports', icon: 'scan', label: '检查报告', description: '查看检查报告详情' },
  { path: '/home/index', icon: 'chart-trending-o', label: '查询指标', description: '查看指标数据' },
  { path: '/home/abnormal-indicators', icon: 'warning-o', label: '异常指标', description: '查看异常指标追踪' },
  { path: '/home/pathology-reports', icon: 'certificate', label: '病理报告', description: '查看病理检查报告' },
  { path: '/home/image-report', icon: 'photo-o', label: '上传报告', description: '上传医疗检查报告' },
  { path: '/home/treatment', icon: 'comment-o', label: '治疗记录', description: '添加和管理治疗记录' },
  { path: '/home/medication', icon: 'gem-o', label: '用药记录', description: '管理当前用药和历史' },
  { path: '/home/status', icon: 'smile-o', label: '状态记录', description: '记录身体状态和心情' },
]
</script>
