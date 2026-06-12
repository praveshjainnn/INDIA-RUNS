"""RecruiterIQ — Main Streamlit Application
AI-powered candidate ranking for the India Runs Data & AI Challenge.
Zero API costs: 100% local, free, runs on any laptop.
"""
from __future__ import annotations
import sys
import io
import json
import csv
import time
from pathlib import Path

import streamlit as st
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from recruiteriq.config import (
    CANDIDATES_JSONL, SAMPLE_CANDIDATES, SHORTLIST_SIZE, DISPLAY_DEFAULT
)
from recruiteriq.ui.components import (
    render_header, render_jd_panel, render_candidate_card,
    render_metrics_bar, render_processing_state, render_radar_chart,
)
from recruiteriq.pipeline.jd_parser import parse_jd
from recruiteriq.pipeline.candidate_loader import load_candidates
from recruiteriq.pipeline.feature_extractor import enrich_candidate
from recruiteriq.pipeline.fast_scorer import fast_score_candidate
from recruiteriq.pipeline.embedder import embed_text, embed_batch
from recruiteriq.pipeline.scorer import build_ranked_candidate
from recruiteriq.pipeline.rationale_builder import enrich_with_rationale
from recruiteriq.models.schemas import JobDescriptionProfile, RankedCandidate

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RecruiterIQ — AI Candidate Ranking",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject CSS ────────────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "ui" / "styles.css"
if css_path.exists():
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Sample JD ─────────────────────────────────────────────────────────────────
SAMPLE_JD = """Senior AI/ML Engineer — Search & Ranking

We're building the next generation of intelligent search and recommendation systems at scale.
You will own the full ML lifecycle: from designing ranking models and evaluation frameworks
to shipping production services serving millions of users.

Requirements:
- 5+ years of experience in Machine Learning or AI Engineering
- Strong Python skills with PyTorch or TensorFlow
- Hands-on experience with embeddings, semantic search, vector databases (Faiss, Milvus, Qdrant)
- Experience building and deploying retrieval or ranking systems in production
- Familiarity with LLMs, RAG, fine-tuning (LoRA, PEFT)
- Experience with evaluation metrics: NDCG, MRR, A/B testing
- BM25, Elasticsearch, OpenSearch experience is a plus

Nice to Have:
- Kafka, Airflow for feature pipelines
- MLflow or similar for experiment tracking
- Experience at a product company (not consulting/IT services)

We value: ownership, cross-functional collaboration, scale mindset, data-driven decisions.
Location: Pune or Noida preferred. Hybrid work model. Open to remote for exceptional candidates.
"""


