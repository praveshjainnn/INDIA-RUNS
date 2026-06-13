# RecruiterIQ

**AI-powered candidate ranking — India Runs Data & AI Challenge, Redrob Hackathon**

Keyword filters miss the right people. Not because the talent isn't there — because matching strings to strings isn't the same as understanding a career. RecruiterIQ replaces keyword search with a hybrid semantic + reasoning pipeline that ranks 487,000 candidates the way a great recruiter would: by actually reading who fits the role.

---

## System Architecture

The pipeline runs as a four-phase dual-pass cascade. Each phase narrows the candidate pool so the most expensive operation — cloud LLM reasoning — runs only on the top 30 candidates, not 487,000.

```
┌─────────────────────────────────────────────────────────────────────┐
│  INPUT                                                               │
│  Job Description (free text)          Candidate Dataset (487K)      │
└──────────────────────────┬───────────────────────┬──────────────────┘
                           └──────────┬────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1 — Fast Heuristic Filter                                     │
│  O(N) Python · no GPU · milliseconds · 487,000 → ~50,000            │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  Model 1        │  │  Model 2        │  │  Model 3            │  │
│  │  Dual-pass      │  │  Technical      │  │  Narrative text     │  │
│  │  cascade        │  │  title          │  │  density builder    │  │
│  │  orchestrator   │  │  classifier     │  │                     │  │
│  │  pipeline.py    │  │  fast_scorer.py │  │  feature_extractor  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ ~50,000 candidates
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 2 — Local Semantic Embeddings                                 │
│  all-MiniLM-L6-v2 · 384D vectors · CPU only · no API · → 500        │
│                                                                      │
│  ┌──────────────────────────┐   ┌──────────────────────────────┐    │
│  │  Model 4                 │   │  Model 5                     │    │
│  │  SBERT dense vector      │   │  Cosine similarity           │    │
│  │  encoder                 │   │  matcher                     │    │
│  │  embedder.py             │   │  scorer.py                   │    │
│  └──────────────────────────┘   └──────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ Top 500
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 3 — 5-Dimensional Scoring                                     │
│  Structured signals + semantic blend · 500 → 30                     │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Model 6     │  │  Model 7     │  │  Model 8     │              │
│  │  Seniority   │  │  Tenure      │  │  Career      │              │
│  │  Gaussian    │  │  consistency │  │  velocity    │              │
│  │  banding     │  │  model       │  │  tracker     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Model 9     │  │  Model 10    │  │  Model 11    │              │
│  │  Company     │  │  Academic    │  │  Skill       │              │
│  │  domain      │  │  prestige    │  │  endorsement │              │
│  │  matcher     │  │  tier        │  │  boost       │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Model 12    │  │  Model 13    │  │  Model 14    │              │
│  │  Skill       │  │  Availability│  │  Geolocation │              │
│  │  rarity IDF  │  │  classifier  │  │  & work mode │              │
│  │  weighting   │  │              │  │  matcher     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ Top 30
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 4 — LLM Deep Reasoning                                        │
│  xAI Grok-2-1212 · 1 API call · top 30 only · under $1 total cost   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Model 15 — Grok deep-reasoning re-ranker                   │    │
│  │  Adjusts scores · writes 2-sentence rationale per candidate  │    │
│  │  Generates interview probe questions from profile gaps        │    │
│  │  llm_engine.py · auto-fallback to local scoring if API fails │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────┬────────────────────┬─────────────────────┘
                           │                    │
               ┌───────────▼──────┐   ┌─────────▼──────────────┐
               │  submission.csv  │   │  recruiteriq_report.xlsx│
               │  100 candidates  │   │  full score breakdown   │
               │  ranks + scores  │   │  skills · probe Qs      │
               └──────────────────┘   └────────────────────────┘
```

**Total runtime: ~2–3 minutes. API cost: under $1.**

Why a cascade? Sending all 487K profiles to a cloud LLM would cost ~$40,000 per run and take 6+ hours. The cascade earns the right to use LLM reasoning where it matters — the final 30 — by handling scale with efficient local models first.

---

## Scoring Dimensions

Every candidate is scored across five dimensions. Each captures something a real recruiter actually weighs.

