<template>
  <FeatureGridPage
    title="智能中心"
    subtitle="AI工具与智能诊断"
    :items="newsItems"
  />
</template>

<script setup>
import FeatureGridPage from '@/components/common/FeatureGridPage.vue'

const newsItems = [
  { path: '/home/consultation', icon: 'friends-o', label: '虚拟会诊', description: '智能专家会诊助手' },
  { path: '/home/knowledge', icon: 'bookmark-o', label: '知识库', description: '护理指南与健康知识' },
  { icon: 'microscope-o', label: '临床试验', description: '查看最新临床试验信息', path: 'https://www.chictr.org.cn/searchproj.html', external: true },
]
</script>
