# HonestLedger — Devpost Submission

## Tagline
The first financial reconciliation agent that catches itself cheating — and proves it didn't.

---

## Inspiration

Self-improving AI agents have a well-known failure mode: they optimise for the *proxy metric* (match rate) rather than the *true goal* (accurate reconciliation). An agent can inflate its score by loosening every threshold — matching more transactions, even wrong ones. This is reward hacking.

Research on reward hacking detection exists — EvilGenie (MIT/Cambridge, Nov 2025), ASG-SI (arXiv:2512.23760, Dec 2025) — but exclusively in the coding domain. Financial reconciliation has equally objective ground truth (balance/don't balance, match/no match), yet no one had transplanted the methodology there.

That gap became HonestLedger.

---

## What It Does

HonestLedger reconciles business payments against invoices using a 3-layer pipeline:

**Layer 1 — Reconcile**: Gemini (via Vertex AI) reasons over each payment vs. all candidate invoices. Not string-matching — actual reasoning: "payer name is a known abbreviation of the vendor, amount differs by a typical bank fee, date within 3-day lag → matched."

**Layer 2 — Introspect (Judge)**: A second Gemini instance reads the Phoenix traces of Layer 1's decisions, identifies error patterns, and proposes concrete rule changes ("raise name similarity threshold to 0.7, allow Rp 10,000 amount tolerance").

**Layer 3 — Verify (Anti-Reward-Hacking Gate)**: Before any rule change goes live:
- Run the proposed rules on the TRAIN set → score_train_new
- Run the proposed rules on a HOLDOUT set (never seen) → score_holdout_new
- If holdout improves ≥ 2%: **GENUINE IMPROVEMENT** → request human approval
- If holdout drops ≥ 5%: **REWARD HACKING DETECTED** → auto-reject, log as cheating attempt
- Human can then approve, reject, or rollback — full audit trail

---

## How We Built It

- **Gemini 2.5 Flash** via Vertex AI for both reconciliation reasoning and LLM-as-a-Judge
- **Google ADK** (Agent Development Kit) for code-owned agent structure
- **Arize Phoenix** (free cloud tier) for full OpenInference tracing of every Gemini call
- **Phoenix MCP server** (`@arizeai/phoenix-mcp` via npx) for programmatic trace introspection
- **FastAPI** backend with 15+ REST endpoints
- **React + Vite + Tailwind + Framer Motion** frontend dashboard with animated reward-hacking banner
- **`uv`** package manager following Arize hackathon starter patterns
- **Apache 2.0** license for compatibility with the Arize starter repo

---

## Challenges

**Reward hacking is hard to engineer**: Gemini is too smart to follow "bad" rules blindly. We solved this by pre-filtering invoice candidates mechanically (hard threshold on name similarity) and adding an "aggressive match mode" instruction when `min_confidence=0.0`, ensuring greedy rules produce demonstrably worse holdout results.

**Phoenix MCP in automated loops**: The Phoenix MCP server was designed for interactive Gemini CLI use. We built a programmatic client that spawns the MCP server as a subprocess and queries it via JSON-RPC, enabling fully automated trace introspection in our judge loop.

**Demo in 3 minutes**: Full Gemini pipeline takes ~25 minutes (rate limits). We added a `/demo/seed` endpoint that loads pre-computed real results instantly, enabling live dashboard demos without waiting.

---

## Accomplishments

- First financial reconciliation system with reward-hacking detection — no prior art found
- Both demo scenarios (GENUINE_IMPROVEMENT and REWARD_HACKING) verified end-to-end on real Gemini calls
- Full observability: every reasoning step visible in Arize Phoenix dashboard
- Clean separation: Lilian Weng's "diverse holdout scenarios" principle implemented in production code

---

## What We Learned

- Rules in LLM prompts are suggestions, not constraints — mechanical pre-filtering is necessary for reliable rule enforcement
- BatchSpanProcessor is essential for Phoenix in production (SimpleSpanProcessor blocks on each span export)
- LLM-as-a-Judge works remarkably well for structured domains with clear error signals

---

## What's Next

- Multi-agent version: parallel judge instances voting on proposals
- Real-time streaming: live reconciliation with WebSocket updates
- Enterprise connectors: ERP integrations (SAP, Oracle) via MCP servers
- Generalise to other self-improving financial agents (fraud detection, credit scoring)

---

## Built With

`google-gemini` · `vertex-ai` · `google-adk` · `arize-phoenix` · `openinference` · `phoenix-mcp` · `fastapi` · `react` · `framer-motion` · `recharts` · `tailwindcss` · `uv` · `python`

---

## Try It

- **Repo**: [github.com/YOUR_USERNAME/honestledger](https://github.com/YOUR_USERNAME/honestledger)
- **Demo**: [URL_HERE]
- **Video**: [YouTube/Vimeo URL]
