import DOMPurify from 'dompurify'

// 配置 DOMPurify：移除所有 on* 事件属性
DOMPurify.addHook('uponSanitizeElement', (node, data) => {
  if (node.nodeType === 1) {
    const attrs = node.attributes
    for (let i = attrs.length - 1; i >= 0; i--) {
      if (attrs[i].name.startsWith('on')) {
        node.removeAttribute(attrs[i].name)
      }
    }
  }
})

/**
 * 清理 HTML 内容，防止 XSS 攻击
 * @param {string} html - 待清理的 HTML 字符串
 * @returns {string} 清理后的安全 HTML
 */
export function sanitizeHtml(html) {
  if (!html) return ''
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'ul', 'ol', 'li',
      'blockquote', 'pre', 'code',
      'strong', 'em', 'del', 'a',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'img', 'span', 'div'
    ],
    ALLOWED_ATTR: [
      'href', 'src', 'alt', 'title', 'class',
      'id', 'target', 'rel',
      'colspan', 'rowspan', 'align', 'valign'
    ],
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ['style', 'script', 'iframe', 'form', 'input', 'textarea', 'button'],
    FORBID_ATTR: ['style', 'onerror', 'onload', 'onclick', 'onmouseover']
  })
}
