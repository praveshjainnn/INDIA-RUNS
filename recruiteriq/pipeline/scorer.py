"""Multi-dimensional scorer for RecruiterIQ.
Extends and integrates with logic from rank_candidates.py.
Produces 5-dimensional scores plus a composite, all 0–100.
"""
from __future__ import annotations
import math
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from ..config import WEIGHTS, THRESHOLDS, TECH_SKILLS, TIER1_CITIES
from ..models.schemas import (
    CandidateProfile, JobDescriptionProfile, RankedCandidate, ScoreBreakdown,
)

_TODAY = date(2026, 6, 12)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _saturate(value: float, scale: float) -> float:
    if value <= 0:
        return 0.0
    return 1.0 - math.exp(-value / scale)


def _lower(*parts: str) -> str:
    return " ".join(p for p in parts if p).lower()


def _phrase_hits(text: str, phrases) -> int:
    return sum(1 for p in phrases if p in text)


# ── Dimension 1: Skill Alignment (30%) ───────────────────────────────────────

def _score_skill_alignment(
    candidate: CandidateProfile,
    jd: JobDescriptionProfile,
    semantic_sim: float,
) -> Tuple[float, List[str]]:
    """
    Blend semantic similarity with skill-level matching.
    Returns (score 0-1, matched_skills).
    """
    # Collect JD skill names (lower)
    jd_must = {s.name.lower() for s in jd.must_have_skills}
    jd_nice = {s.name.lower() for s in jd.nice_to_have_skills}
    jd_all_skills = jd_must | jd_nice

    # Also build a text blob of the JD for phrase matching
    jd_text = _lower(jd.raw_text, jd.role_intent_summary)

    # Candidate skill names + history text
    cand_skills_lower = {s.name.lower() for s in candidate.skills}
    history_text = _lower(
        *[e.description for e in candidate.career_history],
        candidate.summary, candidate.headline,
    )

    # Direct skill name overlap
    matched_must = cand_skills_lower & jd_must
    matched_nice = cand_skills_lower & jd_nice
    must_coverage = len(matched_must) / max(len(jd_must), 1)
    nice_coverage = len(matched_nice) / max(len(jd_nice), 1)

    # Tech skill phrase matching in work history
    tech_phrase_hits = 0
    matched_in_history: List[str] = []
    for skill in TECH_SKILLS:
        if skill in jd_text and skill in history_text:
            tech_phrase_hits += 1
            matched_in_history.append(skill)

    phrase_score = _clamp(_saturate(tech_phrase_hits, 5.0))

    # Proficiency weighting for matched skills
    prof_weights = {"beginner": 0.4, "intermediate": 0.65, "advanced": 0.85, "expert": 1.0}
    prof_score = 0.0
    for sk in candidate.skills:
        if sk.name.lower() in jd_all_skills:
            w = prof_weights.get(sk.proficiency, 0.5)
            # Endorsement boost
            endorsement_boost = _clamp(sk.endorsements / 30) * 0.1
            prof_score += w + endorsement_boost
    prof_score = _clamp(_saturate(prof_score, 3.0))

    # Skill assessment bonus
    assessment_bonus = 0.0
    assessment = candidate.redrob_signals.skill_assessment_scores
    for skill_name, score in assessment.items():
        if skill_name.lower() in jd_all_skills and score > 0:
            assessment_bonus += 0.05 * _clamp(score / 100)
    assessment_bonus = _clamp(assessment_bonus, 0, 0.15)

    # Blend
    raw = (
        0.40 * semantic_sim +           # semantic embedding similarity
        0.25 * must_coverage +          # direct must-have skill match
        0.15 * phrase_score +           # tech phrases in work history
        0.12 * prof_score +             # proficiency-weighted
        0.05 * nice_coverage +          # nice-to-have coverage
        assessment_bonus
    )

    all_matched = list(matched_must | matched_nice | set(matched_in_history[:5]))
    return _clamp(raw), all_matched[:8]


# ── Dimension 2: Experience Relevance (25%) ───────────────────────────────────

def _years_fit(years: float, jd: JobDescriptionProfile) -> float:
    """Gaussian around the target seniority band."""
    target_min = jd.seniority_years_min or 3
    target_max = jd.seniority_years_max or 8
    target_mid = (target_min + target_max) / 2
    sigma = max((target_max - target_min) / 2, 2)
    if years < 0:
        return 0.0
    return math.exp(-((years - target_mid) ** 2) / (2 * sigma ** 2))


