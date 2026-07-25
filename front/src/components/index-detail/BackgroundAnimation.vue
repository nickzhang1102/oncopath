<template>
  <div class="bg-animation">
    <div
      v-for="i in 8"
      :key="`cross-${i}`"
      class="floating-cross"
      :style="{
        left: crossPositions[i-1]?.left || '10%',
        top: crossPositions[i-1]?.top || '10%',
        animationDelay: (i * 0.8) + 's'
      }"
    >
      ✚
    </div>
    <div
      v-for="i in 6"
      :key="`circle-${i}`"
      class="floating-circle"
      :style="{
        left: circlePositions[i-1]?.left || '20%',
        top: circlePositions[i-1]?.top || '20%',
        animationDelay: (i * 1.2) + 's'
      }"
    ></div>
    <div
      v-for="i in 4"
      :key="`heart-${i}`"
      class="floating-heart"
      :style="{
        left: heartPositions[i-1]?.left || '30%',
        top: heartPositions[i-1]?.top || '30%',
        animationDelay: (i * 1.5) + 's'
      }"
    >
      ♥
    </div>
  </div>
</template>

<script setup>
// 预定义位置，避免每次渲染时重新计算
const crossPositions = [
  { left: '8%', top: '15%' },
  { left: '85%', top: '25%' },
  { left: '15%', top: '45%' },
  { left: '75%', top: '65%' },
  { left: '25%', top: '75%' },
  { left: '90%', top: '85%' },
  { left: '5%', top: '35%' },
  { left: '60%', top: '10%' }
];

const circlePositions = [
  { left: '20%', top: '20%' },
  { left: '70%', top: '30%' },
  { left: '40%', top: '60%' },
  { left: '80%', top: '50%' },
  { left: '10%', top: '80%' },
  { left: '50%', top: '90%' }
];

const heartPositions = [
  { left: '30%', top: '40%' },
  { left: '65%', top: '20%' },
  { left: '15%', top: '70%' },
  { left: '85%', top: '60%' }
];
</script>

<style scoped>
.bg-animation {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.floating-cross, .floating-circle, .floating-heart {
  position: absolute;
  opacity: 0.1;
  color: white;
  font-size: 24px;
  animation: float 15s infinite linear;
}

.floating-circle {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: white;
  animation: float 20s infinite linear;
}

.floating-heart {
  font-size: 18px;
  animation: float 18s infinite linear;
}

@keyframes float {
  0% {
    transform: translateY(0) rotate(0deg);
    opacity: 0.1;
  }
  25% {
    opacity: 0.3;
  }
  50% {
    transform: translateY(-100px) rotate(180deg);
    opacity: 0.1;
  }
  75% {
    opacity: 0.3;
  }
  100% {
    transform: translateY(0) rotate(360deg);
    opacity: 0.1;
  }
}
</style>
