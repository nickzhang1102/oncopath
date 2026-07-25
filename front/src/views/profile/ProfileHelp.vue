<template>
  <div class="profile-help">
    <BackButton title="帮助中心" />

    <!-- 常见问题 -->
    <div class="help-section">
      <div class="section-title">常见问题</div>
      <van-collapse v-model="activeNames">
        <van-collapse-item title="如何上传医疗报告？" name="1">
          <p>1. 点击首页底部的"上传"按钮</p>
          <p>2. 选择要上传的报告图片（支持多张）</p>
          <p>3. 系统会自动识别报告内容并提取关键信息</p>
          <p>4. 确认信息无误后点击保存即可</p>
        </van-collapse-item>
        <van-collapse-item title="如何查看历史报告？" name="2">
          <p>1. 点击首页的"报告列表"或底部导航的"报告"</p>
          <p>2. 可以按类型筛选：检查报告、病理报告等</p>
          <p>3. 点击报告卡片可查看详细信息</p>
          <p>4. 支持按日期、关键词搜索报告</p>
        </van-collapse-item>
        <van-collapse-item title="如何进行虚拟会诊？" name="3">
          <p>1. 进入"虚拟会诊"页面</p>
          <p>2. 选择要咨询的报告或病情资料</p>
          <p>3. 输入您的疑问</p>
          <p>4. 系统会调用AI专家团队进行会诊分析</p>
          <p>5. 会诊完成后可查看详细报告</p>
        </van-collapse-item>
        <van-collapse-item title="指标异常提醒是什么？" name="4">
          <p>系统会自动分析您的检查报告，识别异常指标并生成提醒。您可以在"异常指标"页面查看所有异常项目及其历史趋势。</p>
        </van-collapse-item>
        <van-collapse-item title="如何修改个人信息？" name="5">
          <p>1. 点击"个人中心"进入个人页面</p>
          <p>2. 点击"个人信息"</p>
          <p>3. 修改昵称、手机号等信息</p>
          <p>4. 点击保存即可</p>
        </van-collapse-item>
        <van-collapse-item title="数据安全如何保障？" name="6">
          <p>我们采用多重安全措施保护您的数据：</p>
          <p>• 所有数据传输采用HTTPS加密</p>
          <p>• 敏感数据脱敏存储</p>
          <p>• 严格的数据访问权限控制</p>
          <p>• 定期数据备份</p>
        </van-collapse-item>
      </van-collapse>
    </div>

    <!-- 联系客服 -->
    <div class="help-section">
      <div class="section-title">联系客服</div>
      <van-cell-group inset>
        <van-cell title="客服电话" value="400-000-0000" icon="phone-o" />
        <van-cell title="工作时间" value="周一至周五 9:00-18:00" icon="clock-o" />
        <van-cell title="在线客服" is-link icon="service-o" @click="handleOnlineService" />
      </van-cell-group>
    </div>

    <!-- 意见反馈 -->
    <div class="help-section">
      <div class="section-title">意见反馈</div>
      <van-cell-group inset>
        <van-cell title="提交反馈" is-link icon="edit" to="/home/profile" @click="handleFeedback" />
      </van-cell-group>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { showToast } from 'vant'
import BackButton from '@/components/index-detail/BackButton.vue'

const activeNames = ref(['1'])

function handleOnlineService() {
  showToast('在线客服功能开发中')
}

function handleFeedback() {
  showToast('反馈功能开发中')
}
</script>

<style scoped>
.profile-help {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--space-6);
}

.help-section {
  margin-bottom: var(--space-4);
}

.section-title {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

:deep(.van-collapse-item__content) {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.8;
}

:deep(.van-collapse-item__content p) {
  margin: 0 0 var(--space-1) 0;
}
</style>