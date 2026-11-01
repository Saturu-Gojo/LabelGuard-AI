import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
const BADGE = { APPROVED: 'ok', REJECTED: 'bad', REVIEW_REQUIRED: 'warn', FAILED: 'bad' }
export default function Dashboard({ open, onNew }) {
  const [jobs, setJobs] = useState(null), [err, setErr] = useState('')
  useEffect(() => { api.jobs().then(setJobs).catch(e => setErr(e.message)) }, [])
  if (err) return <div className="err">Cannot reach the API ({err}). Start it with: uvicorn app.main:app --reload (from /backend).</div>
  if (!jobs) return <div className="muted">Loading</div>
  const n = f => jobs.filter(f).length
  const crit = jobs.reduce((s, j) => s + (j.summary?.critical_flags || 0), 0)
  return (<div>
    <div className="head"><h1>Dashboard</h1><button className="btn primary" onClick={onNew}>Create new validation</button></div>
    <div className="stats">
      <div className="stat"><b>{jobs.length}</b><span>Validation requests</span></div>
      <div className="stat"><b>{n(j => ['UPLOADED', 'CONTRACT_PENDING', 'QUEUED', 'PROCESSING'].includes(j.status))}</b><span>Pending inspection</span></div>
      <div className="stat"><b className={crit ? 'red' : ''}>{crit}</b><span>Critical flags</span></div>
      <div className="stat"><b>{n(j => j.status === 'REVIEW_REQUIRED')}</b><span>Awaiting human approval</span></div>
    </div>
    <h2>Recent validations</h2>
    {jobs.length === 0 ? <div className="empty">No validations yet. Upload an approved and a revised label to start.</div> :
      <table className="tbl"><thead><tr><th>Product</th><th>Revision</th><th>Market</th><th>Reason</th><th>Status</th><th>Critical</th><th /></tr></thead><tbody>
        {jobs.map(j => <tr key={j.id}><td><b>{j.product_id}</b><div className="small muted">{j.product_name}</div></td><td>{j.old_version} to {j.new_version}</td><td>{j.market}</td><td>{j.change_reason}</td>
          <td><span className={'pill ' + (BADGE[j.status] || '')}>{j.status.replace('_', ' ').toLowerCase()}</span></td><td>{j.summary?.critical_flags ?? '-'}</td>
          <td><button className="btn" onClick={() => open(j)}>Open</button></td></tr>)}
      </tbody></table>}
  </div>)
}