def _score_experience_relevance(
    candidate: CandidateProfile,
    jd: JobDescriptionProfile,
) -> float:
    yoe = candidate.years_of_experience
    years_score = _years_fit(yoe, jd)

    # Domain match
    jd_industries = {d.lower() for d in jd.domain_industry}
    cand_industries = {e.industry.lower() for e in candidate.career_history if e.industry}
    cand_industries.add(candidate.current_industry.lower())

    positive_overlap = sum(
        1 for ci in cand_industries
        if any(ji in ci or ci in ji for ji in jd_industries)
    )
    domain_score = _clamp(_saturate(positive_overlap, 2.0))

    # Industry quality
    pos_hist = sum(1 for ci in cand_industries
                   if any(pos in ci for pos in
                          {"software","technology","internet","saas","fintech",
                           "ai","machine learning","data","analytics","product"}))
    neg_hist = sum(1 for ci in cand_industries
                   if any(neg in ci for neg in
                          {"it services","outsourcing","consulting","manufacturing","paper"}))
    industry_quality = _clamp(_saturate(pos_hist, 2.0) - 0.3 * _saturate(neg_hist, 2.0))

    # Education tier
    edu_score = 0.3
    for edu in candidate.education:
        tier_scores = {"tier_1": 1.0, "tier_2": 0.8, "tier_3": 0.6, "tier_4": 0.45, "unknown": 0.3}
        edu_score = max(edu_score, tier_scores.get(edu.tier, 0.3))

    raw = (
        0.35 * years_score +
        0.30 * domain_score +
        0.20 * industry_quality +
        0.15 * edu_score
    )
    return _clamp(raw)


# ── Dimension 3: Career Signal (20%) ─────────────────────────────────────────

RELEVANT_PHRASES = {
    "embeddings", "vector", "retrieval", "search", "ranking", "recommendation",
    "semantic", "llm", "fine-tuning", "rag", "production", "deployed", "shipped",
    "scale", "pipeline", "feature", "model", "inference", "python", "pytorch",
    "transformers", "bert", "faiss", "milvus", "elasticsearch",
}

PRODUCTION_PHRASES = {
    "production", "deployed", "shipped", "built", "owned", "operated",
    "users", "real users", "scale", "monitoring", "latency", "on-call",
    "pipeline", "service", "api",
}

def _score_career_signal(candidate: CandidateProfile) -> float:
    history = candidate.career_history
    derived = candidate.derived

    # Career velocity (promotions / years)
    velocity = derived.career_velocity_score if derived else 0.5

    # Tenure quality
    tenure = derived.tenure_consistency if derived else 0.5

    # Applied / production experience in history
    history_text = _lower(*[e.description for e in history])
    applied_hits = _phrase_hits(history_text, RELEVANT_PHRASES)
    production_hits = _phrase_hits(history_text, PRODUCTION_PHRASES)
    applied_score = _clamp(_saturate(applied_hits, 6.0))
    production_score = _clamp(_saturate(production_hits, 5.0))

    # Scope / impact signals
    scope_keywords = ["team", "led", "managed", "architected", "owned", "founded",
                      "million", "billion", "users", "qps", "latency"]
    scope_hits = _phrase_hits(history_text, scope_keywords)
    scope_score = _clamp(_saturate(scope_hits, 5.0))

    raw = (
        0.25 * velocity +
        0.20 * tenure +
        0.25 * applied_score +
        0.20 * production_score +
        0.10 * scope_score
    )
    return _clamp(raw)


# ── Dimension 4: Behavioral Fit (15%) ─────────────────────────────────────────

def _score_behavioral_fit(
    candidate: CandidateProfile,
    jd: JobDescriptionProfile,
) -> float:
    sig = candidate.redrob_signals
    derived = candidate.derived

    # Platform activity score
    platform = derived.platform_activity_score if derived else 0.0

    # Availability signals
    avail_score = 0.0
    if sig.open_to_work_flag:
        avail_score += 0.20
    if sig.last_active_date:
        try:
            last = datetime.strptime(sig.last_active_date, "%Y-%m-%d").date()
            delta = (_TODAY - last).days
            avail_score += 0.15 if delta <= 14 else 0.10 if delta <= 30 else 0.05 if delta <= 90 else 0.0
        except ValueError:
            pass
    avail_score += 0.15 * _clamp(sig.recruiter_response_rate)
    avail_score += 0.10 * _clamp(1 - min(sig.avg_response_time_hours, 240) / 240)
    notice = sig.notice_period_days
    avail_score += 0.12 if notice <= 15 else 0.09 if notice <= 30 else 0.05 if notice <= 60 else 0.0
    avail_score += 0.08 * _clamp(sig.interview_completion_rate)
    avail_score = _clamp(avail_score)

    # Behavioral keyword match in profile text
    profile_text = _lower(candidate.summary, candidate.headline,
                          *[e.description for e in candidate.career_history])
    beh_hits = _phrase_hits(profile_text, jd.behavioral_signals)
    beh_score = _clamp(_saturate(beh_hits, 4.0))

    raw = (
        0.40 * platform +
        0.35 * avail_score +
        0.25 * beh_score
    )
    return _clamp(raw)


# ── Dimension 5: Cultural Alignment (10%) ────────────────────────────────────

