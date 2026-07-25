import request from './request'

// 获取知识库分类树
export function getKnowledgeCategories() {
  return request.get('/knowledge/categories')
}

// 创建知识库分类
export function createKnowledgeCategory(data) {
  return request.post('/knowledge/categories', data)
}

// 更新知识库分类
export function updateKnowledgeCategory(categoryId, data) {
  return request.put(`/knowledge/categories/${categoryId}`, data)
}

// 删除知识库分类
export function deleteKnowledgeCategory(categoryId) {
  return request.delete(`/knowledge/categories/${categoryId}`)
}

// 获取文档列表
export function getDocumentList(params) {
  return request.get('/knowledge/documents', { params })
}

// 获取文档详情
export function getDocumentDetail(docId) {
  return request.get(`/knowledge/documents/${docId}`)
}

// 上传文档
export function uploadDocument(formData, onProgress) {
  return request.post('/knowledge/documents', formData, {
    onUploadProgress: onProgress
  })
}

// 更新文档信息
export function updateDocument(docId, data) {
  return request.put(`/knowledge/documents/${docId}`, data)
}

// 删除文档
export function deleteDocument(docId) {
  return request.delete(`/knowledge/documents/${docId}`)
}

// 手动生成AI摘要
export function generateSummary(docId) {
  return request.post(`/knowledge/documents/${docId}/generate-summary`)
}

// 搜索文档
export function searchDocuments(query, params) {
  return request.get('/knowledge/search', { params: { q: query, ...params } })
}

// 获取文档预览URL（后端暂无预览端点，实际指向下载链接）
export function getDocumentPreviewUrl(docId) {
  return `/api/v1/knowledge/documents/${docId}/download`
}

// 获取文档下载URL
export function getDocumentDownloadUrl(docId) {
  return `/api/v1/knowledge/documents/${docId}/download`
}

// 获取直接访问URL
export function getDirectAccessURL(path) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl}${path}`
}