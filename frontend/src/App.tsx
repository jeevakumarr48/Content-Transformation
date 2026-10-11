import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle, ArrowRight, BarChart3, BookOpen, Check, CheckCircle2, ChevronRight, Clipboard,
  Clock3, CloudUpload, Copy, Database, Download, FileText, Gauge, GitBranch, Info,
  LayoutDashboard, Link2, Loader2, Menu, MessageSquare, Network, Pencil, Plus, RotateCcw,
  Send, Settings2, ShieldCheck, Sparkles, Terminal, Upload, Wand2, X, Zap,
} from 'lucide-react'
import { api } from './api'
import './App.css'
import './pipeline.css'

type View = 'dashboard' | 'sources' | 'dna' | 'studio' | 'history' | 'analytics' | 'settings'
type Notice = { type: 'success' | 'error' | 'info'; message: string }

const FORMATS = [
  ['Social Media Post', 'A short, scroll-stopping post'], ['LinkedIn Post', 'Professional thought leadership'],
  ['Instagram Carousel', 'Slide-by-slide visual narrative'], ['X/Twitter Thread', 'A connected series of concise posts'],
  ['YouTube Script', 'Long-form video narration'], ['30-second Reel Script', 'Fast hook, one insight, one CTA'],
  ['60-second Reel Script', 'Hook, 3 insights, conclusion, CTA'], ['Blog Article', 'Search-friendly deep dive'],
  ['Newsletter', 'Curated reader digest'], ['Executive Summary', 'Decision-ready brief'],
  ['Presentation Outline', 'Slide-by-slide structure'], ['Podcast Script', 'Conversational episode arc'],
  ['FAQ', 'Questions and grounded answers'], ['Study Notes', 'Retention-first learning guide'],
  ['Press Release', 'Journalistic announcement'], ['Marketing Copy', 'Benefit-led campaign copy'],
] as const
const AUDIENCES = ['School Student', 'College Student', 'Developer', 'Researcher', 'Business Executive', 'Customer', 'General Public', 'Technical Audience']
const LEVELS = ['Beginner', 'Intermediate', 'Expert']
const TONES = ['Professional', 'Educational', 'Conversational', 'Technical', 'Persuasive', 'Storytelling', 'Simple']
const TEMPLATES = [
  ['Research → Social Media', 'LinkedIn Post', 'General Public', 'Conversational'],
  ['Research → Reel', '60-second Reel Script', 'College Student', 'Storytelling'],
  ['Research → Executive Brief', 'Executive Summary', 'Business Executive', 'Professional'],
  ['Article → Newsletter', 'Newsletter', 'General Public', 'Educational'],
  ['Article → Carousel', 'Instagram Carousel', 'College Student', 'Educational'],
  ['Report → Presentation', 'Presentation Outline', 'Business Executive', 'Professional'],
  ['Technical → Beginner', 'Study Notes', 'School Student', 'Simple'],
] as const

const analysisStages = ['Reading source', 'Extracting content', 'Identifying concepts', 'Extracting claims', 'Building Content DNA', 'Building knowledge map', 'Preparing transformation engine']

