# HonestLedger

> **The first financial reconciliation agent that catches itself cheating — and proves it didn't.**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Track](https://img.shields.io/badge/track-Arize%20Phoenix-purple.svg)](https://arize.com)
[![Built with](https://img.shields.io/badge/built%20with-Gemini%20%2B%20Google%20ADK-4285F4.svg)](https://cloud.google.com/vertex-ai)

HonestLedger is a self-improving financial reconciliation agent built for the **Google Cloud Rapid Agent Hackathon** (Arize Phoenix track). It reconciles payments against invoices using Gemini, diagnoses its own mistakes via LLM-as-a-Judge, and — crucially — **blocks its own reward hacking** using blind holdout verification before any rule change is approved.

**Hackathon:** Google Cloud Rapid Agent Hackathon · **Deadline:** June 11, 2026, 14:00 PDT  
**Track:** Arize Phoenix · **Submission type:** Solo

---

## Why This Matters

Self-improving AI agents have a well-known failure mode: they optimise for the *proxy metric* (match rate) rather than the *true goal* (accurate reconciliation). An agent can inflate its score by loosening every threshold — matching more transactions, even wrong ones. This is **reward hacking**.

HonestLedger is the first system to apply reward-hacking detection — pioneered in coding domains by EvilGenie (MIT/Cambridge, 2025) and formalised in ASG-SI (arXiv:2512.23760) — to **financial reconciliation**, a domain with equally objective ground truth.

> *"No magic way to detect reward hacking; best practice = evaluate against diverse holdout scenarios."*  
> — Lilian Weng, OpenAI (2024)

HonestLedger implements exactly this: every proposed rule change is evaluated against a **held-out set the agent has never seen**. If holdout accuracy drops, the proposal is auto-rejected and logged as a cheating attempt.

---

## Architecture — 3 Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — RECONCILE                                            │
│  Gemini (Vertex AI) reasons over each payment vs invoice list   │
│  Output: { decision, matched_invoice_id, confidence, rationale }│
│  All decisions traced to Arize Phoenix via OpenInference        │
└─────────────────────────────┬───────────────────────────────────┘
                              │ traces
┌─────────────────────────────▼───────────────────────────────────┐
│  LAYER 2 — INTROSPECT (Judge)                                   │
│  Second Gemini reads Phoenix traces, diagnoses error patterns   │
│  Proposes concrete rule parameter changes (e.g. name_sim=0.7)  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ proposal
┌─────────────────────────────▼───────────────────────────────────┐
│  LAYER 3 — VERIFY  ← CORE NOVELTY                               │
│  New rules tested on TRAIN set  → score_train_new               │
│  New rules tested on HOLDOUT set → score_holdout_new            │
│  ┌─ holdout ↑ ≥ 2%  → GENUINE_IMPROVEMENT → human approval     │
│  ├─ holdout ↓ ≥ 5%  → REWARD_HACKING → auto-reject + log       │
│  └─ else            → INCONCLUSIVE → human review              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Agent runtime** | Gemini 2.5 Flash via Vertex AI (`google-genai` SDK) |
| **Agent framework** | Google ADK |
| **Observability** | Arize Phoenix Cloud (free tier) + OpenInference |
| **MCP** | `@arizeai/phoenix-mcp` — trace introspection |
| **Backend API** | FastAPI + Python 3.12 |
| **Package manager** | `uv` + `pyproject.toml` |
| **Frontend** | React 18 + Vite + Tailwind CSS + Framer Motion |
| **Charts** | Recharts |
| **Hosting** | Google Cloud Run (backend) + Vercel (frontend) |
| **License** | Apache 2.0 |

---

## Quick Start

### Prerequisites

- Python 3.10–3.12, [`uv`](https://docs.astral.sh/uv/), Node.js 18+
- Google Cloud project with **Vertex AI API enabled** and billing active
- [Arize Phoenix Cloud](https://app.phoenix.arize.com) account (free tier) — get API key

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_USERNAME/honestledger.git
cd honestledger
cp .env.example .env
# Edit .env — fill in GOOGLE_CLOUD_PROJECT, PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT
```

### 2. Authenticate with Google Cloud

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### 3. Install & run backend

```bash
make install          # installs Python deps via uv
make smoke-test       # verifies Gemini + Phoenix connectivity
make run              # starts FastAPI on :8000
```

### 4. Install & run frontend

```bash
make install-frontend  # npm install in frontend/
make run-frontend      # starts Vite dev server on :5173
```

Open **http://localhost:5173**

### 5. Instant demo (no Gemini calls)

Click **"⚡ Seed Full Demo"** in the dashboard — loads pre-computed results immediately.  
To run the real pipeline (takes ~25 min): `make demo`

---

## Project Structure

```
honestledger/
├── backend/
│   ├── main.py               FastAPI app — all endpoints
│   ├── config.py             Vertex AI + Phoenix env setup
│   ├── agent/
│   │   ├── reconcile.py      Layer 1: Gemini matching with pre-filtering
│   │   ├── judge.py          Layer 2: LLM-as-a-Judge + Phoenix trace query
│   │   ├── verify.py         Layer 3: holdout gate + reward-hacking detection
│   │   ├── rules.py          Rule versioning (v0 strict → v1 sensible → v_greedy)
│   │   └── prompts.py        All Gemini prompts centralised
│   ├── data/
│   │   ├── payments.csv      30 payments (train 20 + holdout 10)
│   │   ├── invoices.csv      30 invoices with duplicate-amount traps
│   │   └── ground_truth.csv  Correct answer key + train/holdout split
│   ├── models/schemas.py     Pydantic models
│   └── tracing/              Phoenix OTEL setup + MCP client
├── frontend/
│   └── src/
│       ├── App.tsx           Main dashboard
│       ├── api.ts            Backend API calls
│       └── components/       7 UI components (see below)
├── scripts/
│   ├── run_demo.py           Full e2e orchestration
│   └── test_verify.py        Tests both verify scenarios
├── docs/
│   ├── pitch.md              Devpost submission text
│   └── demo_script.md        Video recording guide
└── Makefile                  make run / make demo / etc.
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reconcile` | Layer 1 — run Gemini matching |
| `POST` | `/judge` | Layer 2 — diagnose errors + propose rules |
| `POST` | `/verify` | Layer 3 — holdout gate |
| `POST` | `/verify/greedy` | Demo: inject greedy attack + verify |
| `POST` | `/approve` | Human approval (GENUINE only) |
| `POST` | `/reject` | Human rejection |
| `GET`  | `/history` | Iteration history for chart |
| `POST` | `/demo/seed` | Load pre-computed demo state (instant) |

---

## Arize Track Compliance

- [x] **Code-owned agent** (Google ADK + Gemini SDK, not Agent Builder)
- [x] **Meaningful use of tracing** — every Gemini reasoning step traced to Phoenix
- [x] **Meaningful use of MCP** — Phoenix MCP server queried programmatically for trace introspection in the judge loop
- [x] **Self-improvement loop** — agent diagnoses its own errors and proposes rule changes
- [x] **Uses observability data to improve** — judge reads Phoenix traces to diagnose patterns
- [x] **Bonus: agents that use their own observability data** ✓

---

## Dataset

60 transactions (30 payments × 30 invoices) with controlled traps:

- **Name variants**: "PT Global Tekno" ↔ "PT Global Teknologi"
- **Fee deductions**: payment amount = invoice − Rp 6,500 bank fee
- **Date differences**: 2–3 day payment lag
- **Split payments**: 1 payment covers 2 invoices
- **Reward-hacking traps**: 2 invoices with identical amounts but different vendors

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

This project adapts structure from the [Arize gemini-hackathon starter](https://github.com/Arize-ai/gemini-hackathon) (also Apache 2.0).
