/**
 * 报告导出工具
 * 提供PDF和图片导出功能
 */

import html2canvas from 'html2canvas'
import { showToast } from 'vant'
import jsPDF from 'jspdf'

/**
 * 下载 Blob 对象为文件
 * @param {Blob} blob - 要下载的 Blob 数据
 * @param {string} filename - 下载文件名
 * @returns {Promise<boolean>} 是否下载成功
 */
export async function downloadBlob(blob, filename) {
  if (!(blob instanceof Blob)) {
    try {
      blob = new Blob([blob], { type: 'application/pdf' })
    } catch {
      showToast('导出失败，文件格式异常')
      return false
    }
  }

  // 检查是否为错误响应（JSON 错误被包装为 Blob）
  if (blob.type && blob.type.includes('application/json')) {
    try {
      const text = await blob.text()
      const err = JSON.parse(text)
      showToast(err.detail || '导出失败，请重试')
    } catch {
      showToast('导出失败，请重试')
    }
    return false
  }

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  // 延迟释放，移动端浏览器下载启动较慢
  setTimeout(() => URL.revokeObjectURL(url), 5000)
  return true
}

/**
 * 导出DOM元素为图片
 * @param {HTMLElement} element - 要导出的DOM元素
 * @param {string} filename - 文件名（不含扩展名）
 * @returns {Promise<void>}
 */
export async function exportToImage(element, filename = 'report') {
  try {
    const canvas = await html2canvas(element, {
      scale: 2, // 提高分辨率
      useCORS: true, // 允许跨域图片
      logging: false, // 禁用日志
      backgroundColor: '#ffffff', // html2canvas 不解析 CSS 变量，须用字面量
      windowWidth: element.scrollWidth,
      windowHeight: element.scrollHeight
    })

    // 转换为图片并下载
    const imageUrl = canvas.toDataURL('image/png')
    const link = document.createElement('a')
    link.href = imageUrl
    link.download = `${filename}.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    return { success: true }
  } catch (error) {
    console.error('图片导出失败:', error)
    throw new Error(`图片导出失败: ${error.message}`)
  }
}

/**
 * 导出DOM元素为PDF
 * @param {HTMLElement} element - 要导出的DOM元素
 * @param {string} filename - 文件名（不含扩展名）
 * @param {Object} options - PDF选项
 * @returns {Promise<void>}
 */
export async function exportToPDF(element, filename = 'report', options = {}) {
  try {
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff', // html2canvas 不解析 CSS 变量
      windowWidth: element.scrollWidth,
      windowHeight: element.scrollHeight
    })

    const imgWidth = element.scrollWidth
    const imgHeight = element.scrollHeight

    // 计算PDF页面尺寸（A4纸张）
    const pdf = new jsPDF({
      orientation: imgHeight > imgWidth ? 'portrait' : 'landscape',
      unit: 'px',
      format: [imgWidth, imgHeight]
    })

    // 添加图片到PDF
    const imgData = canvas.toDataURL('image/png')
    pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight)

    // 保存PDF
    pdf.save(`${filename}.pdf`)

    return { success: true }
  } catch (error) {
    console.error('PDF导出失败:', error)
    throw new Error(`PDF导出失败: ${error.message}`)
  }
}

/**
 * 导出专家意见
 * @param {Object} opinion - 专家意见对象
 * @param {HTMLElement} element - DOM元素
 */
export async function exportOpinionAsImage(opinion, element) {
  const filename = `expert-opinion-${opinion.expert_name}-${opinion.opinion_id}`
  return await exportToImage(element, filename)
}

export async function exportOpinionAsPDF(opinion, element) {
  const filename = `expert-opinion-${opinion.expert_name}-${opinion.opinion_id}`
  return await exportToPDF(element, filename)
}

/**
 * 导出完整诊断报告
 * @param {Object} report - 综合报告对象
 * @param {HTMLElement} element - DOM元素
 */
export async function exportReportAsImage(report, element) {
  const filename = `diagnosis-report-${report.report_id}`
  return await exportToImage(element, filename)
}

export async function exportReportAsPDF(report, element) {
  const filename = `diagnosis-report-${report.report_id}`
  return await exportToPDF(element, filename)
}