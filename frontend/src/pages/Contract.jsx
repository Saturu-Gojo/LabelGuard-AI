import React, { useEffect, useState } from 'react'
import { api, FIELDS, sleep } from '../api.js'
const METHODS = ['', 'radiation', 'eo', 'steam']
export default function Contract({ job, setJob, go }) {
  const [c, setC] = useState(job.contract), [busy, setBusy] = useState(''), [err, setErr] = useState('')
  useEffect(() => { if (!c) api.contract(job.id).then(setC).catch(e => setErr(e.message)) }, [])
  if (!c) return <div className="muted">Generating contract</div>
  const locked = c.status === 'CONFIRMED'
  const allowed = c.allowed_changes.map(a => a.field), prot = c.protected_fields
  const addAllowed = f => f && setC({ ...c, allowed_changes: [...c.allowed_changes, { field: f, expected_value: null }], protected_fields: prot.filter(p => p !== f) })
  const addProt = f => f && setC({ ...c, protected_fields: [...prot, f], allowed_changes: c.allowed_changes.filter(a => a.field !== f) })
  const free = FIELDS => Object.keys(FIELDS).filter(k => !allowed.includes(k) && !prot.includes(k))
  const confirm = async () => {
    setErr(''); setBusy('Running inspection')
    try {
      await api.confirm(job.id, { change_id: c.change_id, reason: c.reason || '', allowed_changes: c.allowed_changes, protected_fields: c.protected_fields, requires_human_review: true })
      await api.run(job.id)
      for (;;) { await sleep(700); const s = await api.status(job.id); if (s.status === 'FAILED') throw new Error(s.error || 'Inspection failed'); if (!['QUEUED', 'PROCESSING'].includes(s.status)) break }
      setJob(await api.job(job.id)); go('workspace')
    } catch (e) { setErr(e.message); setBusy('') }
  }
  return (<div>
    <div className="head"><h1>Change contract</h1><span className="pill">{c.change_id} · drafted by {c.generated_by}</span></div>
    <div className="card"><div className="muted small">Change request</div><p className="quote">{job.change_request}</p></div>
    <p className="muted">Review what the system understood. The inspection treats this contract as the only authority on what may change.</p>
    <div className="grid2">
      <div className="card"><h2>Allowed changes</h2>
        {c.allowed_changes.length === 0 && <div className="empty">Nothing is allowed to change.</div>}
        {c.allowed_changes.map((a, i) => <div className="crow" key={a.field}><b>{FIELDS[a.field] || a.field}</b>
          {a.field.startsWith('sterilization') && <select disabled={locked} value={a.expected_value || ''} onChange={e => setC({ ...c, allowed_changes: c.allowed_changes.map((x, j) => j === i ? { ...x, expected_value: e.target.value || null } : x) })}>
            {METHODS.map(m => <option key={m} value={m}>{m ? 'Expected: ' + m : 'Any value'}</option>)}</select>}
          {!locked && <button className="x" onClick={() => setC({ ...c, allowed_changes: c.allowed_changes.filter((_, j) => j !== i) })}>Remove</button>}</div>)}
        {!locked && <select value="" onChange={e => addAllowed(e.target.value)}><option value="">Add allowed field</option>{free(FIELDS).map(k => <option key={k} value={k}>{FIELDS[k]}</option>)}</select>}
      </div>
      <div className="card"><h2>Protected fields</h2><div className="muted small">Any change here is flagged as unexpected.</div>
        <div className="chips">{prot.map(p => <span className="chip" key={p}>{FIELDS[p] || p}{!locked && <button onClick={() => setC({ ...c, protected_fields: prot.filter(x => x !== p) })}>x</button>}</span>)}</div>
        {!locked && <select value="" onChange={e => addProt(e.target.value)}><option value="">Add protected field</option>{free(FIELDS).map(k => <option key={k} value={k}>{FIELDS[k]}</option>)}</select>}
      </div>
    </div>
    {err && <div className="err">{err}</div>}
    {locked ? <button className="btn primary big" onClick={() => go('workspace')}>Open comparison</button> :
      <button className="btn primary big" disabled={!!busy} onClick={confirm}>{busy || 'Confirm contract and run inspection'}</button>}
  </div>)
}