| Dimension | Weight | What It Captures |
|-----------|--------|-----------------|
| Skill Alignment | 30% | Semantic match between candidate skills and JD requirements. Cosine similarity on 384D vectors — "Weaviate" matches "vector database" even without exact word overlap. Boosted by peer endorsement count on logarithmic scale. |
| Experience Relevance | 25% | Domain proximity, seniority fit via Gaussian banding (no hard cutoffs), academic prestige tier. |
| Career Signal | 20% | Career velocity (promotion rate relative to years of experience), tenure consistency (rewards stability, penalizes <6-month stints as attrition risk). |
| Behavioral Fit | 15% | Availability signals: open-to-work flag, notice period length, last active date, recruiter response rate. |
| Cultural Alignment | 10% | Work mode match (remote/hybrid/onsite), city tier, relocation willingness. |

---

## The 15 Pipeline Models

### Phase 1 — Fast Heuristic Filter

**Model 1 — Dual-Pass Cascade Orchestrator** `pipeline/pipeline.py`

The master controller for the entire pipeline. Implements the cascade framework: runs a lightweight O(N) heuristic scoring pass across all 487,000 candidates in seconds, selects the top ~50,000 for local semantic embedding, then selects the top 500 for multi-dimensional scoring, and finally the top 30 for LLM re-ranking. This single architectural decision reduces API cost by 99.9% compared to naive LLM-first approaches.

**Model 2 — Technical Title Classifier** `pipeline/fast_scorer.py`

Token-based classifier that evaluates the candidate's current job title and applies a score boost or penalty in the Phase 1 heuristic pass. Titles containing signals like ML, AI, Engineer, Architect, Scientist, and Lead receive boosts. Titles indicating non-technical roles — HR, Sales, Marketing, Consulting — receive penalties. Pure Python string operations, no model inference required. Processes each candidate in microseconds.

**Model 3 — Narrative Text Density Builder** `pipeline/feature_extractor.py → build_narrative()`

Before any vector embedding, all candidate fields are concatenated into one structured natural language narrative: current headline, role descriptions, education degrees, certifications, and skill tags. This maximizes information density for the encoder downstream. A sparse or incomplete narrative produces a weak embedding; this step ensures every available signal reaches the vector space. Also flags profile completeness — candidates with verified email, phone, and platform accounts receive a small completeness boost.

---

### Phase 2 — Local Semantic Embeddings

**Model 4 — SBERT Dense Vector Encoder** `pipeline/embedder.py`

Uses `sentence-transformers/all-MiniLM-L6-v2` to encode candidate narrative text and the job description into 384-dimensional dense semantic vectors. The model runs entirely locally on CPU — no API key, no network call, no data leaving the machine. At this stage both the JD and every candidate narrative exist as coordinate points in the same 384-dimensional semantic space, making meaning-based comparison mathematically tractable.

**Model 5 — Dynamic Cosine Similarity Matcher** `pipeline/scorer.py → _score_skill_alignment()`

Computes the cosine angle between the normalized JD vector and each candidate vector using NumPy matrix multiplication:

```
cosine_similarity = (A · B) / (||A|| × ||B||)
```

A score of 1.0 means identical semantic direction; 0.0 means orthogonal (unrelated). This is what allows the system to match a JD asking for "experience with retrieval systems" to candidates who worked with Elasticsearch, Faiss, Pinecone, and Milvus — without those exact words appearing in the JD. The top 500 candidates by cosine score advance to Phase 3.

---

### Phase 3 — Multi-Dimensional Scoring

**Model 6 — Seniority Gaussian Banding** `pipeline/scorer.py → _years_fit()`

Rather than hard-filtering on years of experience (which creates cliff edges and discards near-miss candidates), fits a Gaussian probability density curve centered at the JD experience midpoint:

```
f(x) = e^(-(x - μ)² / 2σ²)
```

For a role requiring 5–8 years (midpoint 6.5), a candidate with 6.5 years scores 1.0. One with 5 or 8 years scores approximately 0.85. One with 3 or 11 years scores approximately 0.4. No binary rejection — the decay is smooth and mathematically principled.

**Model 7 — Tenure Consistency Model** `pipeline/feature_extractor.py → _tenure_consistency()`

