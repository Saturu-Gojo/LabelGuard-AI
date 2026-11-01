import React, { useEffect, useState } from 'react'
import { api, CLS } from '../api.js'
export default function Findings({ job, go }) {
  const [r, setR] = useState(null), [open, setOpen] = useState({}), [err, setErr] = useState('')
  useEffect(() => { api.report(job.id).then(setR).catch(e => setErr(e.message)) }, [job.id])
  if (err) return <div className="err">{err}</div>
  if (!r) return <div className="muted">Loading</div>
  const s = r.summary
  return (<div>
    <div className="head"><h1>Validation findings</h1><button className="btn primary" onClick={() => go('review')}>Continue to review</button></div>
    <div className="stats">
      <div className="stat"><b>{s.passed_checks}</b><span>Passed checks</span></div><div className="stat"><b className="red">{s.critical_flags}</b><span>Critical flags</span></div>
      <div className="stat"><b className="amber">{s.review_flags}</b><span>Review flags</span></div><div className="stat"><b className="green">{s.expected}</b><span>Expected changes</span></div></div>
    {r.findings.map(f => <div key={f.id} className={'finding ' + f.classification}>
      <button className="fhead" onClick={() => setOpen({ ...open, [f.id]: !open[f.id] })}>
        <b>{f.id}</b><span>{f.field_label}</span><span className={'tag ' + f.classification}>{CLS[f.classification]}</span><span className="muted">{f.severity}</span><span className="grow" /><span className="muted small">{open[f.id] ? 'Hide' : 'Show'} evidence</span></button>
      <p>{f.explanation_ai || f.explanation}</p>
      {open[f.id] && <div className="fbody">
        <div className="kv"><span>Previous value</span><code>{f.old_value ?? 'none'}</code><span>New value</span><code>{f.new_value ?? 'none'}</code>
          <span>Change request</span><em>{f.contract_statement}</em><span>Detected by</span><em>{f.sources.join(', ')}</em>
          <span>Evidence</span><em>{f.evidence.length ? f.evidence.map((e, i) => <div key={i}>Page {e.page}, {e.source}{e.detail ? ', ' + e.detail : ''}, region [{(e.bbox_new || e.bbox_old || []).map(v => Math.round(v)).join(', ')}]</div>) : 'No region (requested change absent)'}</em>
          <span>Rule references</span><em>{f.rule_refs.join(', ') || 'none'} (ruleset {r.ruleset_version})</em><span>Recommended action</span><em>{f.recommended_action}</em></div></div>}
    </div>)}
    <h2>Validation checks</h2>
    <table className="tbl"><tbody>{r.checks.map((c, i) => <tr key={i}><td>{c.name}</td><td className={c.passed ? 'green' : 'red'}><b>{c.passed ? 'Pass' : 'Fail'}</b></td><td className="small muted">{String(c.detail).slice(0, 110)}</td></tr>)}</tbody></table>
  </div>)
}
