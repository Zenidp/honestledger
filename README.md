<div align="center">

# 🏦 HonestLedger

### *AI-Powered Financial Reconciliation with Anti-Reward-Hacking Verification*

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-honestledger-4F46E5?style=for-the-badge)](https://honestledger-816125388987.us-central1.run.app)
[![Google Cloud](https://img.shields.io/badge/Google_Cloud-Vertex_AI-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)](https://cloud.google.com/vertex-ai)
[![Arize Phoenix](https://img.shields.io/badge/Arize-Phoenix_Observability-FF6B35?style=for-the-badge)](https://phoenix.arize.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)](LICENSE)

<img src="docs/honestLadger_bg.jpg" alt="HonestLedger Banner" width="100%">

---

> **Financial reconciliation** traditionally takes days and is prone to human error.
> HonestLedger automates this process with AI, then **verifies the honesty of AI itself** —
> preventing accuracy manipulation that looks good on paper but fails in the real world.

---

```
Upload Data → AI Reconcile → AI Judge → Anti-Hack Verify → Approve → Optimal Rules
     │              │              │              │               │
     ▼              ▼              ▼              ▼               ▼
  CSV/Excel      Gemini 2.5    Analyze +      Holdout Test    Rules saved
  Payments +     Flash AI      Propose        Train vs         to DB per
  Invoices       matches       Rule Fix       Holdout          Tenant
```

</div>

---

## 📋 Table of Contents

- [About the Project](#-about-the-project)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [AI Pipeline (3-Layer)](#-ai-pipeline-3-layer)
- [Anti-Reward-Hacking](#-anti-reward-hacking)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [CSV Data Format](#-csv-data-format)
- [API Reference](#-api-reference)
- [Rule Configuration](#-rule-configuration)
- [Observability with Arize Phoenix](#-observability-with-arize-phoenix)
- [Deploy to Cloud Run](#-deploy-to-cloud-run)
- [Glossary](#-glossary)

---

## 🎯 About the Project

HonestLedger was born from a single question:

> *How do we know that AI isn't simply "cheating" to achieve a high accuracy score?*

In financial reconciliation, an AI system could easily:
- Accept every transaction as "matched" to achieve 100% accuracy — which is **wrong**
- Loosen matching rules until there are almost no constraints — looks great, but is **dangerous**

HonestLedger solves this with a **3-Layer Pipeline**:
1. **Reconcile** — AI matches payments against invoices
2. **Judge** — AI analyzes failures and proposes rule improvements
3. **Verify** — AI tests the proposal on data it has **never seen before** (holdout set)

If accuracy improves on training data but **drops on the holdout** → the system automatically rejects it as **Reward Hacking**.

---

## ✨ Key Features

### 🤖 AI-Driven Reconciliation
- Automatically match **payments vs invoices** using Gemini 2.5 Flash
- Tolerates **vendor name** variations (typos, abbreviations, different prefixes)
- Tolerates **amount** discrepancies (bank fees, rounding, multi-invoice payments)
- Tolerates **date** differences (payment delays, early payments)
- Detects **split payments** (1 payment = sum of 2+ invoices)

### 🧠 Adaptive Rule Learning
- AI Judge analyzes patterns in matching failures
- Identifies what can be fixed with rules vs **structural gaps** (genuinely missing invoices)
- Proposes specific parameter changes (not just "try again")
- **Iteration Memory** — Judge remembers all previous iterations and never repeats the same mistake

### 🛡️ Anti-Reward-Hacking Verification
- Every proposal is tested on a **hidden holdout set**
- **Hybrid holdout**: anchor set + frontier set (most recent 25% of data)
- Automatically detects when AI tries to "cheat" (train improves but holdout drops)
- Protection against **API failures** — if Gemini errors, system returns INCONCLUSIVE, not a false REWARD_HACKING

### 📊 Multi-Tenant & Per-Tenant Rule Versioning
- Each tenant (company) has its own rule set
- Rule versions persisted in database: `v0 → v1 → v2 → ...`
- Rollback to any previous version at any time

### 📄 Report Export
- **Audit CSV** — full results per transaction
- **Accounting CSV** — accounting format with delta columns
- **Audit PDF** — formal report with per-transaction rationale

### 🔍 Observability
- All LLM calls traced to **Arize Phoenix**
- Monitor latency, token usage, confidence scores
- Anomaly detection and accuracy drift monitoring

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/TS)                       │
│  LandingPage → Upload → Pipeline Steps → Results → Export       │
│  Components: PipelineSteps, ReconcileTable, AccuracyChart,      │
│              RuleProposalCard, VerificationGate, ApprovalControls│
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API (Axios)
┌──────────────────────────▼──────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐│
│  │  Auth Layer  │  │  Agent Layer │  │     Data Layer           ││
│  │  API Key     │  │  reconcile   │  │  CSV Upload / Parser     ││
│  │  per Tenant  │  │  judge       │  │  Ground Truth Loader     ││
│  └─────────────┘  │  verify      │  │  Train/Holdout Splitter  ││
│                   │  rules       │  └──────────────────────────┘│
│                   └──────┬───────┘                               │
└──────────────────────────│──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
   ┌───────────────┐ ┌──────────┐ ┌──────────────────┐
   │  Vertex AI    │ │ Supabase │ │  Arize Phoenix   │
   │  Gemini 2.5   │ │ Postgres │ │  (Observability) │
   │  Flash        │ │ per-row  │ │  LLM Tracing     │
   └───────────────┘ └──────────┘ └──────────────────┘
```

---

## 🔄 AI Pipeline (3-Layer)

### Layer 1 — Reconcile

```
Payment CSV + Invoice CSV
         │
         ▼
┌─────────────────────────────┐
│  _filter_candidate_invoices  │  ← Pre-filter by name similarity
│  (SequenceMatcher threshold) │
└─────────────┬───────────────┘
              │ Candidates
              ▼
┌─────────────────────────────┐
│     Gemini 2.5 Flash        │  ← Deep analysis per candidate pair
│  Prompt: name + amount +    │
│          date + active rules│
└─────────────┬───────────────┘
              ▼
   matched / unmatched / uncertain
```

Each transaction produces:

| Field | Example |
|-------|---------|
| `decision` | `matched` / `unmatched` / `uncertain` |
| `matched_invoice_id` | `INV-007A+INV-007B` (split payment) |
| `confidence` | `0.95` |
| `rationale` | Full explanation of why it matched or not |

---

### Layer 2 — Judge

```
Reconcile Results
        │
        ▼
┌──────────────────────────────────────────┐
│            _build_error_analysis()        │
│                                          │
│  [THRESHOLD-BLOCKED]     sim ≤ threshold │ ← Suggest: lower threshold
│  [STRUCTURAL-GAP]        sim < 0.50      │ ← Do NOT change any rules
│  [STRUCTURAL-GAP-LIKELY] no invoice      │ ← Do NOT change amount/date
│  [NAME-OK-AMOUNT-FAIL]   name ok         │ ← Suggest: raise amount tolerance
└────────────────┬─────────────────────────┘
                 │ Error context + Iteration History
                 ▼
        Gemini 2.5 Flash Judge
                 │
                 ▼
        RuleProposal {
          changes: ["name_similarity_threshold=0.63"],
          rationale: "15 payments blocked by threshold..."
        }
```

**Iteration Memory** prevents the Judge from repeating failures:

```
Iteration #1: threshold=0.80 → REWARD_HACKING (train+24%, holdout-22%)
Iteration #2: Judge remembers → will NOT try 0.80 again
             → tries threshold=0.65 with different justification
```

---

### Layer 3 — Verify (Anti-Reward-Hacking Gate)

```
Proposed Rules (vN)
        │
        ├─── Train set (70%) ──────► accuracy_new_train
        ├─── Holdout set (30%) ────► accuracy_new_holdout   ← KEY METRIC
        └─── Frontier set (25%) ───► accuracy_new_frontier  ← ANTI-OVERFIT
                        │
             ┌──────────▼──────────┐
             │   Verdict Logic     │
             │                     │
             │  delta_holdout > 2% │──► GENUINE_IMPROVEMENT ✅
             │  delta_holdout < -5%│──► REWARD_HACKING ❌
             │  0% on small holdout│──► INCONCLUSIVE ⚠️ (API failure guard)
             │  3× INCONCLUSIVE    │──► HARD_BLOCK 🚫
             └─────────────────────┘
```

---

## 🛡️ Anti-Reward-Hacking

### Why This Matters

Without this protection, an AI could:

```
v0:    threshold=0.95 → 40% accuracy  (correct, but too strict)
vBAD:  threshold=0.10 → 90% accuracy  (CHEATING — accepts almost everything)
```

HonestLedger detects this because:
- `vBAD` might perform well on the **train set** (data the AI has seen before)
- But performs **poorly on the holdout set** (data never seen before)
- If `delta_holdout < -threshold` → **REWARD HACKING DETECTED** — proposal auto-rejected

### Verdict Types

| Verdict | Condition | Action |
|---------|-----------|--------|
| `GENUINE_IMPROVEMENT` | Holdout improves ≥ 2% | Auto-approve (Tier 1) or flagged review (Tier 2) |
| `REWARD_HACKING` | Holdout drops beyond threshold | Auto-reject, recorded in iteration history |
| `INCONCLUSIVE` | Marginal change / API error | System retries with a different proposal |
| `HARD_BLOCK` | 3× consecutive INCONCLUSIVE | Escalated to admin for manual review |

### API Failure Protection

Problem: If Gemini hits a 429 rate limit, all results become UNCERTAIN → accuracy drops to 0% → system falsely detects REWARD_HACKING.

HonestLedger's solution:
```python
# If holdout is 0% while baseline > 10% AND there are API failure signals:
if all_uncertain OR high_uncertain_rate (>50%) OR implausible_collapse:
    return INCONCLUSIVE  # ← honest: unknown, not cheating
    # NOT REWARD_HACKING
```

### Small Dataset Protection

For small datasets (holdout < 12 transactions), a single Gemini decision flip causes a disproportionately large accuracy change:

```
N=9 holdout → 1 transaction flip = 11.1% drop
Standard threshold = 5% → would false-alarm REWARD_HACKING!

Fix: effective_threshold = max(5%, 2/N) = max(5%, 22.2%) = 22.2%
At least 3 transaction flips are required before declaring reward hacking
```

---

## 🛠️ Tech Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.115+ | REST API framework |
| **Python** | 3.12 | Primary programming language |
| **Gemini 2.5 Flash** | via Vertex AI | LLM for reconcile, judge, and verify |
| **SQLAlchemy (async)** | 2.0+ | Async ORM for PostgreSQL |
| **AsyncPG** | 0.29+ | Async PostgreSQL driver |
| **Pydantic** | 2.9+ | Schema validation & serialization |
| **FPDF2** | 2.7+ | PDF report generation |
| **OpenTelemetry** | 1.27+ | LLM call tracing |
| **Google ADK** | 1.0+ | Agent Development Kit |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18 | UI framework |
| **TypeScript** | 5+ | Type safety |
| **Vite** | 5+ | Fast build tool |
| **Tailwind CSS** | 3 | Utility-first styling |
| **Recharts** | — | Accuracy-per-iteration charts |
| **Framer Motion** | — | Landing page animations |
| **Lucide React** | — | Icon library |
| **Axios** | — | HTTP client |

### Infrastructure

| Service | Purpose |
|---------|---------|
| **Google Cloud Run** | Backend deployment (serverless container) |
| **Google Vertex AI** | Gemini 2.5 Flash hosting & inference |
| **Supabase (PostgreSQL)** | Multi-tenant database |
| **Arize Phoenix Cloud** | LLM observability & tracing |

---

## 📁 Project Structure

```
honestledger/
│
├── backend/                          # FastAPI application
│   ├── agent/                        # ★ AI pipeline (CORE OF THE SYSTEM)
│   │   ├── reconcile.py              # Layer 1: Gemini matching engine
│   │   ├── judge.py                  # Layer 2: Error analysis + rule proposal
│   │   ├── verify.py                 # Layer 3: Anti-reward-hacking gate
│   │   ├── rules.py                  # Rule versioning & registry
│   │   └── prompts.py                # All system prompts for Gemini
│   │
│   ├── auth/
│   │   └── middleware.py             # API key authentication per tenant
│   │
│   ├── data/
│   │   ├── loader.py                 # CSV parser, train/holdout splitter
│   │   ├── payments.csv              # Default demo data
│   │   ├── invoices.csv              # Default demo data
│   │   ├── ground_truth.csv          # Train/holdout split labels
│   │   └── complex_test/             # Complex test dataset
│   │       ├── payments.csv          # 30 payments, 9 challenge categories
│   │       ├── invoices.csv          # 28 invoices (2 decoys)
│   │       └── ground_truth.csv      # Holdout labels
│   │
│   ├── db/
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   ├── crud.py                   # Database CRUD operations
│   │   ├── database.py               # Async engine & session factory
│   │   └── migrations/               # SQL migrations for Supabase
│   │       ├── 001_architecture_v2.sql
│   │       ├── 002_oauth.sql
│   │       └── 003_self_signup.sql
│   │
│   ├── models/
│   │   └── schemas.py                # Pydantic schemas
│   │
│   ├── tracing/
│   │   ├── phoenix_setup.py          # Arize Phoenix OTel instrumentation
│   │   └── mcp_client.py             # MCP client for span summaries
│   │
│   ├── config.py                     # Env vars + Gemini client singleton
│   └── main.py                       # FastAPI app + all endpoints
│
├── frontend/                         # React/TypeScript application
│   └── src/
│       ├── components/
│       │   ├── LandingPage.tsx       # Homepage with framer-motion animations
│       │   ├── UploadPanel.tsx       # CSV upload + column auto-detection
│       │   ├── PipelineSteps.tsx     # 4-step pipeline progress bar
│       │   ├── ReconcileTable.tsx    # Reconciliation results table
│       │   ├── RuleProposalCard.tsx  # Displays rule change proposals
│       │   ├── VerificationGate.tsx  # Displays verify results + verdict
│       │   ├── ApprovalControls.tsx  # Approve/Reject buttons
│       │   ├── AccuracyChart.tsx     # Accuracy-per-iteration chart (Recharts)
│       │   ├── RewardHackBanner.tsx  # Red banner on REWARD_HACKING
│       │   ├── NextStepsPanel.tsx    # Right panel: active step guidance
│       │   └── ApiKeyReveal.tsx      # One-time API key reveal page
│       │
│       ├── App.tsx                   # Main orchestrator + auto-loop logic
│       ├── api.ts                    # All API calls to the backend
│       └── types.ts                  # TypeScript type definitions
│
├── scripts/                          # Utility & testing scripts
│   ├── smoke_test.py                 # Quick end-to-end sanity check
│   ├── test_reconcile.py             # Isolated reconciliation test
│   ├── test_judge.py                 # Judge agent test
│   └── test_verify.py                # Verification gate test
│
├── docs/
│   ├── demo_script.md                # Hackathon demo script
│   └── pitch.md                      # Pitch deck notes
│
├── Dockerfile                        # Container image (Python + React build)
├── pyproject.toml                    # Python dependencies (uv)
├── .env.example                      # Environment variable template
└── Makefile                          # Shortcut commands
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Google Cloud account with Vertex AI enabled
- Supabase account (or local PostgreSQL)
- Arize Phoenix account (free)

### 1. Clone & Setup

```bash
git clone https://github.com/your-username/honestledger.git
cd honestledger

# Copy the env template
cp .env.example .env
# Fill in .env with your values
```

### 2. Configure `.env`

```env
# Google Cloud Vertex AI
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-flash

# Arize Phoenix (from app.phoenix.arize.com → Settings → API Keys)
PHOENIX_API_KEY=your-phoenix-api-key
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/your-space-id

# Supabase / PostgreSQL (asyncpg format)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Admin secret for admin endpoints
ADMIN_SECRET=your-secret-here
```

### 3. Database Setup (Supabase)

Run the following SQL files in order via the Supabase SQL Editor:

```
backend/db/migrations/001_architecture_v2.sql  ← Core tables
backend/db/migrations/002_oauth.sql            ← Optional (OAuth)
backend/db/migrations/003_self_signup.sql       ← Self-service signup
```

### 4. Run the Backend

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate   # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Start the development server
uvicorn backend.main:app --reload --port 8000
```

Backend available at: `http://localhost:8000`
Swagger UI docs: `http://localhost:8000/docs`

### 5. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: `http://localhost:5173`

### 6. Create an Account

Open `http://localhost:5173` → click **"Get API Key"** → enter your name and email → **save the API key that appears** (shown only once — cannot be recovered, only regenerated by logging in again).

---

## 📊 CSV Data Format

### Payments

Column names are flexible — the system auto-detects them:

| Standard Column | Accepted Aliases | Example |
|-----------------|------------------|---------|
| `id` | `payment_id`, `trx_id`, `no_transaksi` | `TRX-001` |
| `date` | `payment_date`, `tanggal`, `tgl_bayar` | `2024-01-05` |
| `payer_name` | `nama_pembayar`, `nama_vendor`, `company` | `PT Mitra Solusi` |
| `amount` | `jumlah`, `nominal`, `payment_amount` | `15000000` |
| `reference` | `keterangan`, `description`, `memo` | `Invoice Jan 2024` |

```csv
id,date,payer_name,amount,reference
TRX-001,2024-01-05,PT Mitra Solusi Digital,15000000,IT Services Invoice
TRX-002,2024-01-08,Teknologi Maju Indo,8500000,Project Alpha Payment
```

### Invoices

| Standard Column | Accepted Aliases | Example |
|-----------------|------------------|---------|
| `id` | `invoice_id`, `no_invoice` | `INV-001` |
| `date` | `invoice_date`, `tanggal` | `2024-01-05` |
| `vendor_name` | `nama_vendor`, `supplier`, `pemasok` | `PT Mitra Solusi Digital` |
| `amount` | `jumlah`, `nominal`, `invoice_amount` | `15000000` |
| `invoice_number` | `no_faktur`, `nomor_invoice` | `INV/2024/001` |

### Ground Truth (Optional)

Ensures consistent train/holdout splits across sessions:

```csv
payment_id,matched_invoice_id,split,notes
TRX-001,INV-001,train,exact match
TRX-002,INV-002,train,name abbreviation
TRX-022,INV-022,holdout,holdout set
TRX-023,INV-023,holdout,hardest case
```

`split` column values: `train` or `holdout`

---

## 🔌 API Reference

### Authentication

All requests require the header:
```
x-api-key: hl_xxxxxxxxxxxx
```

### Core Endpoints

#### `POST /reconcile` — Run Reconciliation
```json
// Request
{ "split": "train" }

// Response
{
  "results": [
    {
      "payment_id": "TRX-001",
      "decision": "matched",
      "matched_invoice_id": "INV-001",
      "confidence": 1.0,
      "rationale": "Name, amount, and date all match."
    }
  ],
  "accuracy": 0.80,
  "total": 30,
  "correct": 24,
  "rule_version": "v2"
}
```

#### `POST /judge` — Analyze + Propose Rules
```json
// Request
{ "next_version": "v3" }

// Response
{
  "rule_version": "v3",
  "description": "Lower name threshold to capture abbreviated vendor names",
  "changes": ["name_similarity_threshold=0.63"],
  "rationale": "15 payments blocked by threshold 0.95 but have similarity > 0.63..."
}
```

#### `POST /verify` — Start Verification Job
```json
// Response
{ "job_id": "abc12345", "status": "running" }
```

#### `GET /jobs/{job_id}` — Poll Job Status
```json
// Response (when complete)
{
  "status": "done",
  "result": {
    "verdict": "GENUINE_IMPROVEMENT",
    "delta_holdout": 0.133,
    "delta_train": 0.248,
    "score_holdout": 0.556,
    "explanation": "Holdout improved +13.3%..."
  }
}
```

#### `POST /approve` — Approve New Rules
```json
// Response
{ "approved": true, "active_version": "v3" }
```

#### `POST /reject` — Reject Proposal
```json
// Response (Judge will automatically try a different approach)
{ "rejected": true }
```

#### `GET /status` — System Status
```json
{
  "current_rule_version": "v2",
  "has_reconcile_results": true,
  "has_proposal": false,
  "has_verify_report": false,
  "iteration_count": 3
}
```

#### `GET /history` — Iteration History

All iterations with verdicts, deltas, and changed parameters.

#### `GET /reconcile/export?format=audit_pdf`

Available formats: `audit_csv`, `accounting_csv`, `audit_pdf`

#### `POST /auth/signup` — Register New Tenant
```json
// Request
{ "name": "Example Company Inc.", "email": "finance@example.com" }

// Response (API key shown only once)
{ "api_key": "hl_xxxx...", "tenant_id": "uuid..." }
```

---

## ⚙️ Rule Configuration

Each `RuleSet` consists of the following parameters:

| Parameter | v0 (default) | v1 (sensible) | Description |
|-----------|:------------:|:-------------:|-------------|
| `name_similarity_threshold` | `0.95` | `0.70` | Minimum vendor name similarity (0–1). Lower = more tolerant of name variations |
| `amount_tolerance_abs` | `2,000` | `10,000` | Absolute amount difference tolerance (in currency units) |
| `amount_tolerance_pct` | `0.5%` | `2%` | Percentage-based amount tolerance |
| `date_tolerance_days` | `1` day | `5` days | Maximum allowed date difference (days) |
| `min_confidence` | `0.90` | `0.60` | Minimum Gemini confidence score for a valid decision |

### Example Scenarios

```
v0 (too strict — demo baseline):
  "Teknologi Maju Indo" vs "PT Teknologi Maju Indonesia"
  → similarity ≈ 0.79 < threshold 0.95 → BLOCKED ❌

v2 (optimal for complex_test):
  "Teknologi Maju Indo" vs "PT Teknologi Maju Indonesia"
  → similarity ≈ 0.79 > threshold 0.63 → PASSED → Gemini: matched ✅

  "Jaya Mitra" vs "PT Jaya Mitra Bersama"  (HARDEST CASE)
  → similarity ≈ 0.75 > threshold 0.63 → PASSED → Gemini: matched ✅

v_greedy (reward-hacking demo):
  "Ahmad Fauzi" vs "PT Mitra Solusi Digital"
  → threshold 0.00 → PASSED → Gemini: matched ❌  (WRONG!)
  → Verify: holdout drops → REWARD_HACKING DETECTED
```

---

## 📡 Observability with Arize Phoenix

HonestLedger integrates **Arize Phoenix** for real-time LLM monitoring.

### What Gets Traced

- Every Gemini API call (reconcile, judge, verify)
- Token usage per request
- End-to-end latency per pipeline run
- Confidence score distribution
- Error rate (429 quota exceeded, timeouts)

### Phoenix Setup

1. Sign up at [app.phoenix.arize.com](https://app.phoenix.arize.com) (free)
2. Create an API key: **Settings → API Keys**
3. Copy your space endpoint: `https://app.phoenix.arize.com/s/your-space`
4. Add to `.env`:
   ```env
   PHOENIX_API_KEY=eyJ...
   PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/your-space
   ```

### Viewing Traces

Log in to the Phoenix dashboard → select the **"honestledger"** project → view all spans from every pipeline run.

---

## ☁️ Deploy to Cloud Run

### One-Command Deploy

```bash
gcloud run deploy honestledger \
  --source . \
  --project=YOUR_PROJECT_ID \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,\
GOOGLE_CLOUD_LOCATION=us-central1,\
GEMINI_MODEL=gemini-2.5-flash,\
PHOENIX_API_KEY=YOUR_KEY,\
PHOENIX_COLLECTOR_ENDPOINT=YOUR_ENDPOINT,\
DATABASE_URL=YOUR_SUPABASE_URL,\
ADMIN_SECRET=YOUR_SECRET"
```

### GCP Requirements

```bash
# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  --project=YOUR_PROJECT_ID

# Grant Vertex AI permission to the default service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | Region (default: `us-central1`) |
| `GEMINI_MODEL` | Gemini model name (default: `gemini-2.5-flash`) |
| `PHOENIX_API_KEY` | Arize Phoenix API key |
| `PHOENIX_COLLECTOR_ENDPOINT` | Phoenix Cloud endpoint URL |
| `DATABASE_URL` | PostgreSQL connection string (asyncpg format) |
| `ADMIN_SECRET` | Secret for admin endpoints |

---

## 📖 Glossary

Definitions of all technical terms used in the HonestLedger system.

---

### A

**Accuracy**
The percentage of payments successfully matched against their correct invoices.
`accuracy = matched_count / total_payments`
Example: 24/30 = 80%

**Adaptive Rule Learning**
The system's ability to learn from matching failure patterns and automatically adjust reconciliation rules — without ever modifying the original uploaded data.

**Amount Tolerance**
The maximum allowable difference between a payment amount and an invoice amount. Required because of: bank transfer fees, rounding differences, and administrative deductions.

**API Key**
A per-tenant authentication credential in the format `hl_xxxx`. Displayed only once at registration. If lost, logging in again generates a new key and immediately invalidates the old one.

**Arize Phoenix**
An observability platform purpose-built for LLMs (Large Language Models). HonestLedger sends all Gemini call traces to Phoenix for real-time monitoring.

---

### C

**Cluster Tag**
A contextual label that the Judge assigns to characterize the data pattern: `vendor_lokal`, `internasional`, `marketplace`, or `mixed`. Helps the Judge produce more relevant, targeted proposals.

**Confidence Score**
A value from 0.0 to 1.0 indicating how certain Gemini is about a matching decision. If below `min_confidence`, the decision automatically becomes `uncertain`.

---

### D

**Date Tolerance**
The maximum allowed date difference (in days) between a payment date and an invoice date. Necessary because payments are often made a few days before or after the invoice due date.

**Delta Holdout**
The change in accuracy on the holdout set between the old and proposed rules.
`delta_holdout = new_holdout_accuracy - baseline_holdout_accuracy`
This is the **primary metric** that determines the verify verdict.

**Delta Train**
The change in accuracy on the training set. If delta_train is high but delta_holdout is negative, it is a strong indicator of **Reward Hacking**.

---

### F

**Frontier Set**
The most recent 25% of data by date. Acts as the second layer of the Hybrid Holdout to detect overfitting to older data patterns. Rules that work well on old data but poorly on new data = overfitting.

---

### G

**Gemini 2.5 Flash**
Google's generative AI model, accessed via Vertex AI. It serves as the "brain" of the system for three functions: transaction matching, failure analysis, and anti-cheat verification.

**Ground Truth**
An optional CSV file containing the correct answers: which payment should match which invoice, and whether each payment belongs to the `train` or `holdout` split.

---

### H

**Hard Block**
A verdict issued after 3 consecutive INCONCLUSIVE results. It halts the automatic pipeline and flags the case for manual review by an admin.

**Holdout Set**
A subset of data that is **never used** during rule optimization. It is only used during verification to measure whether an improvement is truly generalizable, or merely memorized the training data.

**Hybrid Holdout**
A combination of two holdout types:
- **Anchor set**: from `ground_truth.csv`, consistent across all sessions
- **Frontier set**: the most recent 25% of data, rotates over time

This makes reward hacking detection more robust against different forms of overfitting.

---

### I

**INCONCLUSIVE**
A verify verdict when the accuracy change is too small to draw a conclusion, or when results cannot be trusted due to an API error. The system retries with a different proposal.

**Invoice**
A bill issued by a vendor/supplier to the company. Contains: invoice number, vendor name, amount, and due date.

**Iteration History**
The Judge's memory of all previous iterations: which parameters were changed, what verdicts were received, and which strategies have already been tried. Prevents the Judge from repeating proven-to-fail approaches.

---

### J

**Judge**
Layer 2 of the AI pipeline. Analyzes reconciliation results using category tags (`[THRESHOLD-BLOCKED]`, `[STRUCTURAL-GAP]`, etc.), then proposes specific, measurable rule parameter changes.

---

### M

**MatchDecision**
The three possible Gemini decisions for each transaction:
- `matched` — the payment correctly corresponds to an invoice
- `unmatched` — no matching invoice was found
- `uncertain` — Gemini is not confident enough (confidence below threshold)

**Multi-Tenant**
An architecture where a single deployment serves many companies in full isolation. Each tenant has its own data, rule versions, and iteration history that cannot be accessed by other tenants.

---

### N

**Name Similarity Threshold**
A minimum vendor name similarity score (0–1) computed by the SequenceMatcher algorithm. Only candidate pairs with similarity ≥ threshold are sent to Gemini for deep analysis.

| Value | Effect |
|-------|--------|
| `0.95` | Only near-identical names pass (v0 — too strict) |
| `0.70` | Tolerates common abbreviations (v1 — default) |
| `0.63` | Tolerates significant truncations (v2 — optimal for complex test) |
| `0.00` | No filtering at all (v_greedy — DANGEROUS) |

---

### P

**Payment**
A record of a money transfer from the company's ledger. Contains: transaction ID, date, payer name, amount, and reference/memo.

**Pipeline**
The automated sequence: `Reconcile → Judge → Verify → Approve → (back to Reconcile)`. Runs automatically until a stopping condition is met.

---

### R

**Rationale**
A text explanation from Gemini describing why a payment was matched or left unmatched. Stored per transaction and included in all audit export formats.

**Reconcile**
Layer 1 of the AI pipeline. Matches each payment against the most suitable invoice based on the currently active rules.

**Reward Hacking**
The behavior of an AI "cheating" to inflate accuracy: loosening rules far beyond reason so that training data accuracy improves, while real-world or unseen data performance degrades. This is a documented phenomenon in machine learning that HonestLedger is specifically designed to prevent.

**REWARD_HACKING (Verdict)**
The verify verdict when `delta_holdout < -effective_hacking_drop`. The proposal is auto-rejected and recorded in iteration history so the Judge does not repeat a similar strategy.

**Rule Version**
A complete snapshot of all rule parameters at a given point in time (v0, v1, v2, ...). Persisted permanently in the database per tenant. Can be rolled back to at any time.

**RuleSet**
The full configuration of five matching parameters: `name_similarity_threshold`, `amount_tolerance_abs`, `amount_tolerance_pct`, `date_tolerance_days`, `min_confidence`.

---

### S

**SequenceMatcher**
A Python algorithm (from the `difflib` library) that measures the similarity between two strings. Used as a fast pre-filter before Gemini — only sending relevant candidates to the LLM, reducing API call volume.

**Small Dataset Mode**
A special mode activated when holdout contains fewer than 12 transactions. The REWARD_HACKING threshold is dynamically adjusted because a single Gemini decision flip produces a disproportionately large accuracy change mathematically.

**Split Payment**
A single payment that represents the combined total of two or more invoices.
Example: TRX-007 (33,500,000) = INV-007A (18,000,000) + INV-007B (15,500,000)

**Structural Gap**
A payment that genuinely has no matching invoice — not because the rules are insufficient, but because: the invoice hasn't been issued yet (down payment), the transaction is not from a vendor (refund, wrong transfer), or the vendor is unrecognized. The system correctly identifies and flags these for manual review.

---

### T

**Tenant**
A single company account within the system. Each tenant has full isolation: its own API key, data, rule version history, and iteration records.

**Tier (Verify Tier)**
The confidence level associated with a GENUINE_IMPROVEMENT verdict:
- **Tier 1**: High confidence (delta ≥ 5%, small train-holdout gap) → eligible for auto-approve
- **Tier 2**: Moderate improvement → flagged for human review within 24 hours
- **Tier 3**: Extreme outcomes (REWARD_HACKING / HARD_BLOCK) → escalated to admin

**Train Set**
70% of the data used during rule evaluation. Rules are measured against this data, but the final verdict is always determined by the **holdout set**, never the train set.

---

### V

**Verify**
Layer 3 of the AI pipeline — the Anti-Reward-Hacking Gate. Runs proposed rules against holdout data (never used during optimization) to prove that improvements are real and not engineered.

**Vertex AI**
Google Cloud's platform for hosting and running generative AI models. HonestLedger uses Vertex AI to access Gemini 2.5 Flash, providing enterprise-grade reliability and quota controls.

---

### Complete Flow Diagram

```
┌──────────────┐
│  Upload CSV  │  payments.csv + invoices.csv (+ optional ground_truth.csv)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Reconcile  │  Gemini matches each payment against candidate invoices
│POST /reconcile│  → result: matched/unmatched/uncertain per transaction
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Judge     │  Failure pattern analysis + iteration memory
│ POST /judge  │  → proposal: {"changes": ["threshold=0.63"]}
└──────┬───────┘
       │
       ▼
┌──────────────────────────┐
│         Verify            │  Test proposal against hidden holdout set
│ POST /verify → poll job   │
│                           │
│  GENUINE_IMPROVEMENT? ────┼──► POST /approve → active rules = vN
│         │                 │              │
│         NO                │    POST /reconcile (loop restarts)
│         ▼                 │
│  REWARD_HACKING? ─────────┼──► auto-reject → Judge tries a new strategy
│         │                 │
│         NO                │
│         ▼                 │
│  INCONCLUSIVE? ───────────┼──► retry (max 5×) → HARD_BLOCK → stop
└──────────────────────────┘
```

---

## 🤝 Contributing

This project was built for the **Google Cloud Hackathon — Arize Track (2026)**.

To contribute:
1. Fork this repository
2. Create a branch: `git checkout -b feature/your-feature-name`
3. Commit: `git commit -m 'feat: add feature X'`
4. Push: `git push origin feature/your-feature-name`
5. Open a Pull Request

---

## 📜 License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built with ❤️ for **Google Cloud Hackathon 2026**

[![Live Demo](https://img.shields.io/badge/🚀_Try_It_Now-honestledger-4F46E5?style=for-the-badge)](https://honestledger-816125388987.us-central1.run.app)

*"It's not about how high the accuracy is — it's about how honest the AI is."*

</div>
