<template>
  <van-popup
    :show="show"
    @update:show="$emit('update:show', $event)"
    :position="isDesktop ? 'center' : 'bottom'"
    :round="!isDesktop"
    :style="isDesktop ? 'width: 420px; border-radius: var(--radius-lg);' : ''"
  >
    <div class="sponsor-panel">
      <span class="sponsor-close" @click="$emit('update:show', false)">✕</span>

      <!-- 档位选择视图 -->
      <template v-if="!selectedTier">
        <p class="sponsor-title">如果 OncoPath 对你有帮助，欢迎<em>请作者喝一杯咖啡</em></p>
        <p class="sponsor-subtitle">选择一份能量补给，助力持续更新：</p>
        <div class="tier-grid">
          <div
            v-for="tier in TIERS"
            :key="tier.amount"
            class="tier-card"
            @click="selectedTier = tier"
          >
            <span class="tier-amount">¥{{ tier.amount }}</span>
            <span class="tier-label">{{ tier.emoji }} {{ tier.label }}</span>
          </div>
        </div>
        <p class="sponsor-star-tip">
          ⭐ 去 GitHub 点个 <a :href="REPO_URL" target="_blank" rel="noopener">Star</a>，同样是对作者的支持
        </p>
      </template>

      <!-- 收款码视图（每档专属金额码） -->
      <template v-else>
        <p class="sponsor-title">感谢支持 💚</p>
        <p class="sponsor-subtitle">请使用微信扫码，即按 <strong>¥{{ selectedTier.amount }}</strong> 完成支付</p>
        <div class="qr-wrap">
          <img :src="selectedTier.qr" :alt="`微信收款码 ¥${selectedTier.amount}`">
          <span class="qr-tier-tag">{{ selectedTier.emoji }} {{ selectedTier.label }}</span>
        </div>
        <p class="qr-hint">如想支持其他金额，可返回选择后备注修改</p>
        <van-button size="small" plain type="primary" icon="arrow-left" @click="selectedTier = null">
          返回选择档位
        </van-button>
      </template>
    </div>
  </van-popup>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useResponsive } from '@/composables/useResponsive'
import wechatQr5 from '@/assets/sponsor/wechat5.png'
import wechatQr10 from '@/assets/sponsor/wechat10.png'
import wechatQr20 from '@/assets/sponsor/wechat20.png'
import wechatQr50 from '@/assets/sponsor/wechat50.png'
import wechatQr99 from '@/assets/sponsor/wechat99.png'

const REPO_URL = 'https://github.com/nickzhang1102/oncopath'

// 赞助档位（能量补给风格，每档绑定专属金额收款码）
const TIERS = [
  { amount: 5, emoji: '🌶️', label: '一包辣条', qr: wechatQr5 },
  { amount: 10, emoji: '🍱', label: '一顿拼好饭', qr: wechatQr10 },
  { amount: 20, emoji: '☕', label: '一杯咖啡', qr: wechatQr20 },
  { amount: 50, emoji: '🍢', label: '一次烧烤', qr: wechatQr50 },
  { amount: 99, emoji: '🍲', label: '一顿海底捞', qr: wechatQr99 },
]

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:show'])

const { isDesktop } = useResponsive()

// 当前选中的档位（null = 档位选择视图）
const selectedTier = ref(null)

// 弹窗关闭时重置回档位选择视图
watch(() => props.show, (val) => {
  if (!val) selectedTier.value = null
})
</script>

<style scoped>
.sponsor-panel {
  position: relative;
  padding: 24px 20px calc(20px + env(safe-area-inset-bottom, 0px));
  text-align: center;
}

.sponsor-close {
  position: absolute;
  top: 12px;
  right: 16px;
  font-size: 15px;
  color: var(--text-tertiary);
  cursor: pointer;
}

.sponsor-title {
  margin: 0 12px;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.6;
}

.sponsor-title em {
  font-style: normal;
  color: var(--primary-color);
}

.sponsor-subtitle {
  margin: 6px 0 16px;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* 档位网格（能量补给风格） */
.tier-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.tier-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: transform 0.15s, border-color 0.15s, background 0.15s;
}

.tier-card:active {
  transform: scale(0.96);
  border-color: var(--primary-color);
  background: var(--primary-alpha-5);
}

.tier-amount {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.tier-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.sponsor-star-tip {
  margin: 4px 0 0;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.sponsor-star-tip a {
  color: var(--primary-color);
  font-weight: 600;
  text-decoration: none;
}

/* 收款码视图 */
.qr-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.qr-wrap img {
  display: block;
  width: 200px;
  height: auto;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.qr-tier-tag {
  padding: 4px 12px;
  background: var(--primary-alpha-8);
  border-radius: 999px;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--primary-color);
}

.qr-hint {
  margin: 0 0 14px;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

@media (min-width: 768px) {
  .sponsor-panel {
    padding-bottom: 24px;
  }
}
</style>
