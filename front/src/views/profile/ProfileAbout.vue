<template>
  <div class="profile-about">
    <BackButton title="关于我们" />

    <!-- Logo和版本信息 -->
    <div class="about-header">
      <div class="logo-wrapper">
        <van-icon name="medical" size="60" color="var(--primary-color)" />
      </div>
      <h1 class="app-name">OncoPath</h1>
      <p class="version">{{ version ? `版本 ${version}` : '' }}</p>
    </div>

    <!-- 产品介绍 -->
    <div class="about-section">
      <van-cell-group inset>
        <van-cell title="产品介绍" />
        <div class="section-content">
          <p>OncoPath 是一款专业的医疗报告管理工具，致力于帮助用户轻松管理各类医疗报告，提供智能化的报告分析和 AI 辅助理解服务。</p>
        </div>
      </van-cell-group>
    </div>

    <!-- 功能特点 -->
    <div class="about-section">
      <van-cell-group inset>
        <van-cell title="主要功能" />
        <div class="feature-list">
          <div class="feature-item">
            <van-icon name="photograph" class="feature-icon" />
            <span>智能OCR识别报告</span>
          </div>
          <div class="feature-item">
            <van-icon name="chart-trending-o" class="feature-icon" />
            <span>指标异常追踪提醒</span>
          </div>
          <div class="feature-item">
            <van-icon name="friends-o" class="feature-icon" />
            <span>AI专家团队会诊</span>
          </div>
          <div class="feature-item">
            <van-icon name="calendar-o" class="feature-icon" />
            <span>时间线病情记录</span>
          </div>
        </div>
      </van-cell-group>
    </div>

    <!-- 链接 -->
    <div class="about-section">
      <van-cell-group inset>
        <van-cell title="用户协议" is-link @click="handleAgreement" />
        <van-cell title="隐私政策" is-link @click="handlePrivacy" />
      </van-cell-group>
    </div>

    <!-- 版权信息 -->
    <div class="copyright">
      <p>Copyright © 2026 OncoPath</p>
      <p>All Rights Reserved</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { showToast } from 'vant'
import BackButton from '@/components/index-detail/BackButton.vue'
import { useAppVersion } from '@/composables/useAppVersion'

const { version, fetchVersion } = useAppVersion()

onMounted(() => {
  fetchVersion()
})

function handleAgreement() {
  showToast('用户协议页面开发中')
}

function handlePrivacy() {
  showToast('隐私政策页面开发中')
}
</script>

<style scoped>
.profile-about {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--space-8);
}

.about-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-8) 0;
  background: var(--bg-surface);
}

.logo-wrapper {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-4);
}

.app-name {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--space-2) 0;
}

.version {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin: 0;
}

.about-section {
  margin-top: var(--space-4);
}

.section-content {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.8;
}

.feature-list {
  padding: var(--space-3) var(--space-4);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.feature-item {
  display: flex;
  align-items: center;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.feature-icon {
  margin-right: var(--space-2);
  color: var(--primary-color);
  font-size: 18px;
}

.copyright {
  text-align: center;
  padding: var(--space-6) 0;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.copyright p {
  margin: var(--space-1) 0;
}

@media (max-width: 480px) {
  .about-header {
    padding: var(--space-6) 0;
  }

  .logo-wrapper {
    width: 80px;
    height: 80px;
  }

  .feature-list {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 768px) {
  .profile-about {
    max-width: 600px;
    margin: 0 auto;
    padding: var(--space-6);
  }
}
</style>
