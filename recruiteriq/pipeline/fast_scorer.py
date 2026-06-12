"""Fast-path pure-Python scorer — ranks all candidates without embeddings.
Used to shortlist top-N before the expensive embedding pass.
Derived from rank_candidates.py logic but adapted for CandidateProfile.
"""
from __future__ import annotations
import math
from typing import Iterable

from ..models.schemas import CandidateProfile, JobDescriptionProfile
from ..config import TECH_SKILLS, TIER1_CITIES

POSITIVE_INDUSTRIES = {
    "software", "technology", "internet", "saas", "product",
    "e-commerce", "fintech", "ai", "machine learning", "analytics", "data",
}
NEGATIVE_INDUSTRIES = {
    "it services", "consulting", "outsourcing", "manufacturing",
    "paper products", "consumer goods", "hardware",
}
NONTECH_TITLES = {
    "marketing", "sales", "support", "operations", "hr", "people",
    "content", "writer", "designer", "consultant", "consulting",
    "account manager", "customer success", "project manager",
    "program manager", "business analyst",
}
TECH_TITLES = {
    "engineer", "scientist", "researcher", "developer", "architect",
    "analyst", "ml", "ai", "data", "platform", "backend", "fullstack",
}

PRODUCTION_PHRASES = {
    "production", "deployed", "shipped", "built", "owned", "operated",
    "users", "scale", "monitoring", "on-call", "latency", "pipeline", "api",
}

RELEVANT_PHRASES = set(TECH_SKILLS[:30])  # Top-30 tech skills


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _saturate(value: float, scale: float) -> float:
    if value <= 0:
        return 0.0
    return 1.0 - math.exp(-value / scale)


def _phrase_hits(text: str, phrases: Iterable[str]) -> int:
    return sum(1 for p in phrases if p in text)


def _years_fit(years: float, jd: JobDescriptionProfile) -> float:
    target = (jd.seniority_years_min or 3 + jd.seniority_years_max or 7) / 2
    sigma = max(abs((jd.seniority_years_max or 7) - (jd.seniority_years_min or 3)) / 2, 2)
    return math.exp(-((years - target) ** 2) / (2 * sigma ** 2))


def fast_score_candidate(candidate: CandidateProfile, jd: JobDescriptionProfile) -> float:
    """
    Lightweight pure-Python score for fast pre-filtering.
    Returns a float in [0, 1].
    """
    profile = candidate
    sig = candidate.redrob_signals

    title_l = profile.current_title.lower()
    industry_l = profile.current_industry.lower()

    # Title: positive if tech, negative if non-tech
    title_pos = 1.0 if any(t in title_l for t in TECH_TITLES) else 0.0
    title_neg = max(
        (0.7 if any(t in title_l for t in NONTECH_TITLES - {"consultant", "consulting"}) else 0.0),
        (0.9 if any(t in title_l for t in {"consultant", "consulting"}) else 0.0),
    )

    # Industry
    industry_pos = 1.0 if any(p in industry_l for p in POSITIVE_INDUSTRIES) else 0.0
    industry_neg = 1.0 if any(n in industry_l for n in NEGATIVE_INDUSTRIES) else 0.0

    # Skills match
    cand_skills = {s.name.lower() for s in candidate.skills}
    jd_skills = {s.name.lower() for s in jd.must_have_skills}
    skill_overlap = len(cand_skills & jd_skills) / max(len(jd_skills), 1)

    # Work history text signals
    history_blob = " ".join(
        f"{e.title} {e.company} {e.description} {e.industry}"
        for e in candidate.career_history
    ).lower()
    summary_blob = f"{candidate.summary} {candidate.headline} {candidate.current_title}".lower()
    all_text = history_blob + " " + summary_blob

    applied_hits = _phrase_hits(all_text, RELEVANT_PHRASES)
    production_hits = _phrase_hits(all_text, PRODUCTION_PHRASES)
    applied_score = _clamp(_saturate(applied_hits, 4.0))
    production_score = _clamp(_saturate(production_hits, 4.0))

    # JD skill phrase overlap in history
    jd_text = f"{jd.raw_text} {jd.role_intent_summary}".lower()
    tech_phrase_hits = sum(
        1 for skill in TECH_SKILLS
        if skill in jd_text and skill in all_text
    )
    phrase_score = _clamp(_saturate(tech_phrase_hits, 5.0))

    # Experience fit
    experience_score = _years_fit(profile.years_of_experience, jd)

    # Availability
    avail = 0.0
    if sig.open_to_work_flag:
        avail += 0.3
    if sig.notice_period_days <= 30:
        avail += 0.2
    elif sig.notice_period_days <= 60:
        avail += 0.1
    avail += 0.2 * _clamp(sig.recruiter_response_rate)
    avail = _clamp(avail)

    # Location
    loc_text = f"{profile.location} {profile.country}".lower()
    if any(city in loc_text for city in TIER1_CITIES):
        location_score = 1.0
    elif "india" in loc_text:
        location_score = 0.7
    elif sig.willing_to_relocate:
        location_score = 0.55
    else:
        location_score = 0.25

    # Composite
    raw = (
        0.22 * applied_score +
        0.18 * production_score +
        0.15 * skill_overlap +
        0.12 * title_pos +
        0.08 * phrase_score +
        0.08 * experience_score +
        0.07 * avail +
        0.05 * location_score +
        0.03 * industry_pos
    )

    # Penalties
    penalty = 0.0
    penalty += 0.18 * title_neg
    penalty += 0.14 * industry_neg
    if not sig.open_to_work_flag:
        penalty += 0.04
    if location_score < 0.3:
        penalty += 0.06

    return _clamp(raw - penalty)
