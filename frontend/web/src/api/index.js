import client from './client'

export const authApi = {
  register: (data) => client.post('/api/v1/auth/register', data),
  // 后端 login 用 OAuth2 表单（x-www-form-urlencoded）
  login: (username, password) => {
    const body = new URLSearchParams({ username, password })
    return client.post('/api/v1/auth/login', body, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  me: () => client.get('/api/v1/auth/me')
}

export const deviceApi = {
  list: () => client.get('/api/v1/devices'),
  create: (data) => client.post('/api/v1/devices', data),
  deactivate: (id, purge = false) => client.delete(`/api/v1/devices/${id}`, { params: { purge } })
}

export const dataApi = {
  // 设备上报：需设备头（演示用，正常由硬件/网关上报）
  ingest: (deviceId, deviceToken, points) =>
    client.post('/api/v1/data', points, {
      headers: { 'X-Device-Id': deviceId, 'X-Device-Token': deviceToken }
    }),
  query: (params) => client.get('/api/v1/data', { params }),
  heatmap: (metric) => client.get('/api/v1/data/heatmap', { params: { metric } })
}

export const datasetApi = {
  list: (params) => client.get('/api/v1/datasets', { params }),
  pending: () => client.get('/api/v1/datasets/pending'),
  create: (data) => client.post('/api/v1/datasets', data),
  submit: (id) => client.post(`/api/v1/datasets/${id}/submit`),
  review: (id, data) => client.post(`/api/v1/datasets/${id}/review`, data),
  download: (id, format = 'csv') =>
    client.get(`/api/v1/datasets/${id}/download`, { params: { format }, responseType: 'blob' })
}

export const notificationApi = {
  list: () => client.get('/api/v1/notifications'),
  read: (id) => client.post(`/api/v1/notifications/${id}/read`),
  readAll: () => client.post('/api/v1/notifications/read-all')
}

export const statsApi = {
  overview: () => client.get('/api/v1/stats/overview')
}
