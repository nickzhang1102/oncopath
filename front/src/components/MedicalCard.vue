<template>
  <div
    class="medical-card"
    :class="{
      'medical-card--elevated': elevated,
      [`medical-card--${variant}`]: variant
    }"
    @click="$emit('click')"
  >
    <div v-if="icon || $slots.icon" class="medical-card__icon">
      <slot name="icon">
        <van-icon :name="icon" :size="iconSize" :color="iconColor" />
      </slot>
    </div>

    <div class="medical-card__content">
      <div v-if="title" class="medical-card__title">{{ title }}</div>
      <div v-if="subtitle" class="medical-card__subtitle">{{ subtitle }}</div>
      <slot />
    </div>

    <div v-if="$slots.action" class="medical-card__action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: String,
  subtitle: String,
  icon: String,
  iconSize: { type: [String, Number], default: 24 },
  iconColor: { type: String, default: 'var(--primary-color)' },
  elevated: Boolean,
  variant: {
    type: String,
    validator: (v) => ['default', 'success', 'warning', 'danger'].includes(v)
  }
})

defineEmits(['click'])
</script>

<style scoped>
.medical-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  cursor: pointer;
}

.medical-card__icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-alpha-10);
  border-radius: var(--radius-md);
}

.medical-card__content {
  flex: 1;
  min-width: 0;
}

.medical-card__title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.medical-card__subtitle {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.medical-card__action {
  flex-shrink: 0;
}

/* 变体 */
.medical-card--success .medical-card__icon {
  background: var(--status-normal-bg);
}

.medical-card--warning .medical-card__icon {
  background: var(--status-warning-bg);
}

.medical-card--danger .medical-card__icon {
  background: var(--status-danger-bg);
}
</style>
