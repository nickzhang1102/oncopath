<template>
  <div class="markdown-renderer" v-html="renderedContent"></div>
</template>

<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import plaintext from 'highlight.js/lib/languages/plaintext'
import python from 'highlight.js/lib/languages/python'
import shell from 'highlight.js/lib/languages/shell'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import { sanitizeHtml } from '@/utils/sanitize'
import 'highlight.js/styles/github.css'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  streaming: {
    type: Boolean,
    default: false
  }
})

// 流式模式下的光标闪烁效果
const showCursor = ref(true)
let cursorTimer = null

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('css', css)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('plaintext', plaintext)
hljs.registerLanguage('python', python)
hljs.registerLanguage('shell', shell)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('vue', xml)
hljs.registerLanguage('xml', xml)

watch(() => props.streaming, (val) => {
  if (val) {
    cursorTimer = setInterval(() => { showCursor.value = !showCursor.value }, 530)
  } else {
    clearInterval(cursorTimer)
    cursorTimer = null
    showCursor.value = true
  }
}, { immediate: true })

// 组件卸载时清理定时器
onUnmounted(() => {
  if (cursorTimer) {
    clearInterval(cursorTimer)
    cursorTimer = null
  }
})

// 配置 marked — 使用 renderer 扩展实现代码高亮（marked v18+ 不再支持 highlight 选项）
const renderer = new marked.Renderer()
renderer.code = function({ text, lang }) {
  let highlighted
  if (lang && hljs.getLanguage(lang)) {
    try {
      highlighted = hljs.highlight(text, { language: lang }).value
    } catch (err) {
      highlighted = hljs.highlightAuto(text).value
    }
  } else {
    highlighted = hljs.highlightAuto(text).value
  }
  return `<pre><code class="hljs language-${lang || 'auto'}">${highlighted}</code></pre>`
}

marked.setOptions({
  breaks: true,
  gfm: true,
  renderer
})

const renderedContent = computed(() => {
  if (!props.content) return props.streaming ? '<span class="streaming-cursor">▊</span>' : ''
  const rawHtml = marked(props.content)
  let html = sanitizeHtml(rawHtml)
  // 流式模式下追加光标
  if (props.streaming && showCursor.value) {
    html += '<span class="streaming-cursor">▊</span>'
  }
  return html
})
</script>

<style scoped>
.markdown-renderer {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
}

.markdown-renderer :deep(h1),
.markdown-renderer :deep(h2),
.markdown-renderer :deep(h3),
.markdown-renderer :deep(h4),
.markdown-renderer :deep(h5),
.markdown-renderer :deep(h6) {
  margin-top: 12px;
  margin-bottom: 6px;
  font-weight: 600;
  line-height: 1.4;
}

.markdown-renderer :deep(h1) {
  font-size: 1.15em;
  border-bottom: 1px solid var(--border-light);
  padding-bottom: 0.3em;
}

.markdown-renderer :deep(h2) {
  font-size: 1.05em;
  border-bottom: 1px solid var(--border-light);
  padding-bottom: 0.3em;
}

.markdown-renderer :deep(h3) {
  font-size: 1em;
}

.markdown-renderer :deep(p) {
  margin-bottom: 8px;
}

.markdown-renderer :deep(code) {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: var(--markdown-code-bg);
  border-radius: 3px;
}

.markdown-renderer :deep(pre) {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: var(--markdown-pre-bg);
  border-radius: 6px;
  margin-bottom: 16px;
}

.markdown-renderer :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.markdown-renderer :deep(ul),
.markdown-renderer :deep(ol) {
  padding-left: 2em;
  margin-bottom: 16px;
}

.markdown-renderer :deep(li) {
  margin-bottom: 0.25em;
}

.markdown-renderer :deep(blockquote) {
  padding: 0 1em;
  color: var(--markdown-blockquote-color);
  border-left: 0.25em solid var(--markdown-border-color);
  margin-bottom: 16px;
}

.markdown-renderer :deep(a) {
  color: var(--markdown-link-color);
  text-decoration: none;
}

.markdown-renderer :deep(a:hover) {
  text-decoration: underline;
}

.markdown-renderer :deep(table) {
  display: block;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border-spacing: 0;
  border-collapse: collapse;
  margin-bottom: 16px;
}

.markdown-renderer :deep(table th),
.markdown-renderer :deep(table td) {
  padding: 6px 13px;
  border: 1px solid var(--markdown-border-color);
}

.markdown-renderer :deep(table th) {
  font-weight: 600;
  background-color: var(--markdown-pre-bg);
}

.markdown-renderer :deep(table tr:nth-child(2n)) {
  background-color: var(--markdown-pre-bg);
}

.markdown-renderer :deep(img) {
  max-width: 100%;
  box-sizing: content-box;
  background-color: var(--markdown-img-bg);
}

.markdown-renderer :deep(hr) {
  height: 0.25em;
  padding: 0;
  margin: 24px 0;
  background-color: var(--markdown-hr-bg);
  border: 0;
}

.markdown-renderer :deep(.streaming-cursor) {
  color: var(--primary-color);
  animation: blink 1s step-end infinite;
  font-weight: bold;
}

@keyframes blink {
  50% { opacity: 0; }
}
</style>