function App() {
  const [view, setView] = useState<View>('dashboard')
  const [mobileNav, setMobileNav] = useState(false)
  const [sourceId, setSourceId] = useState<number | null>(null)
  const [source, setSource] = useState<any>(null)
  const [dna, setDna] = useState<any>(null)
  const [claims, setClaims] = useState<any[]>([])
  const [nodes, setNodes] = useState<any[]>([])
  const [chunks, setChunks] = useState<any[]>([])
  const [structure, setStructure] = useState<any>(null)
  const [outputs, setOutputs] = useState<any[]>([])
  const [activeOutput, setActiveOutput] = useState(0)
  const [editedContent, setEditedContent] = useState<Record<number, string>>({})
  const [selectedClaim, setSelectedClaim] = useState<any>(null)
  const [analysisStage, setAnalysisStage] = useState(-1)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [audience, setAudience] = useState('College Student')
  const [level, setLevel] = useState('Intermediate')
  const [tone, setTone] = useState('Professional')
  const [length, setLength] = useState<'short' | 'medium' | 'detailed'>('medium')
  const [selectedFormats, setSelectedFormats] = useState<string[]>(['60-second Reel Script'])
  const [inputMode, setInputMode] = useState<'upload' | 'paste' | 'url'>('upload')
  const [paste, setPaste] = useState('')
  const [url, setUrl] = useState('')
  const [history, setHistory] = useState<any[]>([])
  const [analytics, setAnalytics] = useState<any>(null)
  const [assistantInput, setAssistantInput] = useState('')
  const [assistantLog, setAssistantLog] = useState<{ role: 'user' | 'assistant'; text: string }[]>([])
  const fileRef = useRef<HTMLInputElement>(null)

  const notify = (type: Notice['type'], message: string) => {
    setNotice({ type, message })
    window.setTimeout(() => setNotice(null), 4200)
  }

  const hydrate = async (id: number) => {
    const [nextSource, nextChunks] = await Promise.all([api.getSource(id), api.getSourceChunks(id)])
    let nextStructure = null
    try { nextStructure = (await api.getSourceStructure(id)).structure } catch { nextStructure = null }
    setSourceId(id); setSource(nextSource); setChunks(nextChunks); setStructure(nextStructure); setDna(null); setClaims([]); setNodes([]); setOutputs([]); setEditedContent({})
  }

  const analyze = async (id = sourceId) => {
    if (!id) return
    setBusy(true); setAnalysisStage(0); setView('dna')
    try {
      for (let stage = 1; stage < analysisStages.length; stage += 1) {
        await new Promise(resolve => window.setTimeout(resolve, 240))
        setAnalysisStage(stage)
      }
      const result = await api.analyzeSource(id)
      setDna(result.content_dna); setClaims(result.claims); setNodes(result.knowledge_nodes)
      if (result.structure) setStructure(result.structure)
      setChunks(await api.getSourceChunks(id)); setAnalysisStage(-1); notify('success', 'Source intelligence is ready to use.')
    } catch (error: any) {
      setAnalysisStage(-1); notify('error', error.message || 'Analysis failed. Check the backend and try again.')
    } finally { setBusy(false) }
  }

  const loadDemo = async () => {
    setBusy(true)
    try { const result = await api.loadDemo(); await hydrate(result.source_id); await analyze(result.source_id); setView('dna') }
    catch (error: any) { notify('error', error.message || 'Could not load demo source.') }
    finally { setBusy(false) }
  }

  const upload = async (file?: File) => {
    if (!file && inputMode === 'paste' && !paste.trim()) return notify('error', 'Paste a source before uploading.')
    if (!file && inputMode === 'url' && !url.trim()) return notify('error', 'Enter a URL before uploading.')
    setBusy(true)
    try {
      const result = await api.uploadSource(file, inputMode === 'paste' ? paste : undefined, inputMode === 'url' ? url : undefined)
      await hydrate(result.source_id); notify('success', 'Source ingested. Analyze it before generating anything.'); setView('sources')
    } catch (error: any) { notify('error', error.message || 'Could not ingest this source.') }
    finally { setBusy(false) }
  }

  const transform = async () => {
    if (!sourceId) return notify('error', 'Load and analyze a source first.')
    if (!dna || !claims.length) return notify('error', 'Analyze the source before generating content.')
    if (!selectedFormats.length) return notify('error', 'Select at least one output format.')
    setBusy(true)
    try {
      const result = await api.transform({ source_id: sourceId, output_format: selectedFormats[0], output_formats: selectedFormats, audience, knowledge_level: level, tone, length })
      const nextOutputs = result.outputs || [result]
      setOutputs(nextOutputs); setActiveOutput(0); setSelectedClaim(null); setView('studio'); notify('success', `${nextOutputs.length} grounded output${nextOutputs.length === 1 ? '' : 's'} generated.`)
    } catch (error: any) { notify('error', error.message || 'Transformation failed.') }
    finally { setBusy(false) }
  }

  const regenerate = async () => {
    const current = outputs[activeOutput]
    if (!current?.transformation_id) return
    setBusy(true)
    try { const result = await api.regenerateTransformation(current.transformation_id); setOutputs(items => items.map((item, index) => index === activeOutput ? { ...item, ...result } : item)); notify('success', 'Output regenerated and rechecked.') }
    catch (error: any) { notify('error', error.message || 'Regeneration failed.') }
    finally { setBusy(false) }
  }

  const saveEdit = () => {
    const current = outputs[activeOutput]
    if (!current) return
    setOutputs(items => items.map((item, index) => index === activeOutput ? { ...item, content: editedContent[item.output_id] || item.content } : item))
    notify('success', 'Local edit saved. Run audit to re-check the edited version.')
  }

  const variations = async () => {
    if (!sourceId) return
    setBusy(true)
    try {
      const result = await api.generateVariations({ source_id: sourceId, output_format: selectedFormats[0], audience, knowledge_level: level, tone })
      setOutputs(result.variations || []); setActiveOutput(0); notify('success', 'Three grounded variations are ready.')
    } catch (error: any) { notify('error', error.message || 'Could not generate variations.') }
    finally { setBusy(false) }
  }

  const sendAssistant = async (preset?: string) => {
    const message = (preset ?? assistantInput).trim()
    if (!message) return
    setAssistantInput('')
    setAssistantLog(log => [...log, { role: 'user', text: message }])
    setBusy(true)
    try {
      const result = await api.chat(message, outputs[activeOutput]?.transformation_id, currentContent)
      const active = outputs[activeOutput]
      if (result.modified_content && active) {
        setOutputs(items => items.map((item, index) => index === activeOutput ? { ...item, content: result.modified_content } : item))
        setEditedContent(map => ({ ...map, [active.output_id]: result.modified_content }))
      }
      if (result.new_audience) setAudience(result.new_audience)
      if (result.new_tone) setTone(result.new_tone)
      if (result.highlight_claim) {
        const match = claims.find(claim => claim.claim_text === result.highlight_claim)
        if (match) setSelectedClaim(match)
      }
      setAssistantLog(log => [...log, { role: 'assistant', text: result.response || 'Done.' }])
      if (result.modified_content) notify('success', 'Assistant updated the current output.')
    } catch (error: any) {
      setAssistantLog(log => [...log, { role: 'assistant', text: 'Error: ' + (error.message || 'request failed') }])
    } finally { setBusy(false) }
  }

  const exportCurrent = async (format: string) => {
    if (!currentContent) return
    try {
      const result = await api.exportContent(currentContent, format, `transformiq-${outputs[activeOutput]?.output_format || 'output'}`, { source_id: sourceId, audience })
      const data = result.binary ? Uint8Array.from(atob(result.content_base64), char => char.charCodeAt(0)) : result.content
      const blob = new Blob([data], { type: result.mime_type }); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = result.filename; link.click(); URL.revokeObjectURL(link.href)
      notify('success', `${format.toUpperCase()} export downloaded.`)
    } catch (error: any) { notify('error', error.message || 'Export failed.') }
  }

  const loadHistory = async () => { try { setHistory(await api.getTransformations()) } catch (error: any) { notify('error', error.message || 'Could not load history.') } }
  const loadAnalytics = async () => { try { setAnalytics(await api.getAnalytics()) } catch (error: any) { notify('error', error.message || 'Could not load analytics.') } }

  useEffect(() => {
    const loadViewData = async () => {
      if (view === 'history') await loadHistory()
      if (view === 'analytics') await loadAnalytics()
    }
    void loadViewData()
  }, [view])

  const current = outputs[activeOutput]
  const currentContent = current ? editedContent[current.output_id] ?? current.content ?? '' : ''

  return <div className="app-shell">
    <Sidebar view={view} setView={setView} mobileNav={mobileNav} setMobileNav={setMobileNav} onDemo={loadDemo} busy={busy} hasSource={!!sourceId} />
    <div className="app-main">
      <Topbar view={view} onMenu={() => setMobileNav(true)} />
      {notice && <div className={`notice notice-${notice.type}`}><span>{notice.type === 'error' ? <AlertTriangle size={16} /> : notice.type === 'success' ? <CheckCircle2 size={16} /> : <Info size={16} />}</span>{notice.message}<button onClick={() => setNotice(null)}><X size={14} /></button></div>}
      <div className="page-wrap">
        {view === 'dashboard' && <Dashboard source={source} dna={dna} claims={claims} outputs={outputs} analytics={analytics} onDemo={loadDemo} go={setView} busy={busy} />}
        {view === 'sources' && <SourceIntake source={source} inputMode={inputMode} setInputMode={setInputMode} paste={paste} setPaste={setPaste} url={url} setUrl={setUrl} fileRef={fileRef} onUpload={upload} onDemo={loadDemo} onAnalyze={() => analyze()} busy={busy} analysisStage={analysisStage} />}
        {view === 'dna' && <DNAView source={source} dna={dna} claims={claims} nodes={nodes} chunks={chunks} structure={structure} onAnalyze={() => analyze()} onStudio={() => setView('studio')} onSources={() => setView('sources')} busy={busy} analysisStage={analysisStage} selectedClaim={selectedClaim} setSelectedClaim={setSelectedClaim} />}
        {view === 'studio' && <Studio source={source} dna={dna} claims={claims} nodes={nodes} outputs={outputs} current={current} currentContent={currentContent} selectedFormats={selectedFormats} setSelectedFormats={setSelectedFormats} audience={audience} setAudience={setAudience} level={level} setLevel={setLevel} tone={tone} setTone={setTone} length={length} setLength={setLength} onTransform={transform} onRegenerate={regenerate} onVariations={variations} onSaveEdit={saveEdit} setEditedContent={(value: string) => current && setEditedContent(map => ({ ...map, [current.output_id]: value }))} exportCurrent={exportCurrent} selectedClaim={selectedClaim} setSelectedClaim={setSelectedClaim} onAssistant={sendAssistant} assistantInput={assistantInput} setAssistantInput={setAssistantInput} assistantLog={assistantLog} busy={busy} activeOutput={activeOutput} setActiveOutput={setActiveOutput} />}
        {view === 'history' && <HistoryView history={history} onRefresh={loadHistory} />}
        {view === 'analytics' && <AnalyticsView analytics={analytics} />}
        {view === 'settings' && <SettingsView />}
      </div>
    </div>
  </div>
}

