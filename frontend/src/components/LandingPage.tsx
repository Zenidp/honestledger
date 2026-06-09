import { useState, useEffect, useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import {
  ShieldCheck, Zap, GitBranch, BarChart3, ArrowRight,
  CheckCircle, XCircle, AlertTriangle, ChevronRight,
  Github, ExternalLink, Lock, Upload, Brain, Eye,
  TrendingUp, FileCheck, Users, Globe, Star, Menu, X,
  Cpu, Database, Activity,
} from 'lucide-react'
import { setApiKey } from '../api'

// ── Animated counter ───────────────────────────────────────────────────────────

function Counter({ target, suffix = '', duration = 1800 }: { target: number; suffix?: string; duration?: number }) {
  const [val, setVal] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })
  useEffect(() => {
    if (!inView) return
    const start = performance.now()
    const raf = (now: number) => {
      const t = Math.min((now - start) / duration, 1)
      const ease = 1 - Math.pow(1 - t, 3)
      setVal(Math.round(ease * target))
      if (t < 1) requestAnimationFrame(raf)
    }
    requestAnimationFrame(raf)
  }, [inView, target, duration])
  return <span ref={ref}>{val.toLocaleString()}{suffix}</span>
}

// ── Login Modal ────────────────────────────────────────────────────────────────

function LoginModal({ onClose, onAuthenticated }: { onClose: () => void; onAuthenticated: () => void }) {
  const [key, setKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!key.startsWith('hl_')) { setError('API key must start with hl_'); return }
    setLoading(true); setError(null)
    try {
      setApiKey(key.trim())
      const res = await fetch('/api/status', { headers: { 'X-API-Key': key.trim() } })
      if (res.status === 401) { setError('Invalid or inactive API key.'); localStorage.removeItem('hl_api_key') }
      else { onAuthenticated() }
    } catch { setError('Connection error. Please try again.') }
    finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-teal-50 rounded-xl"><ShieldCheck className="w-6 h-6 text-teal-600" /></div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">HonestLedger</h1>
            <p className="text-sm text-gray-500">Enter your API key to continue</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="password" value={key} onChange={e => setKey(e.target.value)}
                placeholder="hl_••••••••••••••••••••••••••••••••"
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono"
                autoFocus />
            </div>
          </div>
          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
          <button type="submit" disabled={!key || loading}
            className="w-full py-2.5 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-200 disabled:text-gray-400 text-white font-medium rounded-lg text-sm transition-colors">
            {loading ? 'Validating…' : 'Access Dashboard'}
          </button>
        </form>
        <p className="text-xs text-gray-400 mt-4 text-center">Keys are stored locally and never shared.</p>
      </motion.div>
    </div>
  )
}

// ── Nav ────────────────────────────────────────────────────────────────────────

function Nav({ onLogin }: { onLogin: () => void }) {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', fn)
    return () => window.removeEventListener('scroll', fn)
  }, [])
  const links = ['Features', 'How it Works', 'Technical', 'Metrics']
  return (
    <nav className={`fixed top-0 left-0 right-0 z-40 transition-all duration-300 ${scrolled ? 'bg-white/95 backdrop-blur-md shadow-sm' : 'bg-transparent'}`}>
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="#" className="flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-teal-600" />
          <span className="font-bold text-gray-900 text-lg">HonestLedger</span>
        </a>
        <div className="hidden md:flex items-center gap-6">
          {links.map(l => (
            <a key={l} href={`#${l.toLowerCase().replace(/ /g,'-')}`}
              className="text-sm text-gray-600 hover:text-teal-600 transition-colors">{l}</a>
          ))}
        </div>
        <div className="hidden md:flex items-center gap-3">
          <a href="https://github.com/Zenidp/honestledger" target="_blank" rel="noreferrer"
            className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 transition-colors">
            <Github className="w-4 h-4" /> GitHub
          </a>
          <button onClick={onLogin}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors">
            Sign In
          </button>
        </div>
        <button className="md:hidden p-2" onClick={() => setMenuOpen(o => !o)}>
          {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>
      {menuOpen && (
        <div className="md:hidden bg-white border-t border-gray-100 px-6 py-4 space-y-3">
          {links.map(l => <a key={l} href={`#${l.toLowerCase().replace(/ /g,'-')}`} className="block text-sm text-gray-700">{l}</a>)}
          <button onClick={onLogin} className="w-full py-2 bg-teal-600 text-white text-sm font-medium rounded-lg">Sign In</button>
        </div>
      )}
    </nav>
  )
}

