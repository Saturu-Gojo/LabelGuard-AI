const B = '/api'
async function j(r) {
  if (!r.ok) { let m; try { m = (await r.json()).detail } catch { m = r.statusText }; throw new Error(typeof m === 'string' ? m : JSON.stringify(m)) }
  return r.json()
}
const post = (u, body) => fetch(B + u, { method: 'POST', ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) }).then(j)
export const api = {
  jobs: () => fetch(`${B}/validation-jobs`).then(j),
  job: id => fetch(`${B}/validation-jobs/${id}`).then(j),
  create: fd => fetch(`${B}/validation-jobs`, { method: 'POST', body: fd }).then(j),
  contract: id => post(`/validation-jobs/${id}/contract`),
  confirm: (id, c, user) => post(`/validation-jobs/${id}/contract/confirm?user=${encodeURIComponent(user || 'demo.user')}`, c),
  run: id => post(`/validation-jobs/${id}/run`),
  status: id => fetch(`${B}/validation-jobs/${id}/status`).then(j),
  report: id => fetch(`${B}/validation-jobs/${id}/report`).then(j),
  approve: (id, a) => post(`/validation-jobs/${id}/approvals`, a),
  audit: id => fetch(`${B}/validation-jobs/${id}/audit`).then(j),
  file: (id, n) => `${B}/validation-jobs/${id}/files/${n}`,
  reportPdf: id => `${B}/validation-jobs/${id}/report.pdf`,
}
export const FIELDS = {
  sterilization_symbol: 'Sterilization symbol', sterilization_statement: 'Sterilization statement', udi: 'Unique Device Identification',
  product_id: 'Product identifier', product_name: 'Product name', manufacturer_details: 'Manufacturer details', safety_warnings: 'Safety warnings', logo: 'Logo',
}
export const CLS = { UNEXPECTED: 'Unexpected', REQUIRES_REVIEW: 'Needs review', EXPECTED: 'Expected' }
export const sleep = ms => new Promise(r => setTimeout(r, ms))
