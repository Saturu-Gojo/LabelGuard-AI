import React, { useState } from 'react'
import Dashboard from './pages/Dashboard.jsx'
import NewValidation from './pages/NewValidation.jsx'
import Contract from './pages/Contract.jsx'
import Workspace from './pages/Workspace.jsx'
import Findings from './pages/Findings.jsx'
import Review from './pages/Review.jsx'

const STEPS = [['contract', 'Change contract'], ['workspace', 'Comparison'], ['findings', 'Findings'], ['review', 'Review and audit']]

export default function App() {
  const [view, setView] = useState('dashboard')
  const [job, setJob] = useState(null)
  const open = (j, v) => { setJob(j); setView(v || (['UPLOADED', 'CONTRACT_PENDING'].includes(j.status) ? 'contract' : 'workspace')) }
  const inJob = job && STEPS.some(s => s[0] === view)
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand"><span className="mark" />LabelGuard AI</div>
        <button className={view === 'dashboard' ? 'nav on' : 'nav'} onClick={() => setView('dashboard')}>Dashboard</button>
        <button className={view === 'new' ? 'nav on' : 'nav'} onClick={() => setView('new')}>New validation</button>
        {job && <div className="curjob"><div className="muted small">Current job</div><b>{job.product_id}</b><div className="small">{job.old_version} to {job.new_version} · {job.market}</div>
          {STEPS.map(([k, l]) => <button key={k} className={view === k ? 'nav sub on' : 'nav sub'} onClick={() => setView(k)}>{l}</button>)}</div>}
        <div className="foot small muted">Prototype with fictional test data. Not a regulatory determination.</div>
      </aside>
      <main className="main">
        {view === 'dashboard' && <Dashboard open={open} onNew={() => setView('new')} />}
        {view === 'new' && <NewValidation onCreated={j => open(j, 'contract')} />}
        {inJob && view === 'contract' && <Contract job={job} setJob={setJob} go={setView} />}
        {inJob && view === 'workspace' && <Workspace job={job} go={setView} />}
        {inJob && view === 'findings' && <Findings job={job} go={setView} />}
        {inJob && view === 'review' && <Review job={job} setJob={setJob} />}
      </main>
    </div>
  )
}
