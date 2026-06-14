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
  list: (params) => client.get('/api/v1/devices', { params }),
  create: (data) => client.post('/api/v1/devices', data),
  rotateToken: (id) => client.post(`/api/v1/devices/${id}/token/rotate`),
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
  detail: (id) => client.get(`/api/v1/datasets/${id}`),
  pending: () => client.get('/api/v1/datasets/pending'),
  create: (data) => client.post('/api/v1/datasets', data),
  update: (id, data) => client.patch(`/api/v1/datasets/${id}`, data),
  versions: (id) => client.get(`/api/v1/datasets/${id}/versions`),
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

// API Key 管理（注意：后端 create 的 name 是 query 参数，非 body）
export const keyApi = {
  list: () => client.get('/api/v1/keys'),
  create: (name) => client.post('/api/v1/keys', null, { params: { name } }),
  revoke: (id) => client.delete(`/api/v1/keys/${id}`)
}

// 元数据辅助：传感器型号词典（供下拉与自动填精度）
export const metaApi = {
  sensorTypes: () => client.get('/api/v1/meta/sensor-types')
}

// 教学中心：知识点树 / 思考题 / 学生记录 / AI 助教
export const teachingApi = {
  nodes: (course_code) => client.get('/api/v1/teaching/nodes', { params: { course_code } }),
  node: (id) => client.get(`/api/v1/teaching/nodes/${id}`),
  createNode: (data) => client.post('/api/v1/teaching/nodes', data),
  updateNode: (id, data) => client.patch(`/api/v1/teaching/nodes/${id}`, data),
  deleteNode: (id) => client.delete(`/api/v1/teaching/nodes/${id}`),
  addQuiz: (nodeId, data) => client.post(`/api/v1/teaching/nodes/${nodeId}/quizzes`, data),
  deleteQuiz: (id) => client.delete(`/api/v1/teaching/quizzes/${id}`),
  answer: (quizId, answer) => client.post(`/api/v1/teaching/quizzes/${quizId}/answer`, { answer }),
  reflection: (nodeId, content) => client.post(`/api/v1/teaching/nodes/${nodeId}/reflection`, { content }),
  logs: (params) => client.get('/api/v1/teaching/logs', { params }),
  aiAsk: (node_id, question) => client.post('/api/v1/teaching/ai/ask', { node_id, question }),
  aiFeedback: (nodeId) => client.post(`/api/v1/teaching/nodes/${nodeId}/ai-feedback`)
}
