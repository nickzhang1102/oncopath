import request from './request'

export const dashboardApi = {
  getDashboard(patientId) {
    return request.get(`/dashboard/${patientId}`)
  },
}