// ── Hero ───────────────────────────────────────────────────────────────────────

function Hero({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-teal-950 pt-20">
      {/* Grid background */}
      <div className="absolute inset-0 opacity-10"
        style={{ backgroundImage: 'linear-gradient(rgba(20,184,166,.3) 1px,transparent 1px),linear-gradient(90deg,rgba(20,184,166,.3) 1px,transparent 1px)', backgroundSize: '40px 40px' }} />
      {/* Glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-teal-500/10 rounded-full blur-3xl" />

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        {/* Badge */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 bg-teal-500/10 border border-teal-500/30 text-teal-400 text-xs font-medium px-4 py-2 rounded-full mb-8">
          <Star className="w-3.5 h-3.5" /> Google Cloud Hackathon · Arize Phoenix Track
        </motion.div>

        {/* Headline */}
        <motion.h1 initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight tracking-tight">
          The reconciliation agent<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-cyan-400">that keeps itself honest.</span>
        </motion.h1>

        {/* Sub */}
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
          className="text-lg md:text-xl text-slate-400 max-w-3xl mx-auto mb-10 leading-relaxed">
          AI-powered financial reconciliation that self-improves, detects its own reward hacking,
          and proves every rule change is genuine — not just inflated metrics.
        </motion.p>

        {/* CTAs */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <button onClick={onGetStarted}
            className="flex items-center gap-2 px-8 py-3.5 bg-teal-500 hover:bg-teal-400 text-white font-semibold rounded-xl transition-all shadow-lg shadow-teal-500/25 hover:shadow-teal-500/40">
            Start Reconciling <ArrowRight className="w-4 h-4" />
          </button>
          <a href="https://github.com/Zenidp/honestledger" target="_blank" rel="noreferrer"
            className="flex items-center gap-2 px-8 py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-medium rounded-xl transition-all">
            <Github className="w-4 h-4" /> View on GitHub
          </a>
        </motion.div>

        {/* Stats strip */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.65 }}
          className="grid grid-cols-3 gap-4 max-w-2xl mx-auto">
          {[
            { value: 100, suffix: '%', label: 'Accuracy on complex dataset' },
            { value: 30,  suffix: 's', label: 'Average reconcile time' },
            { value: 9,   suffix: '',  label: 'Challenge categories handled' },
          ].map(s => (
            <div key={s.label} className="bg-white/5 border border-white/10 rounded-xl py-4 px-3">
              <div className="text-2xl font-bold text-teal-400">
                <Counter target={s.value} suffix={s.suffix} />
              </div>
              <div className="text-xs text-slate-400 mt-1">{s.label}</div>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Scroll cue */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-slate-500 animate-bounce">
        <ChevronRight className="w-5 h-5 rotate-90" />
      </div>
    </section>
  )
}

// ── Logo / Social Proof bar ────────────────────────────────────────────────────

function LogoBar() {
  const items = ['Google Cloud', 'Arize Phoenix', 'Vertex AI', 'FastAPI', 'React', 'PostgreSQL']
  return (
    <section className="bg-slate-950 border-y border-slate-800 py-6">
      <div className="max-w-5xl mx-auto px-6">
        <p className="text-xs text-slate-500 text-center mb-4 uppercase tracking-widest">Built with</p>
        <div className="flex flex-wrap justify-center gap-x-10 gap-y-3">
          {items.map(i => (
            <span key={i} className="text-sm font-medium text-slate-400">{i}</span>
          ))}
        </div>
      </div>
    </section>
  )
}

// ── Problem / Solution ─────────────────────────────────────────────────────────

function ProblemSolution() {
  return (
    <section id="features" className="py-24 bg-white">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">The Problem</span>
          <h2 className="text-4xl font-bold text-gray-900 mt-3 mb-4">Finance teams are drowning in manual reconciliation</h2>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">
            Every month, thousands of hours are spent matching payments to invoices — manually, error-prone, with no audit trail.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 mb-16">
          {/* Before */}
          <div className="bg-red-50 border border-red-100 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <XCircle className="w-5 h-5 text-red-500" />
              <h3 className="font-semibold text-gray-900">Without HonestLedger</h3>
            </div>
            <ul className="space-y-3 text-sm text-gray-600">
              {[
                'Analysts spend 8+ hours/month on manual matching',
                'Typos, abbreviations cause missed matches',
                'No audit trail — who approved what?',
                'AI tools that improve metrics by cheating',
                'One CSV export. No explanations.',
              ].map(t => (
                <li key={t} className="flex items-start gap-2">
                  <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                  {t}
                </li>
              ))}
            </ul>
          </div>
          {/* After */}
          <div className="bg-teal-50 border border-teal-100 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="w-5 h-5 text-teal-500" />
              <h3 className="font-semibold text-gray-900">With HonestLedger</h3>
            </div>
            <ul className="space-y-3 text-sm text-gray-600">
              {[
                'Upload CSVs — done in under 30 seconds',
                'Handles typos, abbreviations, split payments, all-caps',
                'Every decision explained, every approval logged',
                'Reward hacking auto-detected and rejected',
                'PDF audit report + ERP-ready CSV export',
              ].map(t => (
                <li key={t} className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-teal-500 mt-0.5 shrink-0" />
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Value Pillars ──────────────────────────────────────────────────────────────

const PILLARS = [
  {
    icon: Brain,
    color: 'teal',
    title: 'AI-Powered Matching',
    desc: 'Handles real-world messiness — vendor typos, name abbreviations, EN/ID language mix, all-caps, bank fee deductions, and split payments across multiple invoices.',
  },
  {
    icon: TrendingUp,
    color: 'blue',
    title: 'Self-Improving Engine',
    desc: 'LLM-as-a-Judge reads reconciliation traces via Arize Phoenix, diagnoses failure patterns, and proposes parameter improvements — automatically.',
  },
  {
    icon: ShieldCheck,
    color: 'violet',
    title: 'Reward Hacking Detection',
    desc: 'The first reconciliation system to catch its own cheating. If a rule change inflates train accuracy but hurts holdout performance, it\'s auto-rejected with a full explanation.',
  },
  {
    icon: FileCheck,
    color: 'amber',
    title: 'Complete Audit Trail',
    desc: 'Every match decision, rule iteration, and approval is logged with timestamps. Export as PDF audit report or accounting CSV for your ERP system.',
  },
]

function Features() {
  const colors: Record<string, string> = {
    teal:   'bg-teal-50   border-teal-100   text-teal-600',
    blue:   'bg-blue-50   border-blue-100   text-blue-600',
    violet: 'bg-violet-50 border-violet-100 text-violet-600',
    amber:  'bg-amber-50  border-amber-100  text-amber-600',
  }
  return (
    <section className="py-24 bg-gray-50">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">Value Pillars</span>
          <h2 className="text-4xl font-bold text-gray-900 mt-3">Built different, by design</h2>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          {PILLARS.map(p => {
            const Icon = p.icon
            return (
              <motion.div key={p.title}
                initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
                className="bg-white border border-gray-100 rounded-2xl p-6 hover:shadow-md transition-shadow">
                <div className={`inline-flex p-2.5 rounded-xl border mb-4 ${colors[p.color]}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{p.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{p.desc}</p>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

// ── How It Works ───────────────────────────────────────────────────────────────

const STEPS = [
  { icon: Upload,     step: '01', title: 'Upload your CSVs',         desc: 'Drop your payments and invoices files. The system auto-detects column names from any accounting software format.' },
  { icon: Brain,      step: '02', title: 'AI reconciles & judges',   desc: 'Gemini matches payments to invoices with full reasoning. A second LLM reads the trace via Arize Phoenix and proposes rule improvements.' },
  { icon: ShieldCheck,step: '03', title: 'Verify against holdout',   desc: 'Every proposed rule is tested on data the AI has never seen. Only genuine improvements pass. Cheating attempts are auto-rejected.' },
  { icon: FileCheck,  step: '04', title: 'Review, approve & export', desc: 'Approve with one click. Download a PDF audit report or an ERP-ready CSV. Every decision is permanently logged.' },
]

function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 bg-white">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">How it Works</span>
          <h2 className="text-4xl font-bold text-gray-900 mt-3">From upload to audit-ready in four steps</h2>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {STEPS.map((s, i) => {
            const Icon = s.icon
            return (
              <motion.div key={s.step}
                initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                className="relative">
                {i < STEPS.length - 1 && (
                  <div className="hidden lg:block absolute top-6 left-full w-full h-px bg-gray-200 z-0" style={{ width: 'calc(100% - 3rem)', left: 'calc(50% + 1.5rem)' }} />
                )}
                <div className="relative z-10 bg-gray-50 rounded-2xl p-5 h-full">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-8 h-8 bg-teal-600 rounded-lg flex items-center justify-center shrink-0">
                      <Icon className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-xs font-bold text-teal-600 font-mono">STEP {s.step}</span>
                  </div>
                  <h3 className="font-semibold text-gray-900 text-sm mb-2">{s.title}</h3>
                  <p className="text-xs text-gray-500 leading-relaxed">{s.desc}</p>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

// ── Technical Showcase ─────────────────────────────────────────────────────────

function TechShowcase() {
  return (
    <section id="technical" className="py-24 bg-slate-950">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-400">Architecture</span>
          <h2 className="text-4xl font-bold text-white mt-3">Three layers. One honest agent.</h2>
          <p className="text-slate-400 mt-4 max-w-2xl mx-auto">
            A production-grade pipeline combining Google Gemini, Arize Phoenix observability, and a train/holdout verification gate.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-4 mb-12">
          {[
            { icon: Cpu,      label: 'LAYER 1', title: 'Reconcile',  color: 'teal',   desc: 'Gemini reasons over each payment-invoice pair. Full rationale per decision. Handles name variants, fee deductions, split payments.' },
            { icon: Eye,      label: 'LAYER 2', title: 'Judge',      color: 'blue',   desc: 'A second Gemini instance reads execution traces via Arize Phoenix MCP. Diagnoses error patterns. Proposes targeted rule improvements.' },
            { icon: ShieldCheck, label: 'LAYER 3', title: 'Verify', color: 'violet', desc: 'Proposed rules are tested against a held-out set. Train accuracy up + holdout accuracy up = GENUINE. Holdout drops = REWARD HACKING DETECTED.' },
          ].map((l, i) => {
            const Icon = l.icon
            const colors: Record<string, string> = {
              teal: 'border-teal-800 bg-teal-900/20 text-teal-400',
              blue: 'border-blue-800 bg-blue-900/20 text-blue-400',
              violet: 'border-violet-800 bg-violet-900/20 text-violet-400',
            }
            return (
              <motion.div key={l.title}
                initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.15 }}
                className={`border rounded-2xl p-5 ${colors[l.color]}`}>
                <div className="flex items-center gap-2 mb-3">
                  <Icon className="w-4 h-4" />
                  <span className="text-xs font-bold font-mono">{l.label}</span>
                </div>
                <h3 className="text-lg font-bold text-white mb-2">{l.title}</h3>
                <p className="text-xs leading-relaxed opacity-80">{l.desc}</p>
              </motion.div>
            )
          })}
        </div>

        {/* Stack */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <p className="text-xs text-slate-500 uppercase tracking-widest mb-4">Tech Stack</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: Brain,    label: 'Gemini 2.5 Flash',  sub: 'LLM Brain (Vertex AI)' },
              { icon: Activity, label: 'Arize Phoenix',     sub: 'Observability + MCP' },
              { icon: Database, label: 'Supabase',          sub: 'PostgreSQL + Multi-tenant' },
              { icon: Globe,    label: 'Cloud Run',         sub: 'Serverless Deploy' },
            ].map(s => {
              const Icon = s.icon
              return (
                <div key={s.label} className="flex items-center gap-3 bg-slate-800/50 rounded-xl p-3">
                  <Icon className="w-4 h-4 text-teal-400 shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-white">{s.label}</p>
                    <p className="text-xs text-slate-500">{s.sub}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Metrics ────────────────────────────────────────────────────────────────────

function Metrics() {
  return (
    <section id="metrics" className="py-24 bg-white">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="text-xs font-semibold uppercase tracking-widest text-teal-600">Performance</span>
          <h2 className="text-4xl font-bold text-gray-900 mt-3">Numbers that matter</h2>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Accuracy progression */}
          <div className="bg-gray-50 rounded-2xl p-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-teal-600" /> Accuracy Progression — Complex Dataset
            </h3>
            <div className="space-y-3">
              {[
                { version: 'v0 (baseline)', pct: 43, color: 'bg-red-400' },
                { version: 'v1 (after Judge)', pct: 72, color: 'bg-amber-400' },
                { version: 'v2 (optimal)', pct: 100, color: 'bg-teal-500' },
              ].map(r => (
                <div key={r.version}>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>{r.version}</span><span className="font-semibold text-gray-900">{r.pct}%</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <motion.div className={`h-full rounded-full ${r.color}`}
                      initial={{ width: 0 }} whileInView={{ width: `${r.pct}%` }} viewport={{ once: true }}
                      transition={{ duration: 0.8, ease: 'easeOut' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-4">
            {[
              { value: 100, suffix: '%',  label: 'Final accuracy',             sub: '30/30 correct matches' },
              { value: 9,   suffix: '',   label: 'Challenge categories',       sub: 'Typos, fees, splits & more' },
              { value: 5,   suffix: '',   label: 'Structural gaps identified', sub: 'Unmatched = correct answer' },
              { value: 2,   suffix: '',   label: 'Decoy invoices rejected',    sub: 'Same amount, wrong vendor' },
            ].map(s => (
              <div key={s.label} className="bg-gray-50 rounded-2xl p-5">
                <div className="text-3xl font-bold text-teal-600 mb-1">
                  <Counter target={s.value} suffix={s.suffix} />
                </div>
                <p className="text-sm font-medium text-gray-900">{s.label}</p>
                <p className="text-xs text-gray-400 mt-0.5">{s.sub}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Challenge badges */}
        <div className="mt-10">
          <p className="text-sm font-medium text-gray-700 mb-3">Challenges the system handles correctly:</p>
          <div className="flex flex-wrap gap-2">
            {[
              'Name typos', 'Abbreviations', 'EN/ID language mix', 'ALL-CAPS names',
              'Bank fee deductions', 'Date differences', 'Split payments',
              'Decoy invoices', 'Prefix/suffix stripped', 'Rounding differences',
            ].map(c => (
              <span key={c} className="text-xs bg-teal-50 text-teal-700 border border-teal-100 px-3 py-1 rounded-full">
                ✓ {c}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Testimonials / Quote ───────────────────────────────────────────────────────

function Quote() {
  return (
    <section className="py-20 bg-teal-600">
      <div className="max-w-3xl mx-auto px-6 text-center">
        <blockquote className="text-2xl md:text-3xl font-medium text-white leading-relaxed mb-6">
          "This is what trustworthy self-improving AI looks like in finance —
          not just smart, but <em>honest</em>."
        </blockquote>
        <div className="flex items-center justify-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
            <Users className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <p className="text-white font-medium text-sm">HonestLedger</p>
            <p className="text-teal-200 text-xs">Closing line · Demo video</p>
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Bottom CTA ─────────────────────────────────────────────────────────────────

function BottomCTA({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <section className="py-24 bg-slate-950">
      <div className="max-w-3xl mx-auto px-6 text-center">
        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <div className="inline-flex p-3 bg-teal-500/10 border border-teal-500/20 rounded-2xl mb-6">
            <ShieldCheck className="w-8 h-8 text-teal-400" />
          </div>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Ready to reconcile with confidence?
          </h2>
          <p className="text-slate-400 text-lg mb-10">
            Upload your CSVs and let the system do the heavy lifting —
            matches, mismatches, and structural gaps all explained.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button onClick={onGetStarted}
              className="flex items-center gap-2 px-8 py-4 bg-teal-500 hover:bg-teal-400 text-white font-semibold rounded-xl transition-all shadow-lg shadow-teal-500/25 text-lg">
              Get Started Free <ArrowRight className="w-5 h-5" />
            </button>
            <a href="https://github.com/Zenidp/honestledger" target="_blank" rel="noreferrer"
              className="flex items-center gap-2 px-8 py-4 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-medium rounded-xl transition-all">
              <Github className="w-5 h-5" /> Open Source on GitHub
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

// ── Footer ─────────────────────────────────────────────────────────────────────

function Footer() {
  const links = {
    Product: ['Features', 'How it Works', 'Technical Architecture', 'Metrics'],
    Resources: ['GitHub Repository', 'API Documentation', 'Demo Video', 'Devpost Submission'],
    Legal: ['Open Source (Apache-2.0)', 'Privacy Policy', 'Terms of Use'],
  }
  return (
    <footer className="bg-slate-950 border-t border-slate-800">
      <div className="max-w-5xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-4 gap-10 mb-12">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <ShieldCheck className="w-5 h-5 text-teal-500" />
              <span className="font-bold text-white">HonestLedger</span>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed mb-4">
              The reconciliation agent that keeps itself honest. Built for the Google Cloud Hackathon, Arize Track.
            </p>
            <div className="flex gap-3">
              <a href="https://github.com/Zenidp/honestledger" target="_blank" rel="noreferrer"
                className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors">
                <Github className="w-4 h-4 text-slate-300" />
              </a>
              <a href="https://honestledger-482466571967.us-central1.run.app" target="_blank" rel="noreferrer"
                className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors">
                <ExternalLink className="w-4 h-4 text-slate-300" />
              </a>
            </div>
          </div>

          {/* Links */}
          {Object.entries(links).map(([section, items]) => (
            <div key={section}>
              <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-4">{section}</h4>
              <ul className="space-y-2">
                {items.map(item => (
                  <li key={item}>
                    <a href="#" className="text-sm text-slate-500 hover:text-slate-300 transition-colors">{item}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="border-t border-slate-800 pt-8 flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-xs text-slate-500">
            © 2026 HonestLedger · Built by <span className="text-slate-400">Duha Perbangga</span> · Apache-2.0 License
          </p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-xs text-slate-500">
              <GitBranch className="w-3.5 h-3.5" /> main
            </span>
            <span className="flex items-center gap-1.5 text-xs text-teal-500">
              <Activity className="w-3.5 h-3.5" /> Live on Cloud Run
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}

// ── Main export ────────────────────────────────────────────────────────────────

export default function LandingPage({ onLogin }: { onLogin: () => void }) {
  const [showLogin, setShowLogin] = useState(false)
  const handleLogin = () => setShowLogin(true)
  const handleAuthenticated = () => { setShowLogin(false); onLogin() }

  return (
    <div className="min-h-screen bg-white text-gray-900 font-sans">
      <Nav onLogin={handleLogin} />
      <Hero onGetStarted={handleLogin} />
      <LogoBar />
      <ProblemSolution />
      <Features />
      <HowItWorks />
      <TechShowcase />
      <Metrics />
      <Quote />
      <BottomCTA onGetStarted={handleLogin} />
      <Footer />
      {showLogin && <LoginModal onClose={() => setShowLogin(false)} onAuthenticated={handleAuthenticated} />}
    </div>
  )
}