# ── State helpers ─────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "screen": "landing",         # landing | jd_review | results
        "jd_text": "",
        "jd_profile": None,
        "ranked": None,
        "total_candidates": 0,
        "candidates_file": None,
        "display_count": DISPLAY_DEFAULT,
        "use_sample": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_to_landing():
    st.session_state.screen = "landing"
    st.session_state.ranked = None
    st.session_state.jd_profile = None
    st.session_state.total_candidates = 0


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_full_pipeline(jd_text: str, candidates_path: Path, progress_bar, status_text) -> tuple:
    """Run pipeline with Streamlit progress updates."""
    from recruiteriq.config import FAST_PATH_TOP_N

    STEPS = [
        "🔍 Parsing job description...",
        "📂 Fast-scoring all candidates...",
        "🧠 Embedding top candidates (semantic similarity)...",
        "🎯 Multi-dimensional scoring...",
        "📝 Generating rationale & probe questions...",
    ]

    def update(msg: str, pct: float):
        progress_bar.progress(min(pct, 0.99))
        status_text.markdown(f"**{msg}**")

    update(STEPS[0], 0.05)
    jd = parse_jd(jd_text)

    update(STEPS[1], 0.10)
    scored_pool = []
    total = 0

    for candidate in load_candidates(candidates_path):
        enrich_candidate(candidate)
        fast_score = fast_score_candidate(candidate, jd)
        scored_pool.append((fast_score, candidate))
        total += 1

        if total % 2000 == 0:
            # Trim to save memory
            scored_pool.sort(key=lambda x: -x[0])
            scored_pool = scored_pool[:FAST_PATH_TOP_N]
            pct = 0.10 + 0.35 * min(total / 100000, 1.0)
            update(f"📂 Scored {total:,} candidates... (top {len(scored_pool)} kept)", pct)

    scored_pool.sort(key=lambda x: -x[0])
    top_candidates = [c for _, c in scored_pool[:FAST_PATH_TOP_N]]

    update(STEPS[2], 0.50)
    jd_vec = embed_text(jd.embedding_text)
    narratives = [c.narrative_text for c in top_candidates]
    candidate_vecs = embed_batch(narratives, batch_size=64, show_progress=False)
    sim_scores = (candidate_vecs @ jd_vec).tolist()

    update(STEPS[3], 0.75)
    ranked = []
    for candidate, sim in zip(top_candidates, sim_scores):
        rc = build_ranked_candidate(candidate, jd, rank=0, semantic_sim=float(sim))
        ranked.append(rc)

    ranked.sort(key=lambda r: -r.scores.composite)
    ranked = ranked[:SHORTLIST_SIZE]
    for i, rc in enumerate(ranked, 1):
        rc.rank = i

    update(STEPS[4], 0.90)
    for rc in ranked:
        enrich_with_rationale(rc, jd)

    update("✅ Analysis complete!", 1.0)
    return jd, ranked, total


# ── Screens ───────────────────────────────────────────────────────────────────

def screen_landing():
    render_header()

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        use_sample = st.toggle("Use sample dataset (fast, ~100 candidates)", value=True)
        st.session_state.use_sample = use_sample

        if not use_sample:
            uploaded = st.file_uploader(
                "Upload candidate file (.jsonl or .json)",
                type=["jsonl", "json"],
                help="Upload candidates.jsonl for the full dataset, or sample_candidates.json for testing",
            )
            if uploaded:
                # Save to temp
                tmp_path = Path(__file__).parent / "_uploaded_candidates.jsonl"
                tmp_path.write_bytes(uploaded.read())
                st.session_state.candidates_file = str(tmp_path)
                st.success(f"✅ File uploaded: {uploaded.name}")

        st.markdown("---")
        st.markdown("""
        **📊 How it works:**
        1. Parse JD → extract skills & intent
        2. Score all candidates (Python)
        3. Embed top-500 → semantic similarity
        4. Multi-dim scoring (5 dimensions)
        5. Generate rationale & probe questions
        """)
        st.markdown("---")
        st.markdown("**🔒 100% Local & Free**  \nNo API keys. No data leaves your machine.")

    # Main content
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown("### 📋 Paste Your Job Description")
        jd_text = st.text_area(
            label="Job Description",
            value=st.session_state.jd_text or SAMPLE_JD,
            height=380,
            placeholder="Paste any job description here — the more detail, the better the results.",
            label_visibility="collapsed",
        )
        st.session_state.jd_text = jd_text

        word_count = len(jd_text.split())
        if word_count < 50:
            st.warning("⚠️ Add more detail for better results (ideally 100+ words)")
        else:
            st.caption(f"✅ {word_count} words · Ready to analyse")

        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            analyse = st.button(
                "🚀 Analyse & Rank Candidates",
                type="primary",
                use_container_width=True,
                disabled=(word_count < 30),
            )
        with col_btn2:
            if st.button("🔄 Use Sample JD", use_container_width=True):
                st.session_state.jd_text = SAMPLE_JD
                st.rerun()

    with col_right:
        st.markdown("### 💡 What RecruiterIQ does")
        st.markdown("""
        <div class="riq-card animate-in">
        <strong>🔍 Semantic Understanding</strong><br>
        <span style="color:#6B7280; font-size:0.875rem">Goes beyond keywords — understands <em>intent</em> of the JD and candidate profiles.</span>
        </div>
        <div class="riq-card animate-in">
        <strong>📊 5-Dimensional Scoring</strong><br>
        <span style="color:#6B7280; font-size:0.875rem">Skill Alignment · Experience · Career Signal · Behavioral · Cultural</span>
        </div>
        <div class="riq-card animate-in">
        <strong>🧠 Explainable Results</strong><br>
        <span style="color:#6B7280; font-size:0.875rem">Every rank comes with a recruiter rationale and a targeted interview probe question.</span>
        </div>
        <div class="riq-card animate-in">
        <strong>⚡ 100% Free & Local</strong><br>
        <span style="color:#6B7280; font-size:0.875rem">Sentence-transformers run on your CPU. No API costs, no data leaves your machine.</span>
        </div>
        """, unsafe_allow_html=True)

    # Run pipeline when button clicked
    if analyse:
        if use_sample and not SAMPLE_CANDIDATES.exists():
            st.error(f"❌ Sample file not found at: {SAMPLE_CANDIDATES}")
            return

        candidates_path = (
            SAMPLE_CANDIDATES if use_sample
            else Path(st.session_state.candidates_file or str(CANDIDATES_JSONL))
        )

        st.markdown("---")
        st.markdown("### ⚙️ Running Analysis...")
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            with st.spinner(""):
                jd, ranked, total = run_full_pipeline(
                    jd_text, candidates_path, progress_bar, status_text
                )
            st.session_state.jd_profile = jd
            st.session_state.ranked = ranked
            st.session_state.total_candidates = total
            st.session_state.screen = "jd_review"
            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error during analysis: {e}")
            st.exception(e)


