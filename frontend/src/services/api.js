import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Analyse 5 modules ────────────────────────────────────────────────────────
export const analyzeDueDiligence   = (data) => api.post('/analyze/due-diligence',   data)
export const analyzeCompliance     = (data) => api.post('/analyze/compliance',       data)
export const analyzeCreditRisk     = (data) => api.post('/analyze/credit-risk',      data)
export const analyzeAudit          = (data) => api.post('/analyze/audit',            data)
export const analyzeBusinessAdvisor= (data) => api.post('/analyze/business-advisor', data)

// ── Comparaison ──────────────────────────────────────────────────────────────
export const compareCompanies = (data) => api.post('/compare', data)

// ── Dashboard ────────────────────────────────────────────────────────────────
export const getStats   = ()       => api.get('/stats')
export const getHistory = (params) => api.get('/history', { params })
export const getReport  = (id)     => api.get(`/report/${id}`)
export const exportCSV  = ()       => api.get('/export')

// ── Benchmarks ───────────────────────────────────────────────────────────────
export const getAllBenchmarks    = ()       => api.get('/benchmarks')
export const getSectorBenchmark = (sector) => api.get(`/benchmarks/${sector}`)

// ── SHAP Explicabilité ────────────────────────────────────────────────────────
export const explainDoc = (id) => api.post(`/explain/${id}`)

// ── PDF ──────────────────────────────────────────────────────────────────────
export const downloadPDF = (id) => {
  window.open(`/report/${id}/pdf`, '_blank')
}

// ── Health ───────────────────────────────────────────────────────────────────
export const healthCheck = () => api.get('/health')

export default api