function Sidebar({ view, setView, mobileNav, setMobileNav, onDemo, busy, hasSource }: any) {
  const items = [
    ['dashboard', 'Dashboard', LayoutDashboard], ['sources', 'My Sources', Database], ['dna', 'Content DNA', DnaIcon], ['studio', 'Transformation Studio', Wand2], ['history', 'Transformation History', Clock3], ['analytics', 'Analytics', BarChart3], ['settings', 'Settings', Settings2],
  ] as const
  return <>
    {mobileNav && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
    <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <div className="brand-row"><div className="brand-mark"><Network size={19} /></div><div><strong>TRANSFORMIQ</strong><span>reasoning layer / 01</span></div><button className="mobile-close" onClick={() => setMobileNav(false)}><X size={18} /></button></div>
      <div className="workspace-label">Workspace <span className="live-dot" /> demo ready</div>
      <nav>{items.map(([key, label, Icon]) => <button key={key} className={`nav-item ${view === key ? 'active' : ''}`} onClick={() => { setView(key); setMobileNav(false) }}><Icon size={17} /><span>{label}</span>{key === 'studio' && hasSource && <i />}</button>)}</nav>
      <div className="sidebar-bottom"><div className="source-state"><span className={hasSource ? 'state-led state-live' : 'state-led'} />{hasSource ? <span>Source connected</span> : <span>No source connected</span>}<ChevronRight size={14} /></div><button className="demo-button" onClick={onDemo} disabled={busy}><Sparkles size={16} />{busy ? 'Working...' : 'Try Live Demo'}<ArrowRight size={15} /></button></div>
    </aside>
  </>
}

function Topbar({ view, onMenu }: { view: View; onMenu: () => void }) {
  const labels: Record<View, string> = { dashboard: 'Overview', sources: 'Source intake', dna: 'Content DNA', studio: 'Transformation Studio', history: 'Transformation history', analytics: 'Analytics', settings: 'Settings' }
  return <header className="topbar"><button className="mobile-menu" onClick={onMenu}><Menu size={20} /></button><div className="crumb"><span>TRANSFORMIQ</span><ChevronRight size={14} /><strong>{labels[view]}</strong></div><div className="topbar-right"><span className="environment"><span className="live-dot" /> DEMO MODE</span><div className="avatar">JD</div></div></header>
}

function Dashboard({ source, dna, claims, outputs, analytics, onDemo, go, busy }: any) {
  const statData = [
    ['Sources', analytics?.total_sources || (source ? 1 : 0), FileText, 'ink'], ['Transformations', analytics?.total_transformations || outputs.length, Wand2, 'cobalt'], ['Verified claims', analytics?.verified_claims || claims.length, ShieldCheck, 'lime'], ['Avg quality', `${analytics?.average_quality || outputs[0]?.quality_scores?.overall_score || 0}%`, Gauge, 'peach'],
  ] as const
  return <section className="dashboard-view"><div className="hero-grid"><div className="hero-copy"><p className="eyebrow">SOURCE-GROUNDED INTELLIGENCE</p><h1>Turn one source<br /><em>into a signal.</em></h1><p className="hero-lede">TransformIQ maps what your source means before it writes anything. Every output is audience-fit, claim-aware, and ready to trace back.</p><div className="hero-actions"><button className="button button-dark" onClick={() => go('sources')}><Plus size={17} /> New transformation</button><button className="text-button" onClick={onDemo} disabled={busy}><Sparkles size={16} /> {busy ? 'Loading demo...' : 'Try the live demo'} <ArrowRight size={15} /></button></div></div><PipelinePreview /></div>
    <div className="stat-grid">{statData.map(([label, value, Icon, color]) => <div className={`stat-card stat-${color}`} key={label}><div className="stat-icon"><Icon size={18} /></div><strong>{value}</strong><span>{label}</span></div>)}</div>
    {source ? <div className="dashboard-lower"><div className="active-source-panel"><div className="section-heading"><div><p className="eyebrow">ACTIVE SOURCE</p><h2>{source.filename}</h2></div><span className="status-pill status-live"><span className="live-dot" /> analyzed</span></div><div className="source-summary"><div className="source-file-icon"><FileText size={24} /></div><div><strong>{dna?.core_topic || 'Source awaiting analysis'}</strong><p>{dna?.summary || 'Analyze this source to reveal its Content DNA, factual claims, and knowledge map.'}</p></div></div><div className="source-actions"><button className="button button-cobalt" onClick={() => go(dna ? 'studio' : 'dna')}>{dna ? 'Open studio' : 'Analyze source'} <ArrowRight size={15} /></button><button className="button button-ghost" onClick={() => go('dna')}>View intelligence</button></div></div><ActivityRail outputs={outputs} /></div> : <div className="empty-dashboard"><div className="empty-icon"><CloudUpload size={28} /></div><div><h2>Your intelligence workspace is empty.</h2><p>Start with a source. We will show our reasoning before we ask you to publish.</p></div><button className="button button-cobalt" onClick={() => go('sources')}>Add a source <ArrowRight size={15} /></button></div>}
  </section>
}

function PipelinePreview() {
  const steps = [['01', 'SOURCE', 'Research report'], ['02', 'UNDERSTAND', 'Content DNA'], ['03', 'TRACE', 'Claim ledger'], ['04', 'TRANSFORM', 'Audience outputs']]
  return <div className="pipeline-card"><div className="pipeline-top"><span>LIVE PIPELINE</span><span className="pipeline-status"><span className="live-dot" /> ready</span></div>{steps.map(([number, title, copy], index) => <div className="pipeline-step" key={title}><span className="step-number">{number}</span><div><strong>{title}</strong><span>{copy}</span></div>{index < steps.length - 1 && <div className="step-line" />}<ChevronRight size={16} className="step-arrow" /></div>)}<div className="pipeline-footer"><GitBranch size={15} /> Meaning stays attached at every stage</div></div>
}

function ActivityRail({ outputs }: any) {
  return <div className="activity-rail"><div className="section-heading"><div><p className="eyebrow">RECENT ACTIVITY</p><h2>Output ledger</h2></div><span className="mono-caption">{outputs.length} outputs</span></div>{outputs.length ? outputs.slice(0, 3).map((item: any) => <div className="activity-row" key={item.output_id}><div className="activity-mark"><Check size={14} /></div><div><strong>{item.output_format}</strong><span>{item.estimated_length || 'Generated output'}</span></div><span className="quality-mini">{item.quality_scores?.overall_score || 0}%</span></div>) : <div className="quiet-note"><Clock3 size={16} /> Your generated outputs will land here.</div>}</div>
}

function SourceIntake({ source, inputMode, setInputMode, paste, setPaste, url, setUrl, fileRef, onUpload, onDemo, onAnalyze, busy, analysisStage }: any) {
  return <section className="source-view"><PageTitle eyebrow="SOURCE INTAKE" title="Start with the information, not the prompt." copy="Bring one source into the reasoning layer. Generation stays locked until the source has been understood." />{source && <div className="ingested-strip"><div className="source-file-icon"><FileText size={20} /></div><div><strong>{source.filename}</strong><span>{source.file_type} · {source.page_count || 1} page{source.page_count === 1 ? '' : 's'} · source #{source.id}</span></div><button className="button button-ghost" onClick={onAnalyze} disabled={busy}>{analysisStage >= 0 ? 'Analyzing...' : 'Analyze content'} <ArrowRight size={15} /></button></div>}<div className="intake-grid"><div className="intake-card"><div className="mode-tabs">{[['upload', Upload, 'Upload file'], ['paste', Clipboard, 'Paste text'], ['url', Link2, 'Use URL']].map(([mode, Icon, label]: any) => <button key={mode} className={inputMode === mode ? 'selected' : ''} onClick={() => setInputMode(mode)}><Icon size={15} />{label}</button>)}</div>{inputMode === 'upload' && <button className="dropzone" onClick={() => fileRef.current?.click()}><input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md,.markdown" hidden onChange={event => event.target.files?.[0] && onUpload(event.target.files[0])} /><span className="drop-icon"><CloudUpload size={25} /></span><strong>Drop a source or browse files</strong><span>PDF, DOCX, TXT, or Markdown · max 10 MB</span><small>Files are extracted server-side. Nothing is generated yet.</small></button>}{inputMode === 'paste' && <div className="text-input-wrap"><textarea value={paste} onChange={event => setPaste(event.target.value)} placeholder="Paste an article, report, research excerpt, or meeting notes..." /><div className="input-footer"><span>{paste.trim() ? `${paste.trim().split(/\s+/).length} words` : 'Plain text or Markdown'}</span><button className="button button-cobalt" onClick={() => onUpload()} disabled={busy || !paste.trim()}>{busy ? <Loader2 className="spin" size={15} /> : <Upload size={15} />} Ingest text</button></div></div>}{inputMode === 'url' && <div className="url-input-wrap"><Link2 size={20} /><input value={url} onChange={event => setUrl(event.target.value)} placeholder="https://example.com/research-report" /><button className="button button-cobalt" onClick={() => onUpload()} disabled={busy || !url.trim()}>{busy ? <Loader2 className="spin" size={15} /> : <ArrowRight size={15} />} Fetch</button><p>We extract readable page content and sanitize HTML before analysis.</p></div>}</div><aside className="intake-aside"><div className="aside-heading"><ShieldCheck size={17} /><strong>What happens next</strong></div>{['Extract readable content', 'Build your Content DNA', 'Map concepts and evidence', 'Extract claims with locations', 'Unlock source-grounded outputs'].map((item, index) => <div className="next-step" key={item}><span>{index + 1}</span>{item}<Check size={14} /></div>)}<div className="demo-callout"><Sparkles size={17} /><div><strong>Need a fast proof?</strong><p>Load our education research report and run the entire flagship demo.</p><button onClick={onDemo} disabled={busy}>Load demo source <ArrowRight size={14} /></button></div></div></aside></div>{analysisStage >= 0 && <AnalysisProgress stage={analysisStage} />}</section>
}

function AnalysisProgress({ stage }: { stage: number }) {
  return <div className="analysis-progress"><div className="progress-heading"><div><p className="eyebrow">ANALYSIS IN PROGRESS</p><h2>Building your source model</h2></div><span>{stage + 1}/{analysisStages.length}</span></div><div className="progress-track"><span style={{ width: `${((stage + 1) / analysisStages.length) * 100}%` }} /></div><div className="progress-stages">{analysisStages.map((item, index) => <div className={index < stage ? 'done' : index === stage ? 'current' : ''} key={item}><span>{index < stage ? <Check size={13} /> : index === stage ? <Loader2 size={13} className="spin" /> : index + 1}</span>{item}</div>)}</div></div>
}

function DNAView({ source, dna, claims, nodes, chunks, structure, onAnalyze, onStudio, onSources, busy, analysisStage, selectedClaim, setSelectedClaim }: any) {
  if (!source) return <EmptyState title="No source connected" copy="Bring in a source before opening Content DNA." action="Go to source intake" onClick={onSources} />
  if (!dna) return <section className="dna-view"><PageTitle eyebrow="CONTENT DNA" title="Understand the source before you transform it." copy="The source model keeps your outputs grounded in what is actually present." /><div className="analysis-gate"><div className="gate-icon"><DnaIcon size={30} /></div><h2>Your source is ingested, not understood.</h2><p>Run analysis to extract topics, concepts, claims, evidence, audiences, and constraints.</p><button className="button button-cobalt" onClick={onAnalyze} disabled={busy}>{analysisStage >= 0 ? <><Loader2 size={16} className="spin" /> {analysisStages[analysisStage]}</> : <><Sparkles size={16} /> Analyze source</>}</button>{analysisStage >= 0 && <AnalysisProgress stage={analysisStage} />}</div></section>
  return <section className="dna-view"><div className="dna-header"><div><p className="eyebrow">SOURCE INTELLIGENCE / #{source.id}</p><h1>Content DNA</h1><p>{source.filename} · {dna.content_category}</p></div><button className="button button-cobalt" onClick={onStudio}>Transform this source <ArrowRight size={15} /></button></div><div className="dna-hero"><div className="dna-core"><span className="dna-kicker">CORE TOPIC</span><h2>{dna.core_topic}</h2><p>{dna.summary}</p><div className="dna-meta"><span><Clock3 size={14} /> {dna.estimated_reading_time}</span><span><Gauge size={14} /> {dna.complexity_level}</span><span><FileText size={14} /> {claims.length} claims</span></div></div><div className="dna-objective"><span className="dna-kicker">MAIN OBJECTIVE</span><p>{dna.main_objective}</p><div className="objective-rule" /><span className="dna-kicker">TONE</span><strong>{dna.tone}</strong></div></div><div className="dna-grid"><DnaList title="Key arguments" items={dna.key_arguments} /><DnaList title="Key facts" items={dna.key_facts} /><DnaList title="Statistics" items={dna.statistics} /><DnaList title="Target audiences" items={dna.target_audiences} pills /><DnaList title="Keywords" items={dna.important_keywords} pills /><DnaList title="Conclusions" items={dna.conclusions} /></div><DocumentStructure structure={structure} /><KnowledgeMap nodes={nodes} onSelect={setSelectedClaim} selected={selectedClaim} /><ClaimsLedger claims={claims} onSelect={setSelectedClaim} selected={selectedClaim} chunks={chunks} /></section>
}

function DnaList({ title, items = [], pills }: any) { return <div className="dna-list"><div className="list-title"><span>{title}</span><span>{items.length}</span></div><div className={pills ? 'pill-list' : 'bullet-list'}>{items.map((item: string) => pills ? <span key={item}>{item}</span> : <p key={item}><span />{item}</p>)}</div></div> }

function DocumentStructure({ structure }: any) {
  if (!structure) return null
  const stats = structure.stats || {}
  return <div className="structure-panel">
    <div className="section-heading"><div><p className="eyebrow">DOCUMENT PIPELINE</p><h2>Document structure</h2></div><span className="mono-caption"><Database size={14} /> {stats.sections || 0} sections · {stats.chunks || 0} chunks</span></div>
    <div className="structure-grid">
      <div><span className="field-label">SECTIONS DETECTED</span><ul className="struct-list">{(structure.sections || []).map((s: any, i: number) => <li key={i}><b>{s.heading}</b><small>{s.paragraphs}p · {s.list_items} list · {s.tables} table{s.tables === 1 ? '' : 's'} · p{s.page}</small></li>)}</ul></div>
      <div><span className="field-label">DEFINITIONS</span>{structure.definitions?.length ? <ul className="struct-list">{(structure.definitions || []).map((d: any, i: number) => <li key={i}><b>{d.term}</b><small>{d.definition}</small></li>)}</ul> : <p className="struct-empty">None detected</p>}
        <span className="field-label" style={{ marginTop: 12, display: 'block' }}>DATES</span><div className="chip-row">{(structure.dates || []).map((d: string, i: number) => <span className="chip" key={i}>{d}</span>)}{!structure.dates?.length && <span className="struct-empty">None</span>}</div></div>
      <div><span className="field-label">NUMERICAL VALUES</span><div className="chip-row">{(structure.numbers || []).map((n: string, i: number) => <span className="chip chip-num" key={i}>{n}</span>)}</div>
        <span className="field-label" style={{ marginTop: 12, display: 'block' }}>ENTITIES</span><div className="chip-row">{(structure.entities || []).map((e: string, i: number) => <span className="chip" key={i}>{e}</span>)}</div></div>
    </div>
    {structure.tables?.length > 0 && <div className="struct-tables"><span className="field-label">TABLES EXTRACTED ({structure.tables.length})</span>{structure.tables.map((t: any, i: number) => <table key={i} className="struct-table">{t.rows.map((row: string[], r: number) => <tr key={r}>{row.map((cell, c) => r === 0 ? <th key={c}>{cell}</th> : <td key={c}>{cell}</td>)}</tr>)}</table>)}</div>}
    <div className="structure-stats">{[['Blocks', stats.blocks], ['Sections', stats.sections], ['Chunks', stats.chunks], ['Tables', stats.tables], ['Definitions', stats.definitions], ['Entities', stats.entities], ['Dates', stats.dates], ['Numbers', stats.numbers]].map(([label, value]: any) => <span key={label}><b>{value ?? 0}</b>{label}</span>)}</div>
  </div>
}

function KnowledgeMap({ nodes, onSelect, selected }: any) {
  const levels = ['topic', 'concept', 'argument', 'evidence', 'example', 'challenge', 'conclusion']
  const labels: Record<string, string> = { topic: 'Topic', concept: 'Concepts', argument: 'Arguments', evidence: 'Evidence', example: 'Examples', challenge: 'Tensions', conclusion: 'Conclusion' }
  return <div className="knowledge-section"><div className="section-heading"><div><p className="eyebrow">STRUCTURED REPRESENTATION</p><h2>Content knowledge map</h2></div><span className="mono-caption"><Network size={14} /> click a node to inspect evidence</span></div><div className="knowledge-map">{levels.map(level => { const levelNodes = nodes.filter((node: any) => node.node_type === level); if (!levelNodes.length) return null; return <div className="map-row" key={level}><div className="map-label">{labels[level]}</div><div className="map-nodes">{levelNodes.map((node: any) => <button key={node.id} className={`map-node node-${level} ${selected?.id === node.id ? 'selected' : ''}`} onClick={() => onSelect(node)}><span>{node.label}</span><small>{node.content}</small></button>)}</div></div> })}</div>{selected?.source_text && <div className="evidence-drawer"><div><span className="evidence-tag">SOURCE EVIDENCE</span><strong>{selected.label || selected.claim_text}</strong></div><p>“{selected.source_text}”</p><span className="mono-caption">{selected.source_location || 'Source chunk'}</span></div>}</div>
}

function ClaimsLedger({ claims, onSelect, selected, chunks }: any) { return <div className="claims-section"><div className="section-heading"><div><p className="eyebrow">CLAIM TRACEABILITY ENGINE</p><h2>Claim ledger</h2></div><span className="verified-summary"><ShieldCheck size={15} /> {claims.length} source claims extracted</span></div><div className="claims-table"><div className="claim-head"><span>Claim</span><span>Importance</span><span>Confidence</span><span>Location</span></div>{claims.map((claim: any) => <button className={`claim-row ${selected?.id === claim.id ? 'selected' : ''}`} key={claim.id} onClick={() => onSelect(claim)}><span className="claim-copy"><span className="claim-dot" />{claim.claim_text}</span><span><b className={`importance importance-${claim.importance}`}>{claim.importance}</b></span><span className="confidence"><span className="confidence-bar"><i style={{ width: `${claim.confidence * 100}%` }} /></span>{Math.round(claim.confidence * 100)}%</span><span className="claim-location">{claim.source_location || `Chunk ${chunks.findIndex((chunk: any) => chunk.chunk_text === claim.supporting_source_text) + 1}`}</span></button>)}</div></div> }

function LengthControl({ value, onChange }: any) { return <div className="length-control"><span className="field-label">DESIRED LENGTH</span><div>{(['short', 'medium', 'detailed'] as const).map(item => <button className={value === item ? 'selected' : ''} key={item} onClick={() => onChange(item)}>{item[0].toUpperCase() + item.slice(1)}</button>)}</div></div> }

function Studio({ source, dna, claims, outputs, current, currentContent, selectedFormats, setSelectedFormats, audience, setAudience, level, setLevel, tone, setTone, length, setLength, onTransform, onRegenerate, onVariations, onSaveEdit, setEditedContent, exportCurrent, selectedClaim, setSelectedClaim, onAssistant, assistantInput, setAssistantInput, assistantLog, busy, activeOutput, setActiveOutput }: any) {
  return <section className="studio-view"><div className="studio-header"><div><p className="eyebrow">SOURCE → OUTPUT / {source?.filename || 'NO SOURCE'}</p><h1>Transformation Studio</h1><p>Choose the audience, workstream, length and job. The source stays in the room.</p></div><div className="studio-header-tools"><span className="reasoning-badge"><GitBranch size={15} /> claim-aware generation</span><LengthControl value={length} onChange={setLength} /></div></div><div className="studio-layout"><StudioControls selectedFormats={selectedFormats} setSelectedFormats={setSelectedFormats} audience={audience} setAudience={setAudience} level={level} setLevel={setLevel} tone={tone} setTone={setTone} onTransform={onTransform} onVariations={onVariations} busy={busy} /> <div className="output-column">{outputs.length > 0 ? <><OutputTabs outputs={outputs} active={activeOutput} setActive={setActiveOutput} /><TransformationPlan plan={current?.transformation_plan} /><OutputEditor current={current} currentContent={currentContent} setEditedContent={setEditedContent} onSave={onSaveEdit} onRegenerate={onRegenerate} exportCurrent={exportCurrent} busy={busy} /><ScorePanel current={current} /><Storyboard storyboard={current?.storyboard} /><Verification current={current} selectedClaim={selectedClaim} setSelectedClaim={setSelectedClaim} source={source} /><SourceValidation validation={current?.validation} /><SourceCompare source={source} currentContent={currentContent} selectedClaim={selectedClaim} setSelectedClaim={setSelectedClaim} claims={claims} /><Assistant input={assistantInput} setInput={setAssistantInput} onSend={onAssistant} log={assistantLog} busy={busy} /></> : <div className="studio-empty"><div className="empty-icon"><Wand2 size={27} /></div><h2>Make the source useful somewhere new.</h2><p>Pick one or more formats, then transform. Every output arrives with a score and its claim trail.</p>{!dna && <span className="warning-inline"><AlertTriangle size={14} /> Analyze your source first in Content DNA.</span>}</div>}</div></div></section>
}

function StudioControls({ selectedFormats, setSelectedFormats, audience, setAudience, level, setLevel, tone, setTone, onTransform, onVariations, busy }: any) {
  const [templateOpen, setTemplateOpen] = useState(false)
  const toggle = (format: string) => setSelectedFormats((formats: string[]) => formats.includes(format) ? formats.filter(item => item !== format) : [...formats, format])
  const applyTemplate = (template: readonly string[]) => { setSelectedFormats([template[1]]); setAudience(template[2]); setTone(template[3]); setTemplateOpen(false) }
  return <aside className="studio-controls"><div className="control-block"><div className="control-title"><span>01</span><div><strong>Output formats</strong><small>{selectedFormats.length} selected · batch-ready</small></div></div><div className="format-picker">{FORMATS.map(([format, description]) => <button key={format} className={selectedFormats.includes(format) ? 'picked' : ''} onClick={() => toggle(format)}><span>{selectedFormats.includes(format) ? <Check size={13} /> : <Plus size={13} />}</span><div><strong>{format}</strong><small>{description}</small></div></button>)}</div></div><div className="control-block"><div className="control-title"><span>02</span><div><strong>Audience model</strong><small>Who should understand this?</small></div></div><Select value={audience} onChange={setAudience} options={AUDIENCES} /><div className="segmented">{LEVELS.map(item => <button className={level === item ? 'selected' : ''} key={item} onClick={() => setLevel(item)}>{item}</button>)}</div></div><div className="control-block"><div className="control-title"><span>03</span><div><strong>Voice</strong><small>How should it land?</small></div></div><div className="tone-grid">{TONES.map(item => <button className={tone === item ? 'selected' : ''} key={item} onClick={() => setTone(item)}>{item}</button>)}</div></div><div className="template-control"><button onClick={() => setTemplateOpen(open => !open)}><BookOpen size={15} /> Use a transformation template <ChevronRight size={14} /></button>{templateOpen && <div className="template-menu">{TEMPLATES.map(template => <button key={template[0]} onClick={() => applyTemplate(template)}>{template[0]}<small>{template[1]} · {template[2]}</small></button>)}</div>}</div><button className="button button-dark transform-button" onClick={onTransform} disabled={busy || !selectedFormats.length}>{busy ? <><Loader2 className="spin" size={17} /> Mapping claims...</> : <><Zap size={17} /> Transform {selectedFormats.length ? `${selectedFormats.length} output${selectedFormats.length === 1 ? '' : 's'}` : 'content'}</>}</button><button className="button button-ghost variation-button" onClick={onVariations} disabled={busy || !selectedFormats.length}><Sparkles size={15} /> Generate 3 variations</button></aside>
}

function Select({ value, onChange, options }: any) { return <div className="select-wrap"><select value={value} onChange={event => onChange(event.target.value)}>{options.map((option: string) => <option key={option}>{option}</option>)}</select><ChevronRight size={14} /></div> }

function OutputTabs({ outputs, active, setActive }: any) { return <div className="output-tabs">{outputs.map((output: any, index: number) => <button key={`${output.output_id || index}-${output.output_format}`} className={active === index ? 'active' : ''} onClick={() => setActive(index)}><span>{String(index + 1).padStart(2, '0')}</span>{output.output_format}<i>{output.quality_scores?.overall_score || 0}%</i></button>)}</div> }

function OutputEditor({ current, currentContent, setEditedContent, onSave, onRegenerate, exportCurrent, busy }: any) { const [editing, setEditing] = useState(false); return <div className="output-editor"><div className="output-editor-head"><div><span className="output-label">GENERATED OUTPUT</span><h2>{current.output_format}</h2><p>{current.estimated_length || 'Audience-specific draft'} · {current.target_audience || 'College Student'}</p></div><div className="output-actions"><button title="Regenerate" onClick={onRegenerate} disabled={busy}><RotateCcw size={15} /></button><button title="Edit" className={editing ? 'active' : ''} onClick={() => setEditing(!editing)}><Pencil size={15} /></button><button title="Copy" onClick={() => { navigator.clipboard.writeText(currentContent) }}><Copy size={15} /></button><div className="export-menu"><button title="Export"><Download size={15} /></button><div><button onClick={() => exportCurrent('txt')}>TXT</button><button onClick={() => exportCurrent('markdown')}>MD</button><button onClick={() => exportCurrent('json')}>JSON</button><button onClick={() => exportCurrent('docx')}>DOCX</button><button onClick={() => exportCurrent('pdf')}>PDF</button></div></div></div></div><div className={`editor-paper ${editing ? 'editing' : ''}`}>{editing ? <><textarea value={currentContent} onChange={event => setEditedContent(event.target.value)} /><button className="button button-cobalt save-edit" onClick={() => { onSave(); setEditing(false) }}><Check size={15} /> Save local edit</button></> : <div className="formatted-output">{currentContent.split('\n').map((line: string, index: number) => <p key={index} className={line.startsWith('#') ? 'content-heading' : line.startsWith('[') ? 'content-scene' : line.trim() === '' ? 'content-space' : ''}>{line || '\u00a0'}</p>)}</div>}</div></div> }

function TransformationPlan({ plan }: any) { if (!plan) return null; return <div className="plan-panel"><div className="section-heading"><div><p className="eyebrow">TRANSFORMATION PLAN</p><h2>How this output was built</h2></div><span className="mono-caption"><GitBranch size={14} /> {plan.claim_quota || 5} claims selected</span></div><div className="plan-grid"><div><span className="field-label">STRUCTURE</span><p>{plan.structure}</p></div><div><span className="field-label">AUDIENCE RULE</span><p>{plan.audience_rule}</p></div><div><span className="field-label">TARGET LENGTH</span><p>{plan.target_length}</p></div></div><div className="plan-steps">{(plan.steps || []).map((step: any) => <div className="plan-step" key={step.step}><span>{step.step}</span><p>{step.action}</p></div>)}</div></div> }
function SourceValidation({ validation }: any) {
  if (!validation) return null
  return <div className="validation-panel">
    <div className="section-heading"><div><p className="eyebrow">SOURCE-BASED VALIDATION</p><h2>Nothing important lost</h2></div><span className="mono-caption"><ShieldCheck size={14} /> {validation.references?.length || 0} references</span></div>
    <div className="validation-checks">{(validation.checks || []).map((check: any, i: number) => <div className={`validation-check check-${check.level}`} key={i}>{check.level === 'pass' ? <CheckCircle2 size={14} /> : check.level === 'error' ? <AlertTriangle size={14} /> : <Info size={14} />}{check.message}</div>)}</div>
    <div className="validation-grid">
      <div><span className="field-label">NUMBERS PRESERVED ({validation.preserved_numbers?.length || 0})</span><div className="chip-row">{(validation.preserved_numbers || []).map((n: string, i: number) => <span className="chip chip-num ok" key={i}>{n}</span>)}</div>
        {validation.missing_numbers?.length > 0 && <><span className="field-label" style={{ marginTop: 10, display: 'block' }}>NUMBERS NOT USED ({validation.missing_numbers.length})</span><div className="chip-row">{validation.missing_numbers.map((n: string, i: number) => <span className="chip chip-missing" key={i}>{n}</span>)}</div></>}</div>
      <div><span className="field-label">CITED SOURCE LOCATIONS</span><div className="chip-row">{(validation.references || []).map((r: string, i: number) => <span className="chip" key={i}>{r}</span>)}{!validation.references?.length && <span className="struct-empty">No explicit locations</span>}</div>
        {validation.missing_concepts?.length > 0 && <><span className="field-label" style={{ marginTop: 10, display: 'block' }}>CONCEPTS NOT COVERED</span><div className="chip-row">{validation.missing_concepts.map((c: string, i: number) => <span className="chip" key={i}>{c}</span>)}</div></>}</div>
    </div>
  </div>
}

function ScorePanel({ current }: any) { const scores = current?.quality_scores; const audit = current?.audit; if (!scores) return null; return <div className="score-panel"><div className="score-overall"><span className="output-label">AI CONTENT AUDITOR · TRANSFORMATION SCORE</span><strong>{Math.round(scores.overall_score)}<small>/100</small></strong><span className="score-flag"><ShieldCheck size={14} /> {scores.unsupported_claims ? `${scores.unsupported_claims} unsupported` : 'source grounded'}</span></div><div className="score-bars"><ScoreBar label="Source coverage" value={scores.source_coverage} /><ScoreBar label="Factual consistency" value={scores.factual_consistency} /><ScoreBar label="Audience relevance" value={scores.audience_relevance} /><ScoreBar label="Readability" value={scores.readability} />{scores.format_compliance !== undefined && <ScoreBar label="Format compliance" value={scores.format_compliance} />}{audit && <><ScoreBar label="Tone match" value={audit.tone_match} /><ScoreBar label="Originality" value={audit.originality} /></>}</div></div> }
function ScoreBar({ label, value }: any) { return <div className="score-bar"><div><span>{label}</span><b>{Math.round(value)}%</b></div><span><i style={{ width: `${value}%` }} /></span></div> }

function Storyboard({ storyboard }: any) { if (!storyboard?.length) return null; return <div className="storyboard-section"><div className="section-heading"><div><p className="eyebrow">VIDEO OUTPUT</p><h2>AI video storyboard</h2></div><span className="mono-caption">{storyboard.length} scenes · captions included</span></div><div className="storyboard-grid">{storyboard.map((scene: any) => <div className="scene-card" key={scene.scene}><div className="scene-top"><strong>SCENE {String(scene.scene).padStart(2, '0')}</strong><span>{scene.duration}</span></div><div className="scene-visual"><Terminal size={16} /><span>{scene.visual}</span></div><div><span className="field-label">NARRATION</span><p>{scene.narration}</p></div><div><span className="field-label">ON-SCREEN TEXT</span><strong className="screen-text">{scene.on_screen_text}</strong></div></div>)}</div></div> }

function Verification({ current, selectedClaim, setSelectedClaim }: any) { const verifications = current?.verifications || []; return <div className="verification-panel"><div className="section-heading"><div><p className="eyebrow">CLAIM-LEVEL CHECK</p><h2>Verification ledger</h2></div><div className="verification-counts"><span className="verified"><CheckCircle2 size={14} /> {verifications.filter((v: any) => v.verification_status === 'verified').length} verified</span><span className="partial"><Info size={14} /> {verifications.filter((v: any) => v.verification_status === 'partially_supported').length} partial</span><span className="unsupported"><AlertTriangle size={14} /> {verifications.filter((v: any) => v.verification_status === 'unsupported').length} unsupported</span></div></div><div className="verification-list">{verifications.map((item: any, index: number) => <button className={`verification-row verification-${item.verification_status} ${selectedClaim?.claim_text === item.claim_text ? 'selected' : ''}`} key={`${item.claim_text}-${index}`} onClick={() => setSelectedClaim(item)}><span className="verification-icon">{item.verification_status === 'verified' ? <Check size={14} /> : item.verification_status === 'partially_supported' ? <Info size={14} /> : <AlertTriangle size={14} />}</span><span className="verification-text"><strong>{item.claim_text || item.generated_statement}</strong><small>{item.source_location || 'No source location available'} {item.confidence ? `· ${Math.round(item.confidence * 100)}% confidence` : ''}</small></span><ChevronRight size={15} /></button>)}</div></div> }

function SourceCompare({ source, currentContent, selectedClaim, setSelectedClaim, claims }: any) { if (!source || !currentContent) return null; const text = source.raw_text || ''; const match = selectedClaim?.source_text || selectedClaim?.supporting_source_text; const highlight = (value: string) => { if (!match || !value.toLowerCase().includes(match.toLowerCase().slice(0, 80))) return <span>{value}</span>; const index = value.toLowerCase().indexOf(match.toLowerCase().slice(0, 80)); return <span>{value.slice(0, index)}<mark>{value.slice(index, Math.min(value.length, index + match.length))}</mark>{value.slice(index + match.length)}</span> }; return <div className="compare-panel"><div className="section-heading"><div><p className="eyebrow">INTERACTIVE SOURCE VERIFICATION</p><h2>Show me where it came from.</h2></div><span className="mono-caption"><Link2 size={14} /> click a verified statement</span></div><div className="compare-grid"><div className="compare-source"><div className="compare-head"><span>ORIGINAL SOURCE</span><span>{source.filename}</span></div><div className="source-scroll">{text.split('\n\n').slice(0, 12).map((paragraph: string, index: number) => <p key={index} className={match && paragraph.toLowerCase().includes(match.toLowerCase().slice(0, 50)) ? 'highlighted-source' : ''}>{highlight(paragraph)}</p>)}</div></div><div className="compare-output"><div className="compare-head"><span>GENERATED CONTENT</span><span>click to trace</span></div><div className="output-scroll">{currentContent.split(/(?<=[.!?])\s+/).map((sentence: string, index: number) => { const linked = claims.find((claim: any) => sentence.toLowerCase().includes(claim.claim_text.split(' ').slice(0, 3).join(' ').toLowerCase())); return <button className={selectedClaim?.claim_text === linked?.claim_text ? 'linked active' : linked ? 'linked' : ''} key={index} onClick={() => linked && setSelectedClaim(linked)}>{sentence}</button> })}</div></div></div></div> }

function Assistant({ input, setInput, onSend, log, busy }: any) { return <div className="assistant-panel"><div className="assistant-head"><div className="assistant-mark"><MessageSquare size={16} /></div><div><strong>Transform Assistant</strong><span>Edits the current output · source attached</span></div><span className="assistant-live"><span className="live-dot" /> ready</span></div><div className="assistant-log">{!log.length && <div className="assistant-empty">Ask for a stronger hook, a simpler explanation, or a different audience. I will modify the current output, not start over.</div>}{log.map((message: any, index: number) => <div className={`assistant-message ${message.role}`} key={index}>{message.text}</div>)}</div><div className="assistant-input"><input value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => event.key === 'Enter' && onSend()} placeholder="Make this simpler..." /><button onClick={() => onSend()} disabled={busy || !input.trim()}>{busy ? <Loader2 className="spin" size={15} /> : <Send size={15} />}</button></div><div className="assistant-suggestions">{['Create a stronger hook', 'Remove technical jargon', 'Make this suitable for LinkedIn', 'Create a 30-second version', 'Turn this into a presentation', 'Explain this claim'].map(item => <button onClick={() => onSend(item)} key={item} disabled={busy}>{item}</button>)}</div></div> }

function HistoryView({ history, onRefresh }: any) { return <section className="history-view"><PageTitle eyebrow="TRANSFORMATION HISTORY" title="A record of what the source became." copy="Every generation is stored with its audience, format, and source relationship." /><div className="history-toolbar"><span>{history.length} transformations recorded</span><button className="button button-ghost" onClick={onRefresh}><RotateCcw size={15} /> Refresh</button></div><div className="history-table"><div className="history-head"><span>Output</span><span>Audience</span><span>Tone</span><span>Status</span><span>Created</span></div>{history.length ? history.map((item: any) => <div className="history-row" key={item.id}><div><strong>{item.output_format}</strong><small>Transformation #{item.id}</small></div><span>{item.target_audience}</span><span>{item.tone}</span><b className="status-pill status-live"><span className="live-dot" /> {item.status}</b><span className="mono-caption">{new Date(item.created_at).toLocaleDateString()}</span></div>) : <div className="history-empty"><Clock3 size={25} /><span>No transformations yet. The ledger is waiting for its first output.</span></div>}</div></section> }

function AnalyticsView({ analytics }: any) { if (!analytics) return <section className="analytics-view"><PageTitle eyebrow="ANALYTICS" title="Measure useful transformation." copy="The dashboard updates as outputs, claims, and quality scores accumulate." /><div className="loading-state"><Loader2 className="spin" size={24} /> Loading analytics...</div></section>; const formats = analytics.most_used_formats || []; return <section className="analytics-view"><PageTitle eyebrow="CONTENT TRANSFORMATION ANALYTICS" title="The signal behind the output." copy="Understand which formats travel furthest, which audiences recur, and how much source truth stays intact." /><div className="analytics-kpis"><Kpi label="Total transformations" value={analytics.total_transformations} icon={Wand2} /><Kpi label="Average quality" value={`${analytics.average_quality}%`} icon={Gauge} /><Kpi label="Verified claims" value={analytics.verified_claims} icon={ShieldCheck} /><Kpi label="Time saved estimate" value={analytics.time_saved_estimate} icon={Clock3} /></div><div className="analytics-grid"><div className="chart-panel"><div className="section-heading"><div><p className="eyebrow">FORMAT MIX</p><h2>Most used formats</h2></div></div>{formats.length ? <div className="bar-chart">{formats.map((item: any, index: number) => <div className="bar-row" key={item.format}><span>{item.format}</span><div><i style={{ width: `${Math.max(8, item.count / formats[0].count * 100)}%`, background: index % 2 ? '#3155d8' : '#b8db55' }} /></div><b>{item.count}</b></div>)}</div> : <div className="quiet-note">No output mix yet.</div>}</div><div className="chart-panel"><div className="section-heading"><div><p className="eyebrow">AUDIENCE SIGNAL</p><h2>Where the source travels</h2></div></div>{(analytics.most_used_audiences || []).length ? <div className="audience-list">{analytics.most_used_audiences.map((item: any, index: number) => <div key={item.audience}><span className="audience-index">0{index + 1}</span><strong>{item.audience}</strong><b>{item.count}</b></div>)}</div> : <div className="quiet-note">Audience patterns appear after your first transformation.</div>}</div></div></section> }
function Kpi({ label, value, icon: Icon }: any) { return <div className="kpi"><Icon size={17} /><strong>{value}</strong><span>{label}</span></div> }
function SettingsView() { return <section className="settings-view"><PageTitle eyebrow="WORKSPACE SETTINGS" title="Control the reasoning layer." copy="Prototype settings are explicit so the demo never pretends an external model is available when it is not." /><div className="settings-grid"><div className="settings-panel"><div className="setting-row"><div><strong>Provider mode</strong><span>Fallback provider with deterministic demo data</span></div><b className="status-pill status-live"><span className="live-dot" /> demo active</b></div><div className="setting-row"><div><strong>API key</strong><span>Read from backend/.env only. Never shipped to the browser.</span></div><b className="mono-caption">server-side</b></div><div className="setting-row"><div><strong>Maximum upload</strong><span>PDF, DOCX, TXT, Markdown, URL</span></div><b className="mono-caption">10 MB</b></div></div><div className="settings-panel architecture-panel"><div className="aside-heading"><GitBranch size={17} /><strong>Service boundaries</strong></div>{['content_ingestion', 'content_analyzer', 'claim_extractor', 'knowledge_mapper', 'transformation_engine', 'fact_checker', 'quality_scorer'].map(item => <div key={item}><Terminal size={13} />{item}<Check size={13} /></div>)}</div></div></section> }
function PageTitle({ eyebrow, title, copy }: any) { return <div className="page-title"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{copy}</p></div> }
function EmptyState({ title, copy, action, onClick }: any) { return <div className="empty-state"><div className="empty-icon"><Database size={25} /></div><h2>{title}</h2><p>{copy}</p><button className="button button-cobalt" onClick={onClick}>{action} <ArrowRight size={15} /></button></div> }
function DnaIcon({ size = 18 }: { size?: number }) { return <span className="dna-icon" style={{ width: size, height: size }}><i /><i /></span> }

export default App
