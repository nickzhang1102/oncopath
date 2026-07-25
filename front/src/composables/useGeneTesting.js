import { computed } from 'vue'

/**
 * 解析基因检测字段（兼容纯文本和 JSON 结构两种格式）
 * @param {import('vue').Ref<string|null|undefined>} rawValue - gene_testing 原始值
 * @returns {{ display: import('vue').ComputedRef<string>, items: import('vue').ComputedRef<Array>, method: import('vue').ComputedRef<string>, interpretation: import('vue').ComputedRef<string>, isStructured: import('vue').ComputedRef<boolean> }}
 */
export function useGeneTesting(rawValue) {
  const parsed = computed(() => {
    const raw = rawValue.value
    if (!raw) return { items: [], method: '', interpretation: '', text: '', structured: false }

    try {
      const data = JSON.parse(raw)
      if (data && typeof data === 'object' && data.test_items) {
        return {
          items: data.test_items.map(i => ({
            gene: i.gene || '',
            result: i.result || '',
            mutation_type: i.mutation_type || '',
            frequency: i.frequency || '',
          })),
          method: data.test_method || '',
          interpretation: data.interpretation || '',
          text: '',
          structured: true,
        }
      }
      return { items: [], method: '', interpretation: '', text: String(data), structured: false }
    } catch {
      return { items: [], method: '', interpretation: '', text: raw, structured: false }
    }
  })

  const display = computed(() => {
    const p = parsed.value
    if (p.structured) {
      const parts = p.items.map(i => {
        let s = i.gene || ''
        if (i.result) s += `: ${i.result}`
        return s
      })
      let text = parts.join('; ')
      if (p.method) text += ` (${p.method})`
      if (p.interpretation) text += `\n${p.interpretation}`
      return text || ''
    }
    return p.text
  })

  // 列表卡片展示用（简洁摘要）
  const cardDisplay = computed(() => {
    const p = parsed.value
    if (!p.structured) return p.text
    if (p.items.length === 0) return ''
    let text = `${p.items.length}项检测`
    const firstResult = p.items.find(i => i.result)
    if (firstResult) text += ` · ${firstResult.gene}: ${firstResult.result}`
    return text
  })

  const items = computed(() => parsed.value.items)
  const method = computed(() => parsed.value.method)
  const interpretation = computed(() => parsed.value.interpretation)
  const isStructured = computed(() => parsed.value.structured)

  return { display, cardDisplay, items, method, interpretation, isStructured }
}