def _score_cultural_alignment(
    candidate: CandidateProfile,
    jd: JobDescriptionProfile,
) -> float:
    sig = candidate.redrob_signals

    # Work mode match
    mode_match = 0.0
    jd_mode = jd.work_mode.lower()
    cand_mode = sig.preferred_work_mode.lower()
    if jd_mode == cand_mode:
        mode_match = 1.0
    elif "flexible" in (jd_mode, cand_mode):
        mode_match = 0.8
    elif {jd_mode, cand_mode} & {"hybrid", "remote"}:
        mode_match = 0.6
    else:
        mode_match = 0.3

    # Location fit
    location_text = _lower(candidate.location, candidate.country)
    if any(city in location_text for city in TIER1_CITIES):
        loc_score = 1.0
    elif "india" in location_text:
        loc_score = 0.7
    elif sig.willing_to_relocate:
        loc_score = 0.55
    else:
        loc_score = 0.2

    if sig.willing_to_relocate:
        loc_score = min(1.0, loc_score + 0.1)

    # Cultural signals in profile
    profile_text = _lower(candidate.summary, candidate.headline)
    cultural_hits = _phrase_hits(profile_text, jd.cultural_signals)
    cultural_score = _clamp(_saturate(cultural_hits, 3.0))

    raw = (
        0.40 * mode_match +
        0.40 * loc_score +
        0.20 * cultural_score
    )
    return _clamp(raw)


# ── Composite Scorer ──────────────────────────────────────────────────────────

def _tier_from_score(composite: float) -> str:
    if composite >= THRESHOLDS["strong_match"]:
        return "strong_match"
    if composite >= THRESHOLDS["good_match"]:
        return "good_match"
    if composite >= THRESHOLDS["possible"]:
        return "possible"
    return "stretch"


def score_candidate(
    candidate: CandidateProfile,
    jd: JobDescriptionProfile,
    semantic_sim: float = 0.0,
) -> Tuple[ScoreBreakdown, List[str], Dict]:
    """
    Compute 5-dimensional scores for one candidate against a JD.
    Returns (ScoreBreakdown, matched_skills, raw_features).
    """
    skill_raw, matched_skills = _score_skill_alignment(candidate, jd, semantic_sim)
    exp_raw = _score_experience_relevance(candidate, jd)
    career_raw = _score_career_signal(candidate)
    behavioral_raw = _score_behavioral_fit(candidate, jd)
    cultural_raw = _score_cultural_alignment(candidate, jd)

    # Convert to 0–100
    skill_score     = skill_raw * 100
    exp_score       = exp_raw * 100
    career_score    = career_raw * 100
    behavioral_score= behavioral_raw * 100
    cultural_score  = cultural_raw * 100

    composite = (
        WEIGHTS["skill_alignment"]      * skill_score +
        WEIGHTS["experience_relevance"] * exp_score +
        WEIGHTS["career_signal"]        * career_score +
        WEIGHTS["behavioral_fit"]       * behavioral_score +
        WEIGHTS["cultural_alignment"]   * cultural_score
    )
    composite = _clamp(composite, 0, 100)

    breakdown = ScoreBreakdown(
        composite=round(composite, 2),
        skill_alignment=round(skill_score, 2),
        experience_relevance=round(exp_score, 2),
        career_signal=round(career_score, 2),
        behavioral_fit=round(behavioral_score, 2),
        cultural_alignment=round(cultural_score, 2),
    )

    raw_features = {
        "semantic_sim": semantic_sim,
        "matched_skills": matched_skills,
        "location": candidate.location,
        "country": candidate.country,
        "notice_period": candidate.redrob_signals.notice_period_days,
        "open_to_work": candidate.redrob_signals.open_to_work_flag,
        "github_score": candidate.redrob_signals.github_activity_score,
        "response_rate": candidate.redrob_signals.recruiter_response_rate,
        "preferred_mode": candidate.redrob_signals.preferred_work_mode,
    }

    return breakdown, matched_skills, raw_features


def build_ranked_candidate(
    candidate: CandidateProfile,
    jd: JobDescriptionProfile,
    rank: int,
    semantic_sim: float,
) -> RankedCandidate:
    """Full scoring → RankedCandidate object."""
    scores, matched_skills, raw_features = score_candidate(candidate, jd, semantic_sim)
    tier = _tier_from_score(scores.composite)

    return RankedCandidate(
        rank=rank,
        candidate_id=candidate.candidate_id,
        name=candidate.name,
        current_title=candidate.current_title,
        current_company=candidate.current_company,
        total_experience_years=candidate.years_of_experience,
        top_skills=matched_skills,
        scores=scores,
        score_tier=tier,
        semantic_similarity=semantic_sim,
        career_history=candidate.career_history,
        education=candidate.education,
        redrob_signals=candidate.redrob_signals,
        raw_features=raw_features,
    )
