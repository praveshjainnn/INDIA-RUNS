# RecruiterIQ

**AI-powered candidate ranking for the India Runs Data & AI Challenge — Redrob Hackathon**

Keyword filters miss the right people. Not because the talent isn't there — because matching strings to strings isn't the same as understanding a person's career. RecruiterIQ replaces keyword search with a hybrid semantic + reasoning pipeline that ranks 487,000 candidates the way a great recruiter would: by actually reading who fits the role.

---

## The Problem with How Hiring Works Today

A recruiter posts a job for a Senior ML Engineer. The ATS searches for the string "PyTorch". It misses the candidate who wrote "built custom autograd engine in C++/Python", because "PyTorch" doesn't appear. It surfaces someone who listed "PyTorch" in a skills dump they copy-pasted from a template.

RecruiterIQ doesn't search for words. It understands what the role needs — and finds who genuinely fits.

---

## How It Works

The pipeline runs in four phases designed around one constraint: **you cannot send 487,000 profiles to a cloud LLM**. That would cost ~$40,000 per run and take 6+ hours. So we built a cascade.

```
487,000 candidates
        │
        ▼  Phase 1 — Fast Heuristic Filter (Python, O(N), milliseconds)
     ~50,000
        │
        ▼  Phase 2 — Local Semantic Embedding (all-MiniLM-L6-v2, no API, no GPU)
       500
        │
        ▼  Phase 3 — 5-Dimensional Scoring (structured signals + cosine similarity)
        30
        │
        ▼  Phase 4 — LLM Deep Reasoning (xAI Grok-2-1212, top 30 only)
       100  ──→  submission.csv + recruiteriq_report.xlsx
```

**Total runtime: ~2–3 minutes. API cost: under $1.**

---

## Scoring Model

Every candidate is scored across five dimensions. These aren't arbitrary — each captures something a real recruiter actually weighs.

| Dimension | Weight | What It Captures |
|-----------|--------|-----------------|
| Skill Alignment | 30% | Semantic match between candidate skills and JD requirements. Uses cosine similarity on 384D vectors — "Weaviate" matches "vector database" even without exact word overlap. Boosted by peer endorsement count (logarithmic scale). |
| Experience Relevance | 25% | Domain proximity, seniority fit via Gaussian banding (no hard cutoffs), academic prestige tier. |
| Career Signal | 20% | Career velocity (promotion rate relative to YOE), tenure consistency (rewards stability, penalizes <6-month stints as attrition risk). |
| Behavioral Fit | 15% | Availability signals: open-to-work flag, notice period length, last active date, recruiter response rate. |
| Cultural Alignment | 10% | Work mode match (remote/hybrid/onsite), city tier, relocation willingness. |

---

## The 15 Pipeline Models

<details>
<summary><strong>Phase 1 — Cascade Filtering</strong></summary>

**1. Dual-Pass Cascade Orchestrator** `pipeline/pipeline.py`
Controls which candidates advance to each stage. Phase 1 runs in O(N) across the full 487K pool. Selects top 500 for embedding. Selects top 30 for LLM. Reduces API cost by 99.9%.

**2. Technical Title Classifier** `pipeline/fast_scorer.py`
Token-based classifier that boosts technical role titles (ML, AI, Engineer, Architect) and penalizes non-technical ones (HR, Sales, Consulting). No ML model needed — pure heuristics run in microseconds per candidate.

**3. Narrative Text Builder** `pipeline/feature_extractor.py → build_narrative()`
Before any embedding, all candidate fields (headline, role descriptions, education, certifications) are concatenated into a single rich narrative. This maximizes information density for the vector encoder downstream.

</details>

<details>
<summary><strong>Phase 2 — Local Semantic Embeddings</strong></summary>

**4. SBERT Dense Vector Encoder** `pipeline/embedder.py`
Uses `sentence-transformers/all-MiniLM-L6-v2` to encode candidate narratives and the JD into 384-dimensional vectors. Runs locally on CPU — no API key, no network call, no data leaving your machine.

**5. Cosine Similarity Matcher** `pipeline/scorer.py → _score_skill_alignment()`
Computes dot product of normalized embedding vectors. Captures semantic intent — a JD asking for "retrieval systems experience" correctly surfaces candidates who worked with Elasticsearch, Faiss, and Milvus even without those exact words in the JD.

</details>

<details>
<summary><strong>Phase 3 — Multi-Dimensional Scoring</strong></summary>

**6. Seniority Gaussian Banding** `pipeline/scorer.py → _years_fit()`
Rather than hard filtering on years of experience, we fit a Gaussian curve centered at the JD midpoint. A 6.5-year candidate for a 5–8 year role scores ~1.0; a 4-year candidate scores ~0.75 rather than zero. No cliff edges.

**7. Tenure Consistency Model** `pipeline/feature_extractor.py → _tenure_consistency()`
Calculates average tenure per role. Peak score at 18+ months. Progressive decay for frequent job changes (<6-month stints flagged as attrition risk). A 10-year career with 4 stable roles outscores one with 12 short-tenure roles.

**8. Career Velocity Tracker** `pipeline/feature_extractor.py → _career_velocity()`
Counts senior title progressions (Senior → Lead → Principal → Manager) divided by total experience years. Identifies fast-tracked talent versus lateral movers.

**9. Company Domain Matcher** `pipeline/scorer.py → _score_experience_relevance()`
Compares the candidate's employer industries against the JD's target domain. Rewards product/SaaS/fintech/AI backgrounds. Discounts IT outsourcing and generic consulting for technical product roles.

