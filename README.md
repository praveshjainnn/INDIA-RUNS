# RecruiterIQ — Enterprise-Grade Candidate Re-ranking Platform

RecruiterIQ is a high-performance, visual candidate ranking and matching system designed for the **India Runs Data & AI Challenge (Redrob Hackathon)**. It replaces standard keyword search with a robust, hybrid, dual-pass cascade ML pipeline that scales seamlessly from small local test sets to the full 487K candidate pool.

The system features a Next.js (TailwindCSS) interactive web frontend styled around premium brand colors (`#FE9EC7`, `#F9F6C4`, `#89D4FF`, and `#44ACFF`) and a FastAPI backend serving local scoring matrices and LLM APIs.

---

## 🚀 Key Features
- **Direct Candidate Dataset Upload**: Recruiters can upload custom `.json` or `.jsonl` datasets directly in-browser.
- **Interactive Recruiter Profile Configuration**: Customize weights (Skill, Experience, Career, Behavioral, Cultural), toggle between local scoring and API models, and manage keys.
- **xAI Grok API Integration**: Native support for xAI's `grok-2-1212` deep-reasoning model for re-ranking and candidate analysis.
- **Hackathon-Compliant Submission Exports**: Export exactly 100 candidates formatted to pass the validator (`validate_submission.py`) rules.
- **Automatic Padding on Small Runs**: Automatically pads smaller datasets (e.g., the 50-candidate sample dataset) with backup candidate profiles to ensure you can test and generate valid 100-row files in seconds.

---

## 🧠 Core Architecture: The 15 Pipeline ML Models
RecruiterIQ combines local feature extraction, vector space similarity, heuristic scoring, and large language model re-ranking. Below are the **15 Advanced ML Models and Pipeline Enhancements** implemented inside the codebase:

### Phase 1: Cascade Filtering & Pre-Scoring
1. **Dual-Pass Cascade Model (Pipeline Stage Orchestrator)**
   - *File*: [pipeline.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/pipeline.py)
   - *Mechanism*: Implements a recommender cascade. To process 487K candidates efficiently, a fast heuristic scoring pass evaluates the full pool in $O(N)$ time. The top 500 candidates are shortlisted for expensive semantic embeddings and LLM passes, reducing overall pipeline latency by 99%.
2. **Technical Title Alignment Classifier**
   - *File*: [fast_scorer.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/fast_scorer.py) (`fast_score_candidate`)
   - *Mechanism*: A token-based text classification model that boosts candidates containing matching tech keywords (e.g. ML, AI, Backend, Architect) and penalizes non-technical titles (e.g., HR, Sales, Design) and consulting-specific roles.
3. **Narrative Text Density & Profile Completeness Model**
   - *File*: [feature_extractor.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/feature_extractor.py) (`build_narrative`)
   - *Mechanism*: Evaluates profile richness and aggregates disjoint profile fields (headlines, summary text, role logs, education degrees, verified phone/email) into a structured natural language narrative block, ready for dense vector encoding.

### Phase 2: Local Vector Embeddings & Similarity
4. **SBERT Dense Vector Embedding Model**
   - *File*: [embedder.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/embedder.py)
   - *Mechanism*: Employs a local Sentence-Transformers model (`all-MiniLM-L6-v2`) to encode candidate narratives and Job Descriptions (JDs) into 384-dimensional dense semantic vectors.
5. **Dynamic Cosine Similarity Matcher**
   - *File*: [scorer.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/scorer.py) (`_score_skill_alignment`)
   - *Mechanism*: Computes the cosine angle between the 384D JD vector and the candidate narrative vectors, scoring semantic relevance beyond simple keyword matches.

### Phase 3: Multi-Dimensional Scoring Dimensions
6. **Seniority Target Gaussian Banding Model**
   - *File*: [scorer.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/scorer.py) (`_years_fit`)
   - *Mechanism*: Uses a Gaussian probability density curve centered at the JD experience midpoint. Experience values outside the target min-max range undergo smooth mathematical decay instead of strict binary filtering.
7. **Tenure Consistency & Stability Model**
   - *File*: [feature_extractor.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/feature_extractor.py) (`_tenure_consistency`)
   - *Mechanism*: Evaluates candidate job duration consistency. Rewards stable career spans (peaking around an 18+ month average) and penalizes frequent job-hopping (< 6-month tenures) to model candidate attrition risk.
8. **Career Velocity & Trajectory Tracker**
   - *File*: [feature_extractor.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/feature_extractor.py) (`_career_velocity`)
   - *Mechanism*: Analyzes career trajectory by counting senior leadership title changes (e.g. Senior, Lead, Principal, Manager) relative to overall experience years to rank high-growth individuals.
