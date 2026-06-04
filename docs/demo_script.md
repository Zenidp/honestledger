# HonestLedger — Demo Video Script (3 minutes)

## Setup (before recording)

```bash
# Terminal 1 — backend
make run

# Terminal 2 — frontend
make run-frontend

# Browser: http://localhost:5173
```

Keep both terminals visible but minimised. Record at 1080p.

---

## 0:00 – 0:10 | Hook (10 sec)

**Screen**: Dashboard empty state  
**Voice**:
> "What if your AI agent was quietly cheating — and you had no way to know?  
> This is HonestLedger. It's the first reconciliation agent that catches itself."

---

## 0:10 – 0:30 | The Problem (20 sec)

**Action**: Click **"⚡ Seed Full Demo"** button  
**Screen**: ReconcileTable populates with 20 payments, v0 rules, 80% accuracy  
**Zoom**: Show 4 payments (PAY005–PAY008) marked as `unmatched` with rationale "No candidates passed name similarity filter"  

**Voice**:
> "With strict rules, the agent misses 4 legitimate payments — 
> vendor name variants like 'PT Global Tekno' vs 'PT Global Teknologi'.  
> 80% accuracy. Not good enough."

---

## 0:30 – 1:00 | Phoenix Sees Everything (30 sec)

**Action**: Open Arize Phoenix dashboard in new tab: https://app.phoenix.arize.com  
**Screen**: Show traces — each payment decision with full reasoning visible  
**Zoom**: Click one trace, show the Gemini rationale text  

**Voice**:
> "Every decision is traced to Arize Phoenix.  
> The judge reads these traces and diagnoses the problem."

**Action**: Switch back to dashboard, point to RuleProposalCard  
**Screen**: Shows proposal: "Relax name similarity from 0.95 → 0.7, amount tolerance 2k → 10k"

**Voice**:
> "The judge proposes: relax the name matching threshold.  
> But wait — should we trust it?"

---

## 1:00 – 1:40 | The Verification Gate (40 sec)

**Screen**: VerificationGate component  
**Zoom**: Two score bars — train and holdout  

**Voice**:
> "Before accepting any change, HonestLedger runs it against a HOLDOUT set —  
> data the agent has never seen."

**Screen**: Score bars animate:
- Train: 80% → 100% (+20%)  
- Holdout: 90% → 100% (+10%)

**Screen**: Green `GENUINE IMPROVEMENT` badge appears  

**Voice**:
> "Holdout accuracy jumps 10%. This is a genuine improvement.  
> The system requests human approval."

**Action**: Click **"Approve & Activate"**  
**Screen**: AccuracyChart shows first iteration dot (green ✓)

---

## 1:40 – 2:20 | CLIMAX — Reward Hacking Detected (40 sec)

**Action**: Click **"Greedy Attack"** button  
**Screen**: VerificationGate updates — score bars move:
- Train: 100% → 90% (−10%)  
- Holdout: 100% → 90% (−10%)

**Screen**: Red `REWARD HACKING` badge appears  
**Screen**: Red banner drops from top: **"REWARD HACKING DETECTED — Rule rejected"**  

**Voice**:
> "Now watch what happens when someone tries to cheat.  
> A greedy proposal removes ALL matching constraints.  
> Train score looks high — but holdout DROPS."

**Pause 2 seconds on the red banner.**

**Voice**:
> "HonestLedger caught the agent cheating.  
> Proposal auto-rejected. Logged in audit trail."

**Action**: Click **"Reject"**  
**Screen**: Banner dismisses. AccuracyChart shows second dot (red ⚠)

---

## 2:20 – 2:50 | The Arc of Victory (30 sec)

**Screen**: AccuracyChart — both iterations visible  
**Zoom**: Green dot (genuine, approved) vs red dot (hacking, rejected)  

**Voice**:
> "Genuine improvements accumulate.  
> Reward hacking is blocked every time."

**Screen**: Scroll to show iteration pills: "#1 v1-proposed → approved" and "#2 v1-greedy → rejected"

**Voice**:
> "Full audit trail. Every decision recorded.  
> This is what trustworthy self-improving AI looks like in finance."

---

## 2:50 – 3:00 | Closing (10 sec)

**Screen**: Dashboard overview — full pipeline visible  

**Voice**:
> "HonestLedger — not just smart. Honest."

**Screen**: Fade to repo URL / Devpost link

---

## Recording Tips

1. Use **OBS** or **Loom** — 1080p, 30fps minimum
2. Hide bookmarks bar and browser extensions
3. Use full-screen browser, font size 100%
4. Record audio separately if possible (cleaner)
5. **Seed the demo before recording** — all data loads in < 1 second
6. Edit in DaVinci Resolve (free) or iMovie — cut pauses, add captions
7. Upload to YouTube as **Unlisted** (not Private — Devpost needs to embed it)

## Timezone Reminder

**Deadline: June 11, 2026, 14:00 PDT**  
PDT = UTC−7 → that's **June 12, 2026 at 04:00 WIB**  
Submit at least 2 hours early (by June 12, 02:00 WIB)
