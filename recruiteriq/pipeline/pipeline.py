"""Main pipeline orchestrator — ties all stages together."""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Callable, Dict
import json
import csv

from .candidate_loader import load_candidates, stream_jsonl, count_lines
from .feature_extractor import enrich_candidate
from .jd_parser import parse_jd
from .embedder import embed_text, embed_batch, cosine_similarity_matrix
from .scorer import build_ranked_candidate
from .rationale_builder import enrich_with_rationale
from ..models.schemas import JobDescriptionProfile, CandidateProfile, RankedCandidate, SkillRequirement
from ..config import FAST_PATH_TOP_N, SHORTLIST_SIZE


def run_pipeline(
    jd_text: str,
    candidates_path: Path,
    shortlist_size: int = SHORTLIST_SIZE,
    on_progress: Optional[Callable[[str, float], None]] = None,
    llm_provider: Optional[str] = None,
    api_key: Optional[str] = None,
) -> tuple[JobDescriptionProfile, List[RankedCandidate]]:
    """
    Full pipeline:
    1. Parse JD (Heuristic or LLM)
    2. Stream + enrich candidates (feature extraction)
    3. Fast-path pure-Python scoring → top-N candidates
    4. Embed JD + top candidates → semantic similarity
    5. Multi-dim scoring with semantic sim
    6. LLM Re-ranking of top 30 (or Local template fallback)
    7. Return sorted ranked list
    """
    def progress(msg: str, pct: float):
        if on_progress:
            on_progress(msg, pct)

    # ── Step 1: Parse JD ─────────────────────────────────────────────────────
    use_llm = llm_provider and llm_provider != "none" and api_key
    
    if use_llm:
        progress(f"🔍 Understanding your job description with {llm_provider.upper()} LLM...", 0.05)
        try:
            from .llm_engine import parse_jd_with_llm
            parsed = parse_jd_with_llm(jd_text, llm_provider, api_key)
            
            # Map parsed JSON dict to JobDescriptionProfile
            must_skills = [SkillRequirement(name=s) for s in parsed.get("must_have_skills", [])]
            nice_skills = [SkillRequirement(name=s) for s in parsed.get("nice_to_have_skills", [])]
            
            jd = JobDescriptionProfile(
                raw_text=jd_text,
                role_title=parsed.get("role_title", "Unknown Role"),
                seniority_level=parsed.get("seniority_level", "mid"),
                seniority_years_min=parsed.get("seniority_years_min"),
                seniority_years_max=parsed.get("seniority_years_max"),
                work_mode=parsed.get("work_mode", "hybrid"),
                domain_industry=parsed.get("domain_industry", []),
                must_have_skills=must_skills,
                nice_to_have_skills=nice_skills,
                behavioral_signals=parsed.get("behavioral_signals", []),
                cultural_signals=parsed.get("cultural_signals", []),
                role_intent_summary=parsed.get("role_intent_summary", ""),
            )
            
            # Build embedding text
            from .jd_parser import _build_embedding_text
            jd.embedding_text = _build_embedding_text(jd)
            
        except Exception as e:
            print(f"LLM JD parsing failed: {e}. Falling back to local heuristics.")
            progress("🔍 LLM parsing failed; falling back to local parsing...", 0.05)
            jd = parse_jd(jd_text)
    else:
        progress("🔍 Understanding your job description (local heuristics)...", 0.05)
        jd = parse_jd(jd_text)

    # ── Step 2: Fast-path scoring (pure Python, no embedding) ────────────────
    progress("📂 Loading and scoring candidates...", 0.10)

    # Import rank_candidates scoring logic
    from .fast_scorer import fast_score_candidate

    scored_pool: List[tuple[float, CandidateProfile]] = []

    for i, candidate in enumerate(load_candidates(candidates_path)):
        enrich_candidate(candidate)
        fast_score = fast_score_candidate(candidate, jd)

        # Keep top-FAST_PATH_TOP_N efficiently using a list + sort
        scored_pool.append((fast_score, candidate))

        if i % 1000 == 0 and i > 0:
            # Trim pool to save memory
            scored_pool.sort(key=lambda x: -x[0])
            scored_pool = scored_pool[:FAST_PATH_TOP_N]
            progress(f"📂 Scoring candidates... {i:,} processed", 0.10 + 0.30 * min(i / 50000, 1.0))

    # Final trim
    scored_pool.sort(key=lambda x: -x[0])
    top_candidates = [c for _, c in scored_pool[:FAST_PATH_TOP_N]]

    progress(f"✅ Shortlisted top {len(top_candidates)} candidates for deep analysis", 0.45)

    # ── Step 3: Embed JD + top candidates ────────────────────────────────────
    progress("🧠 Computing semantic similarity...", 0.50)

    jd_vec = embed_text(jd.embedding_text)
    narratives = [c.narrative_text for c in top_candidates]
    candidate_vecs = embed_batch(narratives, batch_size=64)

    # Cosine similarity for each candidate
    sim_scores = (candidate_vecs @ jd_vec).tolist()

    progress("🎯 Running multi-dimensional scoring...", 0.75)

    # ── Step 4: Multi-dimensional scoring ────────────────────────────────────
    ranked: List[RankedCandidate] = []
    for candidate, semantic_sim in zip(top_candidates, sim_scores):
        rc = build_ranked_candidate(candidate, jd, rank=0, semantic_sim=float(semantic_sim))
        ranked.append(rc)

    # Sort by composite score
    ranked.sort(key=lambda r: -r.scores.composite)

    # Take final shortlist
    ranked = ranked[:shortlist_size]

    # Assign ranks
    for i, rc in enumerate(ranked, start=1):
        rc.rank = i

    # ── Step 5: LLM Re-ranking of top 30 ─────────────────────────────────────
    llm_reranked_ids = set()
    if use_llm:
        progress(f"📝 Re-ranking top candidates with {llm_provider.upper()}...", 0.90)
        try:
            from .llm_engine import rerank_candidates_with_llm
            # Convert top 30 to dicts
            top30 = [json.loads(rc.model_dump_json()) for rc in ranked[:30]]
            jd_dict = json.loads(jd.model_dump_json())
            
            reranked_data = rerank_candidates_with_llm(jd_dict, top30, llm_provider, api_key)
            
            # Create mapping
            rerank_map = {item["candidate_id"]: item for item in reranked_data}
            
            # Update ranked scores
            for rc in ranked:
                if rc.candidate_id in rerank_map:
                    item = rerank_map[rc.candidate_id]
                    rc.scores.composite = float(item["new_score"])
                    rc.recruiter_rationale = str(item["recruiter_rationale"])
                    rc.probe_question = str(item["interview_probe"])
                    llm_reranked_ids.add(rc.candidate_id)
            
            # Sort full list again with updated LLM scores
            ranked.sort(key=lambda r: -r.scores.composite)
            for i, rc in enumerate(ranked, start=1):
                rc.rank = i
                
        except Exception as e:
            print(f"LLM re-ranking failed: {e}. Falling back to local rationales.")
            progress("⚠️ LLM re-ranking failed; using local heuristics...", 0.90)

    # Add local/fallback rationale & strengths for anyone not processed by LLM
    progress("📝 Finalizing candidate rationales...", 0.95)
    for rc in ranked:
        if rc.candidate_id not in llm_reranked_ids:
            enrich_with_rationale(rc, jd)

    progress("✅ Done! Your ranked shortlist is ready.", 1.0)
    return jd, ranked



def export_to_csv(
    ranked: List[RankedCandidate],
    output_path: Path,
) -> Path:
    """Export ranked candidates to CSV in hackathon submission format."""
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        for rc in ranked:
            writer.writerow(rc.to_csv_row())
    return output_path
