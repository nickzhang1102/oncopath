import request from './request'

export const exportApi = {
  // 导出单次检验报告 PDF
  exportMedicalCheck(checkId) {
    return request.post(`/export/medical-check/${checkId}`, null, {
      responseType: 'blob',
    })
  },

  // 导出单次检查报告 PDF
  exportExamReport(examId) {
    return request.post(`/export/exam-report/${examId}`, null, {
      responseType: 'blob',
    })
  },

  // 导出单次病理报告 PDF
  exportPathologyReport(reportId) {
    return request.post(`/export/pathology-report/${reportId}`, null, {
      responseType: 'blob',
    })
  },

  // 导出时间线 PDF
  exportTimeline(patientId) {
    return request.post(`/export/patient-timeline/${patientId}`, null, {
      responseType: 'blob',
    })
  },

  // 导出完整病历 PDF
  exportSummary(patientId) {
    return request.post(`/export/patient-summary/${patientId}`, null, {
      responseType: 'blob',
    })
  },
}