def screen_jd_review():
    render_header()

    jd: JobDescriptionProfile = st.session_state.jd_profile
    ranked: list = st.session_state.ranked

    st.markdown("## ✅ Step 1: Confirm JD Understanding")
    st.markdown("*Review what the system extracted from your job description before seeing the ranked results.*")

    col_jd, col_btn = st.columns([3, 1])
    with col_jd:
        render_jd_panel(jd)

    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("✅ Looks right → Show me candidates", type="primary", use_container_width=True):
            st.session_state.screen = "results"
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✏️ Edit JD & Re-analyse", use_container_width=True):
            reset_to_landing()
            st.rerun()

    # Show preview
    if ranked:
        st.markdown("---")
        st.markdown(f"**Preview:** Found **{len(ranked)}** ranked candidates from {st.session_state.total_candidates:,} total")
        preview_cols = st.columns(3)
        for i, rc in enumerate(ranked[:3]):
            with preview_cols[i]:
                tier_color = {"strong_match": "#22C55E", "good_match": "#4F6EF7",
                              "possible": "#F59E0B", "stretch": "#9CA3AF"}.get(rc.score_tier, "#9CA3AF")
                st.markdown(f"""
                <div class="metric-card animate-in">
                    <span style="font-size:1.3rem; font-weight:700; color:{tier_color}">#{rc.rank} · {rc.scores.composite:.1f}</span>
                    <div style="font-weight:600; font-size:0.9rem; margin-top:0.3rem">{rc.name or rc.candidate_id}</div>
                    <div style="font-size:0.75rem; color:#6B7280">{rc.current_title}</div>
                </div>""", unsafe_allow_html=True)


