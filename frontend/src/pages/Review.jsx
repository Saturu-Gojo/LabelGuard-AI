import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
export default function Review({ job, setJob }) {
  const [r, setR] = useState(null), [j, setJ] = useState(job), [reviewer, setRev] = useState(''), [comment, setCom] = useState(''), [err, setErr] = useState(''), [audit, setAudit] = useState([])
  const load = async () => { setJ(await api.job(job.id)); setAudit(await api.audit(job.id)) }
  useEffect(() => { api.report(job.id).then(setR).catch(e => setErr(e.message)); load() }, [job.id])
  const decide = async decision => {
    setErr(''); if (!reviewer.trim()) { setErr('Enter the reviewer name.'); return }
    try { await api.approve(job.id, { reviewer, decision, comment }); setCom(''); await load(); setJob(await api.job(job.id)) } catch (e) { setErr(e.message) }
  }
  if (!r) return <div className="muted">{err || 'Loading'}</div>
  const s = r.summary, final = ['APPROVED', 'REJECTED'].includes(j.status)
  return (<div>
    <div className="head"><h1>Review and audit</h1><a className="btn" href={api.reportPdf(job.id)}>Download inspection report (PDF)</a></div>
    <div className="grid2">
      <div className="card"><h2>Reviewer decision</h2>
        <div className="row gap"><span className={'pill ' + ({ APPROVED: 'ok', REJECTED: 'bad', REVIEW_REQUIRED: 'warn' }[j.status] || '')}>{j.status.replace('_', ' ').toLowerCase()}</span>
          <span className="small muted">{s.unexpected} unexpected, {s.review_flags} need review</span></div>
        <label className="fld"><span>Reviewer</span><input value={reviewer} onChange={e => setRev(e.target.value)} placeholder="Name and role, for example A. Rao, QA" /></label>
        <label className="fld"><span>Comment {s.unexpected ? '(required to approve with open findings)' : ''}</span><textarea rows="3" value={comment} onChange={e => setCom(e.target.value)} /></label>
        {err && <div className="err">{err}</div>}
        <div className="row gap"><button className="btn" disabled={final} onClick={() => decide('APPROVE')}>Approve after resolution</button>
          <button className="btn" disabled={final} onClick={() => decide('REQUEST_CORRECTION')}>Request correction</button>
          <button className="btn danger" disabled={final} onClick={() => decide('REJECT')}>Reject</button></div>
        <div className="small muted">Approval must follow your organisation's controlled quality process.</div></div>
      <div className="card"><h2>Version record</h2>
        <div className="kv"><span>Approved label</span><code>{r.documents.old_sha256.slice(0, 20)}</code><span>Revised label</span><code>{r.documents.new_sha256.slice(0, 20)}</code>
          <span>Ruleset</span><code>{r.ruleset_version}</code><span>Contract</span><code>{r.contract.change_id}, confirmed by {r.contract.confirmed_by}</code></div>
        <h2>Decisions</h2>{j.approvals.length === 0 ? <div className="muted small">No decisions yet.</div> :
          j.approvals.map((a, i) => <div key={i} className="small"><b>{a.decision.replace('_', ' ').toLowerCase()}</b> by {a.reviewer} at {a.timestamp}{a.comment ? ': ' + a.comment : ''}</div>)}</div>
    </div>
    <h2>Audit trail</h2>
    <table className="tbl"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Detail</th></tr></thead><tbody>
      {audit.map((a, i) => <tr key={i}><td className="small">{a.timestamp}</td><td>{a.actor}</td><td>{a.action.replace(/_/g, ' ').toLowerCase()}</td><td className="small muted">{String(a.detail).slice(0, 120)}</td></tr>)}</tbody></table>
  </div>)
}
