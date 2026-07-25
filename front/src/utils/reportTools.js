/**
 * 报告导出工具函数
 * 支持复制、PDF下载、图片下载
 */

/**
 * 复制文本到剪贴板
 * @param {string} text - 要复制的文本
 * @returns {Promise<boolean>} - 是否成功
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    console.error('复制失败:', error)
    // 降级方案：使用传统方法
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-9999px'
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand('copy')
      document.body.removeChild(textArea)
      return true
    } catch (e) {
      document.body.removeChild(textArea)
      return false
    }
  }
}

/**
 * 将DOM元素导出为PDF
 * @param {HTMLElement} element - DOM元素
 * @param {string} filename - 文件名
 * @returns {Promise<void>}
 */
export async function exportToPDF(element, filename = 'report.pdf') {
  // 动态导入html2pdf.js（如果已安装）
  try {
    const html2pdf = (await import('html2pdf.js')).default

    const opt = {
      margin: 10,
      filename: filename,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: {
        scale: 2,
        useCORS: true,
        backgroundColor: '#ffffff'
      },
      jsPDF: {
        unit: 'mm',
        format: 'a4',
        orientation: 'portrait'
      }
    }

    await html2pdf().set(opt).from(element).save()
  } catch (error) {
    console.error('PDF导出失败:', error)
    throw new Error('PDF导出功能需要安装 html2pdf.js 依赖')
  }
}

/**
 * 将DOM元素导出为图片
 * @param {HTMLElement} element - DOM元素
 * @param {string} filename - 文件名
 * @returns {Promise<void>}
 */
export async function exportToImage(element, filename = 'report.png') {
  // 动态导入html2canvas（如果已安装）
  try {
    const html2canvas = (await import('html2canvas')).default

    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#ffffff'
    })

    // 转换为图片并下载
    canvas.toBlob((blob) => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    }, 'image/png')
  } catch (error) {
    console.error('图片导出失败:', error)
    throw new Error('图片导出功能需要安装 html2canvas 依赖')
  }
}

/**
 * 格式化专家意见为纯文本
 * @param {object} opinion - 专家意见对象
 * @returns {string} - 格式化后的文本
 */
export function formatOpinionText(opinion) {
  let text = `${opinion.expert_name}意见\n`
  text += `${'='.repeat(40)}\n\n`
  text += `摘要：\n${opinion.summary}\n\n`

  if (opinion.detailed_analysis) {
    text += `详细分析：\n`
    if (opinion.detailed_analysis.disease_analysis) {
      text += `  病情分析：${opinion.detailed_analysis.disease_analysis}\n`
    }
    if (opinion.detailed_analysis.treatment_suggestions) {
      text += `  治疗建议：${opinion.detailed_analysis.treatment_suggestions}\n`
    }
    if (opinion.detailed_analysis.risk_alerts) {
      text += `  风险提示：${opinion.detailed_analysis.risk_alerts}\n`
    }
  }

  text += `\n置信度：${(opinion.confidence * 100).toFixed(0)}%\n`

  return text
}

/**
 * 格式化综合报告为纯文本
 * @param {object} report - 报告对象
 * @returns {string} - 格式化后的文本
 */
export function formatReportText(report) {
  let text = `综合会诊结论\n`
  text += `${'='.repeat(40)}\n\n`

  text += `治疗建议：\n${report.treatment_suggestions}\n\n`
  text += `管理建议：\n${report.management_suggestions}\n\n`
  text += `风险提示：\n${report.risk_alerts}\n\n`
  text += `后续计划：\n${report.follow_up_plan}\n\n`

  text += `专家团队：${report.expert_count}位\n`

  return text
}