Calculates average job duration across all roles in the candidate's history. Peak score is achieved at 18+ months average tenure. Progressive decay penalizes frequent job changes, with tenures under 6 months flagged as high attrition risk. A candidate with 4 roles averaging 30 months each substantially outscores one with 10 roles averaging 8 months, controlling for total experience years.

**Model 8 — Career Velocity Tracker** `pipeline/feature_extractor.py → _career_velocity()`

Measures career trajectory by counting senior-title progressions (Senior, Lead, Principal, Staff, Manager, Director) and dividing by total years of experience. A candidate who reached Staff Engineer in 5 years scores higher on this dimension than one who held the same title for 10 years. Identifies fast-tracked talent and distinguishes upward mobility from lateral movement.

**Model 9 — Company Domain Matching Engine** `pipeline/scorer.py → _score_experience_relevance()`

Compares the industries of all prior employers against the JD's target domain. Rewards candidates from product, SaaS, fintech, AI-native, and deep-tech companies. Applies a discount for backgrounds in IT outsourcing, IT services, and generic consulting when the JD targets a product or engineering-led organization. Domain familiarity reduces onboarding friction in ways that don't appear in a resume skills list.

**Model 10 — Academic Prestige and Degree Tiering** `pipeline/scorer.py → _score_experience_relevance()`

Maps educational institutions to four prestige tiers (Tier 1: IITs, NITs, IISc; Tier 2: top private institutions; Tier 3: state universities; Tier 4: regional colleges) and weights degree levels (PhD > MTech/MS > BTech > diploma). Applied as a modest additive boost to the Experience Relevance dimension — not a filter. A self-taught candidate with exceptional career signals can still rank first.

**Model 11 — Technical Skill Endorsement Boost** `pipeline/scorer.py → _score_skill_alignment()`

Integrates LinkedIn endorsement counts as a social proof signal on top of the semantic skill alignment score. Applied with logarithmic scaling so the marginal value diminishes at high counts — the difference between 0 and 10 endorsements matters substantially more than the difference between 90 and 100. Candidates without endorsements receive no boost but also no penalty; endorsement signals are purely additive.

**Model 12 — Contextual Skill Rarity Weighting (IDF Heuristic)** `pipeline/scorer.py → _score_skill_alignment()`

Applies separate coverage scores for must-have skills and nice-to-have skills as defined in the JD. A candidate who covers all must-have skills but few nice-to-haves scores substantially higher than one who covers mostly nice-to-haves and misses requirements. Rare, non-negotiable technical requirements (e.g., a specific vector database) are weighted higher than generic skills (e.g., Python) that appear across most candidates in the pool. Mirrors how a real recruiter prioritizes a requirements list.

**Model 13 — Candidate Engagement and Availability Classifier** `pipeline/scorer.py → _score_behavioral_fit()`

Combines multiple availability signals to predict how reachable and actively interested a candidate actually is. Inputs: open-to-work flag (binary boost), notice period in days (shorter = higher score, modeled as decay function), days since last active on platform (recency decay), email and phone verification status, and historical recruiter response rate where available. A candidate who is open-to-work, was active three days ago, and has a 30-day notice period scores far higher on behavioral fit than one who hasn't engaged in six months.

**Model 14 — Work Mode and Geolocation Proximity Matcher** `pipeline/scorer.py → _score_cultural_alignment()`

Matches the candidate's stated work mode preference (remote, hybrid, onsite, flexible) against the JD's work policy. A perfect mode match scores 1.0; a mismatch scores lower with graduated penalty. Also applies a location boost for candidates residing in Tier-1 Indian technology cities (Bangalore, Pune, Noida, Hyderabad, NCR, Mumbai) for hybrid or onsite roles. Candidates outside these cities who have explicitly flagged relocation willingness receive a partial boost.

---

### Phase 4 — LLM Deep Reasoning

**Model 15 — xAI Grok Deep-Reasoning Re-ranker** `pipeline/llm_engine.py → rerank_candidates_with_llm()`

The top 30 candidates from Phase 3 are passed to xAI Grok-2-1212 via a single structured batch API call using the OpenAI-compatible interface at `https://api.xai.com/v1`. The model receives each candidate's full profile alongside the original job description. It then adjusts the final composite score based on holistic reasoning that goes beyond the structured signals, generates a 2-sentence emoji-free recruiter rationale for each candidate (mentioning specific skills and years of experience), and writes a targeted interview probe question based on the specific gap between each candidate's profile and the JD requirements.

