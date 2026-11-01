import React, { useEffect, useState } from 'react'
import { api, CLS } from '../api.js'
const S = 150 / 72
const COLOR = { UNEXPECTED: 'var(--red)', REQUIRES_REVIEW: 'var(--amber)', EXPECTED: 'var(--green)' }

function Pane({ title, src, side, findings, sel, onSel, showAll, page }) {
  const [dim, setDim] = useState(null)
  const boxes = []
  findings.forEach(f => f.evidence.forEach((e, k) => {
    let bb = side === 'old' ? e.bbox_old : e.bbox_new, ghost = false
    if (!bb && f.change_type === 'removed' && side === 'new') { bb = e.bbox_old; ghost = true }
    if (!bb && f.change_type === 'added' && side === 'old') { bb = e.bbox_new; ghost = true }
    if (e.source === 'visual' || !bb || e.page !== page) return
    boxes.push({ f, bb, ghost, key: f.id + k })
  }))
  return (<div className="pane"><div className="panehead">{title}</div>
    <div className="imgwrap"><img src={src} alt={title} onLoad={e => setDim([e.target.naturalWidth, e.target.naturalHeight])} />
      {dim && boxes.map(({ f, bb, ghost, key }) => {
        const on = sel === f.id
        if (!showAll && !on) return null
        return <button key={key} className={'box' + (on ? ' on' : '') + (ghost ? ' ghost' : '')} title={ghost ? f.id + ' (missing here)' : f.id} onClick={() => onSel(f.id)}
          style={{ left: bb[0] * S / dim[0] * 100 + '%', top: bb[1] * S / dim[1] * 100 + '%', width: (bb[2] - bb[0]) * S / dim[0] * 100 + '%', height: (bb[3] - bb[1]) * S / dim[1] * 100 + '%', borderColor: COLOR[f.classification] }}>
          <span style={{ background: COLOR[f.classification] }}>{f.id}{ghost ? ' missing' : ''}</span></button>
      })}</div></div>)
}

export default function Workspace({ job, go }) {
  const [r, setR] = useState(null), [err, setErr] = useState(''), [filter, setFilter] = useState('ALL'), [sel, setSel] = useState(null), [showAll, setShowAll] = useState(true), [page, setPage] = useState(1)
  useEffect(() => { api.report(job.id).then(x => { setR(x); setSel(x.findings[0]?.id) }).catch(e => setErr(e.message)) }, [job.id])
  if (err) return <div className="err">{err}. Confirm the contract and run the inspection first.</div>
  if (!r) return <div className="muted">Loading inspection</div>
  const list = r.findings.filter(f => filter === 'ALL' || f.classification === filter)
  const cur = r.findings.find(f => f.id === sel)
  const s = r.summary
  return (<div>
    <div className="head"><h1>Comparison workspace</h1>
      <div className="row gap"><label className="small"><input type="checkbox" checked={showAll} onChange={e => setShowAll(e.target.checked)} /> Show all highlights</label>
        {r.pages.old.length > 1 && <select value={page} onChange={e => setPage(+e.target.value)}>{r.pages.old.map((_, i) => <option key={i} value={i + 1}>Page {i + 1}</option>)}</select>}
        <button className="btn" onClick={() => go('findings')}>Findings detail</button></div></div>
    <div className="banner"><b>{job.product_id}</b> {job.old_version} to {job.new_version} · {s.unexpected} unexpected · {s.review_flags} need review · {s.expected} expected · {s.passed_checks} checks passed · {r.processing_seconds}s</div>
    <div className="ws">
      <div className="panes">
        <Pane title={`Approved label (${job.old_version})`} src={api.file(job.id, r.pages.old[page - 1])} side="old" findings={r.findings} sel={sel} onSel={setSel} showAll={showAll} page={page} />
        <Pane title={`Revised label (${job.new_version})`} src={api.file(job.id, r.pages.new[page - 1])} side="new" findings={r.findings} sel={sel} onSel={setSel} showAll={showAll} page={page} />
      </div>
      <div className="list">
        <div className="seg">{[['ALL', 'All'], ['UNEXPECTED', 'Unexpected'], ['REQUIRES_REVIEW', 'Needs review'], ['EXPECTED', 'Expected']].map(([k, l]) =>
          <button key={k} className={filter === k ? 'on' : ''} onClick={() => setFilter(k)}>{l}</button>)}</div>
        {list.map(f => <button key={f.id} className={'frow' + (sel === f.id ? ' on' : '')} onClick={() => setSel(f.id)}>
          <i style={{ background: COLOR[f.classification] }} /><div><b>{f.id} {f.field_label}</b><div className="small muted">{CLS[f.classification]} · {f.severity} · {f.change_type.replace(/_/g, ' ')}</div></div></button>)}
        {list.length === 0 && <div className="empty">No findings in this filter.</div>}
        {cur && <div className="detail"><div className="small muted">{cur.id} detected by {cur.sources.join(', ')}</div>
          <p>{cur.explanation_ai || cur.explanation}</p>
          <div className="kv"><span>Previous</span><code>{cur.old_value ?? 'none'}</code><span>New</span><code>{cur.new_value ?? 'none'}</code></div>
          <div className="small"><b>Contract:</b> {cur.contract_statement}</div>
          <div className="small"><b>Next step:</b> {cur.recommended_action}</div></div>}
      </div>
    </div></div>)
}
