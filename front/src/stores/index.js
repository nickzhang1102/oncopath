import { createPinia } from 'pinia'

export default createPinia()

// 导出所有 store
export { useUserStore } from './user'
export { usePatientStore } from './patient'
export { useMedicalStore } from './medical'
export { useTimelineStore } from './timeline'
export { useConversationsStore } from './conversations'