If the Grok API returns a 4xx or 5xx error, or if no API key is configured, the pipeline automatically activates a local fallback: rationales are generated from template logic using the Phase 3 structured scores, and the submission file is produced using the Phase 3 composite scores directly. The output remains fully validator-compliant.

---

## Submission Output

`submission.csv` — 100 ranked candidates, validated against hackathon submission rules.

```
candidate_id,rank,score,reasoning
CAND_0077337,1,0.9965,"Staff Machine Learning Engineer at 7.0 yrs lands well on the JD because of Semantic Search, QLoRA, Pinecone and real production work..."
CAND_0071974,2,0.9919,"Senior AI Engineer at 7.8 yrs lands well on the JD because of LoRA, Weaviate, PEFT and real production work..."
CAND_0010257,3,0.9873,"With 6.5 yrs in senior data scientist, the strongest evidence is Milvus, TensorFlow, Python plus shipping history..."
```

**Compliance:**
- Exactly 100 rows, ranks 1–100
- Scores strictly non-increasing (0.9965 → 0.5495), normalized to `[0.2000, 0.9950]`
- Tie-breaks resolved by `candidate_id` ascending
- Zero emojis in any reasoning field
- `recruiteriq_report.xlsx`: score breakdowns per dimension, matched skills, probe questions, `#FE9EC7` header fill, autofit columns, frozen header pane

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React, Next.js 14 (App Router) | Interactive UI, client-side state, server rendering |
| Styling | TailwindCSS, custom CSS | Brand theme (`#FE9EC7`, `#89D4FF`, `#F9F6C4`, `#44ACFF`), Inter font |
| Backend | FastAPI, Python 3.10+ | Async REST API, pipeline execution |
| Local AI | PyTorch, `sentence-transformers` | Runs `all-MiniLM-L6-v2` locally — no GPU, no API key |
| Vector math | NumPy | Cosine similarity matrix operations at scale |
| Data | Pandas, OpenPyXL | Profile ingestion, CSV + Excel report generation |
| Validation | Pydantic v2 | Strict type-safe data modeling throughout pipeline |
| Cloud LLM | xAI Grok-2-1212 | Deep reasoning re-ranking for top 30 candidates only |

---

## Running Locally

**Prerequisites:** Python 3.10+, Node.js 18+

```bash
# Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r recruiteriq/requirements.txt
python api/main.py               # http://localhost:8000

# Frontend
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

Open `http://localhost:3000`. Click **Upload Dataset**, select your `.json` or `.jsonl` file. Paste a job description. Click **Analyse & Rank**.

To enable Grok re-ranking: open the **Profile** drawer (top-right), select xAI Grok-2-1212, enter your API key (`xai-...`). The pipeline runs without it — local scoring remains active as fallback.

---

## Project Structure

```
recruiteriq/
├── pipeline/
│   ├── pipeline.py            # Model 1: dual-pass cascade orchestrator
│   ├── fast_scorer.py         # Model 2: technical title classifier
│   ├── feature_extractor.py   # Models 3, 7, 8: narrative builder, tenure, velocity
│   ├── embedder.py            # Model 4: SBERT local embedding
│   ├── scorer.py              # Models 5, 6, 9–14: scoring engine
│   └── llm_engine.py          # Model 15: Grok re-ranker + local fallback
├── api/
│   └── main.py                # FastAPI server
└── requirements.txt
frontend/
├── app/                       # Next.js App Router pages
├── components/                # Candidate cards, radar charts, score panels
└── package.json
submission.csv                 # Hackathon output — 100 ranked candidates
recruiteriq_report.xlsx        # Full detailed report
```

---

## Why This Works

Three things are true simultaneously:

Semantic embeddings alone miss structured signals like tenure stability and availability. Keyword and structured scoring alone misses candidates who describe the same skills differently. LLM-only ranking is economically infeasible at 487,000 profiles.

The cascade solves all three. Local heuristics handle scale. SBERT handles semantic understanding. Structured models handle career signals. Grok handles the nuanced judgment call on the final 30. Each layer does what it is best at.

The result is a shortlist a recruiter can trust — with a specific, written explanation for every rank.

---

*Built for the India Runs Data & AI Challenge — Redrob Hackathon*