def screen_results():
    jd: JobDescriptionProfile = st.session_state.jd_profile
    ranked: list[RankedCandidate] = st.session_state.ranked
    total = st.session_state.total_candidates

    # Sidebar — JD panel + controls
    with st.sidebar:
        render_jd_panel(jd)
        st.markdown("---")

        display_n = st.slider("Show top N candidates", 5, min(len(ranked), 100), DISPLAY_DEFAULT, 5)
        st.session_state.display_count = display_n

        st.markdown("---")
        if st.button("🔁 Re-analyse with new JD", use_container_width=True):
            reset_to_landing()
            st.rerun()

    # Main area
    render_header()

    st.markdown(f"## 📊 Ranked Shortlist — {len(ranked)} candidates from {total:,} total")
    st.markdown("*Ranked by composite AI score across 5 dimensions. Click any card to expand.*")

    # Metrics bar
    render_metrics_bar(ranked, total)

    # Filter controls
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        tier_filter = st.multiselect(
            "Filter by tier",
            ["strong_match", "good_match", "possible", "stretch"],
            default=["strong_match", "good_match", "possible", "stretch"],
            format_func=lambda x: {"strong_match": "✅ Strong Match", "good_match": "🔵 Good Match",
                                   "possible": "🟡 Possible", "stretch": "⚪ Stretch"}.get(x, x),
        )
    with col_f2:
        sort_by = st.selectbox(
            "Sort by",
            ["Composite Score", "Skill Alignment", "Experience", "Career Signal"],
        )
    with col_f3:
        search_name = st.text_input("🔍 Search by name/ID", placeholder="e.g. CAND_0001234")

    # Apply filters
    display_ranked = ranked[:display_n]
    if tier_filter:
        display_ranked = [r for r in display_ranked if r.score_tier in tier_filter]
    if search_name:
        q = search_name.lower()
        display_ranked = [r for r in display_ranked
                          if q in (r.name or "").lower() or q in r.candidate_id.lower()]

    # Sort
    sort_key_map = {
        "Composite Score": lambda r: -r.scores.composite,
        "Skill Alignment": lambda r: -r.scores.skill_alignment,
        "Experience": lambda r: -r.scores.experience_relevance,
        "Career Signal": lambda r: -r.scores.career_signal,
    }
    display_ranked.sort(key=sort_key_map.get(sort_by, lambda r: -r.scores.composite))

    if not display_ranked:
        st.info("No candidates match the current filters.")
    else:
        # Render cards
        for rc in display_ranked:
            render_candidate_card(rc, jd)

    # Export section
    st.markdown("---")
    col_exp1, col_exp2, col_exp3 = st.columns(3)

    with col_exp1:
        # Hackathon submission format CSV
        csv_rows = [rc.to_csv_row() for rc in ranked]
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        writer.writerows(csv_rows)
        st.download_button(
            label="⬇️ Download Submission CSV",
            data=csv_buf.getvalue(),
            file_name=f"recruiteriq_submission_{jd.role_title.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

    with col_exp2:
        # Full detailed CSV
        detailed_rows = []
        for rc in ranked:
            detailed_rows.append({
                "rank": rc.rank,
                "candidate_id": rc.candidate_id,
                "name": rc.name,
                "composite_score": rc.scores.composite,
                "skill_alignment": rc.scores.skill_alignment,
                "experience_relevance": rc.scores.experience_relevance,
                "career_signal": rc.scores.career_signal,
                "behavioral_fit": rc.scores.behavioral_fit,
                "cultural_alignment": rc.scores.cultural_alignment,
                "score_tier": rc.score_tier,
                "current_title": rc.current_title,
                "current_company": rc.current_company,
                "total_experience_years": rc.total_experience_years,
                "top_strength": rc.top_strength,
                "probe_question": rc.probe_question,
                "recruiter_rationale": rc.recruiter_rationale,
            })
        df = pd.DataFrame(detailed_rows)
        st.download_button(
            label="⬇️ Full Detailed Report",
            data=df.to_csv(index=False),
            file_name=f"recruiteriq_full_{jd.role_title.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_exp3:
        st.caption(f"📄 {len(ranked)} candidates ranked | Submission format: candidate_id, rank, score, reasoning")
        st.caption(f"🎯 Role: **{jd.role_title}** · {jd.work_mode.title()} · {jd.seniority_level.title()}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    init_state()

    screen = st.session_state.screen
    if screen == "landing":
        screen_landing()
    elif screen == "jd_review":
        screen_jd_review()
    elif screen == "results":
        screen_results()
    else:
        screen_landing()


if __name__ == "__main__":
    main()