**10. Academic Prestige Tiering** `pipeline/scorer.py → _score_experience_relevance()`
Maps institutions to tiers (IIT/NIT = Tier 1 through regional colleges = Tier 4) and weights degree levels (PhD > MTech/MS > BTech). Applied as a modest boost — not a filter.

**11. Skill Endorsement Boost** `pipeline/scorer.py → _score_skill_alignment()`
Integrates LinkedIn endorsement counts as social proof, applied with logarithmic scaling. The gap between 0 and 10 endorsements matters more than 90 to 100. Candidates without endorsements aren't penalized — they just receive no boost.

**12. Skill Rarity Weighting (IDF Heuristic)** `pipeline/scorer.py → _score_skill_alignment()`
Must-have JD skills are weighted significantly higher than nice-to-haves. Missing a required skill (e.g. "Kubernetes") costs more than missing a preferred one (e.g. "Helm"). Mirrors actual recruiter prioritization.

**13. Availability Classifier** `pipeline/scorer.py → _score_behavioral_fit()`
Combines: open-to-work flag (binary boost), notice period decay (shorter = higher score), days since last active (recency decay), and historical recruiter response rate to predict how reachable and hireable a candidate actually is.

**14. Work Mode & Geolocation Matcher** `pipeline/scorer.py → _score_cultural_alignment()`
Matches candidate work mode preference (remote/hybrid/onsite) against the JD. Applies location boost for Tier-1 Indian tech cities (Bangalore, Pune, Noida, Hyderabad, NCR). Relocation-willing candidates outside these cities also receive a partial boost.

</details>

<details>
<summary><strong>Phase 4 — LLM Deep Reasoning</strong></summary>

**15. Grok Deep-Reasoning Re-ranker** `pipeline/llm_engine.py → rerank_candidates_with_llm()`
The top 30 candidates from Phase 3 are sent to xAI Grok-2-1212 in a single structured batch call. Grok adjusts final scores based on holistic profile reasoning, generates a 2-sentence emoji-free recruiter rationale per candidate, and writes a targeted interview probe question based on each candidate's specific gaps relative to the JD.

If the API is unavailable or the key is invalid, the pipeline automatically falls back to template-based rationale generation from local scores. The output remains fully compliant.

</details>

---

## Submission Output

`submission.csv` — 100 ranked candidates, validated against hackathon submission rules.

```
candidate_id,rank,score,reasoning
CAND_0077337,1,0.9965,"Staff Machine Learning Engineer at 7.0 yrs lands well on the JD because of Semantic Search, QLoRA, Pinecone and real production work..."
CAND_0071974,2,0.9919,"Senior AI Engineer at 7.8 yrs lands well on the JD because of LoRA, Weaviate, PEFT and real production work..."
CAND_0010257,3,0.9873,"With 6.5 yrs in senior data scientist, the strongest evidence is Milvus, TensorFlow, Python plus shipping history..."
```

**Compliance checklist:**
- 100 rows, ranks 1–100
- Scores strictly non-increasing, normalized to `[0.2000, 0.9950]`
- Tie-breaks resolved by `candidate_id` ascending
- Zero emojis in any reasoning field
- `recruiteriq_report.xlsx` with score breakdowns, matched skills, probe questions, formatted headers

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Next.js 14 (App Router) |
| Styling | TailwindCSS, custom CSS — Inter font, brand color theme |
| Backend | FastAPI, Python 3.10+ |
| Local AI | PyTorch, `sentence-transformers` — `all-MiniLM-L6-v2` |
| Vector Math | NumPy — cosine similarity at scale |
| Data | Pandas, OpenPyXL |
| Validation | Pydantic v2 |
| Cloud LLM | xAI Grok-2-1212 (top 30 candidates only) |

---

## Running Locally

**Prerequisites:** Python 3.10+, Node.js 18+

```bash
# 1. Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r recruiteriq/requirements.txt
python api/main.py               # Runs on http://localhost:8000

# 2. Frontend
cd frontend
npm install
npm run dev                      # Runs on http://localhost:3000
```

Open `http://localhost:3000`. Upload a dataset, paste a job description, click **Analyse & Rank**.

**To use Grok re-ranking:** open the Profile drawer in the top-right, select xAI Grok-2-1212, and enter your API key (`xai-...`). The pipeline works without it — local scoring remains active as a fallback.

---

## Project Structure

```
recruiteriq/
├── pipeline/
│   ├── pipeline.py          # Dual-pass cascade orchestrator
│   ├── fast_scorer.py       # Phase 1 heuristic filter
│   ├── feature_extractor.py # Narrative builder, career velocity, tenure signals
│   ├── embedder.py          # SBERT local embedding
│   ├── scorer.py            # 5-dimensional scoring engine
│   └── llm_engine.py        # Grok API re-ranker + fallback
├── api/
│   └── main.py              # FastAPI server
├── requirements.txt
frontend/
├── app/                     # Next.js App Router pages
├── components/              # Candidate cards, score breakdowns, radar charts
└── package.json
submission.csv               # Hackathon output — 100 ranked candidates
recruiteriq_report.xlsx      # Full detailed report
```

---

## Why This Approach Works

**The core claim:** semantic understanding + structured signals + LLM reasoning produces better shortlists than any single method alone.

- Semantic embeddings alone miss structured signals like tenure stability and availability.
- Keyword/structured scoring alone misses candidates who express skills differently.
- LLM-only ranking is economically infeasible at 487K profiles.

The cascade earns the right to use LLM reasoning where it matters — the final 30 — by handling scale with efficient local models first. The result is a shortlist a recruiter can actually trust, with an explanation for every rank.

---

*Built for the India Runs Data & AI Challenge — Redrob Hackathon*