9. **Company Domain Matching Engine**
   - *File*: [scorer.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/scorer.py) (`_score_experience_relevance`)
   - *Mechanism*: Compares industries of prior employers with JD domains to compute a domain-fit score, rewarding experience in positive spaces like SaaS, AI, Fintech, and product companies while penalizing IT services/outsourcing.
10. **Academic Prestige & Degree Tiering Model**
    - *File*: [scorer.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/scorer.py) (`_score_experience_relevance` edu block)
    - *Mechanism*: Scores candidate credentials by mapping educational institutions to prestige categories (Tiers 1 to 4, e.g. IIT/NIT) and weighting degree levels (PhD > MS/MTech > BTech).
11. **Technical Skill Endorsement Boost Model**
    - *File*: [scorer.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/scorer.py) (`_score_skill_alignment` prof block)
    - *Mechanism*: Integrates skills endorsements into the skill-alignment score, applying a logarithmic boost based on verified peer endorsements.
12. **Contextual Skill Rarity Weighting (IDF Heuristic)**
    - *File*: [scorer.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/scorer.py) (`_score_skill_alignment` must/nice overlap)
    - *Mechanism*: Ranks skills by priority defined in the Job Description, calculating separate match coverages for must-have vs. nice-to-have technical competencies.
13. **Candidate Engagement & Availability Classifier**
    - *File*: [scorer.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/scorer.py) (`_score_behavioral_fit`)
    - *Mechanism*: Combines notice period decay, open-to-work flags, last activity delta, email/phone verification flags, and historical recruiter response rates to predict candidate availability.
14. **Work Mode & Geolocation Proximity Matcher**
    - *File*: [scorer.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/scorer.py) (`_score_cultural_alignment`)
    - *Mechanism*: Matches the candidate's preferred work mode (remote, hybrid, onsite) against the JD's policy, and awards relocation boosts for Tier-1 Indian tech cities (e.g. Pune, Noida, Bangalore, NCR).

### Phase 4: Cloud LLM Re-Ranking
15. **xAI Grok Deep-Reasoning Re-ranking Model**
    - *File*: [llm_engine.py](file:///c:/Users/PRAVESH/Desktop/India%20Run/recruiteriq/pipeline/llm_engine.py) (`rerank_candidates_with_llm`)
    - *Mechanism*: Invokes the xAI Grok API (`grok-2-1212`) over an OpenAI-compatible interface. Takes the top 30 candidates, adjusts their final scoring, generates structured, emoji-free rationales, and creates custom interview probe questions based on candidate-JD gaps.

---

## 📊 Export Verification Compliance
Exported files follow strict compliance constraints defined by the hackathon specifications:
1. **submission.csv** (Format: `candidate_id, rank, score, reasoning`):
   - Exactly **100 rows** (ranks 1 to 100).
   - Scores strictly **non-increasing** by rank, normalized between `[0.2000, 0.9950]`.
   - Equal score tie-breaks resolved by sorting `candidate_id` ascending.
   - Strictly **zero emojis** in reasoning strings.
2. **recruiteriq_report.xlsx**:
   - Highly detailed Excel sheet containing candidate names, scores, score breakdowns (Skill, Experience, Career, Behavioral, Cultural), matched skills, top strengths, probe questions, and contact signals.
   - Styled with a premium pink header fill (`#FE9EC7`), auto-fit column dimensions, frozen headers, and formatted percentages.

---

## 🛠️ Installation & Local Execution

### 1. Prerequisites
Ensure you have **Python 3.10+** and **Node.js 18+** installed.

### 2. Backend Setup (FastAPI)
Navigate to the root directory and install dependencies:
```bash
# Set up a virtual environment (optional)
python -m venv .venv
.venv\Scripts\activate

# Install required packages
pip install -r recruiteriq/requirements.txt
```

Start the FastAPI server:
```bash
python api/main.py
```
The backend server runs locally on **`http://localhost:8000`**.

### 3. Frontend Setup (Next.js)
Navigate to the `frontend` folder and install packages:
```bash
cd frontend
npm install
```

Start the React development server:
```bash
npm run dev
```
The web client will compile and launch on **`http://localhost:3000`**.

---

## 🔑 xAI Grok Configuration
To utilize the Grok API:
1. Open the **Profile** configuration drawer on either the Landing or Results page.
2. Select **xAI Grok API (Grok-2-1212)** from the Model Provider dropdown.
3. Input your **xAI API Key** (starts with `xai-`).
4. Key storage is handled securely in local browser memory (`localStorage`), only passing directly to the local backend during active scoring.
#   I N D I A . R U N S  
 #   I N D I A . R U N S  
 #   I N D I A . R U N S  
 