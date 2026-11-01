import React, { useState } from 'react'
import { api } from '../api.js'
const blobFile = async (url, name, type) => new File([await (await fetch(url)).blob()], name, { type })
export default function NewValidation({ onCreated }) {
  const [f, setF] = useState({ product_id: '', product_name: '', market: 'EU', language: 'English', old_version: 'V1', new_version: 'V2', change_reason: '', change_request: '' })
  const [oldPdf, setOld] = useState(null), [newPdf, setNew] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState('')
  const set = k => e => setF({ ...f, [k]: e.target.value })
  const sample = async () => {
    const d = await (await fetch('/sample/change_request.json')).json(); setF(d)
    setOld(await blobFile('/sample/old_label.pdf', 'old_label.pdf', 'application/pdf')); setNew(await blobFile('/sample/revised_label.pdf', 'revised_label.pdf', 'application/pdf'))
  }
  const submit = async () => {
    setErr(''); if (!oldPdf || !newPdf || !f.product_id || !f.change_request) { setErr('Product ID, both PDFs and the change request are required.'); return }
    setBusy(true)
    try {
      const fd = new FormData(); Object.entries(f).forEach(([k, v]) => fd.append(k, v)); fd.append('old_pdf', oldPdf); fd.append('new_pdf', newPdf)
      const job = await api.create(fd); await api.contract(job.id); onCreated(await api.job(job.id))
    } catch (e) { setErr(e.message); setBusy(false) }
  }
  const Inp = ({ k, label, ph }) => <label className="fld"><span>{label}</span><input value={f[k]} onChange={set(k)} placeholder={ph} /></label>
  const File_ = ({ label, file, setFile }) => <label className={'drop' + (file ? ' has' : '')}><span>{label}</span><b>{file ? file.name : 'Choose a PDF'}</b>
    <input type="file" accept="application/pdf" onChange={e => setFile(e.target.files[0])} hidden /></label>
  return (<div>
    <div className="head"><h1>New validation</h1><button className="btn" onClick={sample}>Load sample stent labels</button></div>
    <div className="grid2">
      <div className="card"><h2>Product and revision</h2>
        <div className="row"><Inp k="product_id" label="Product ID" ph="STENT101" /><Inp k="product_name" label="Product name" ph="Cardiac Stent" /></div>
        <div className="row"><Inp k="market" label="Target market" /><Inp k="language" label="Language" /></div>
        <div className="row"><Inp k="old_version" label="Approved version" /><Inp k="new_version" label="Revised version" /></div>
        <Inp k="change_reason" label="Change reason" ph="Sterilization update" /></div>
      <div className="card"><h2>Documents</h2>
        <div className="row"><File_ label="Approved label" file={oldPdf} setFile={setOld} /><File_ label="Revised label" file={newPdf} setFile={setNew} /></div>
        <label className="fld"><span>Change request</span><textarea rows="6" value={f.change_request} onChange={set('change_request')}
          placeholder="Update the sterilization method from EO to Radiation. Keep UDI, product identification, manufacturer details, and safety warnings unchanged." /></label></div>
    </div>
    {err && <div className="err">{err}</div>}
    <button className="btn primary big" disabled={busy} onClick={submit}>{busy ? 'Generating contract' : 'Generate change contract'}</button>
  </div>)
}
