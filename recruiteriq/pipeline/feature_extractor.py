"""Feature Extractor — derives signals and builds narrative text from CandidateProfile."""
from __future__ import annotations
import math
import re
from datetime import date, datetime
from typing import Optional

from ..models.schemas import CandidateProfile, DerivedSignals
from ..config import TECH_SKILLS, TIER1_CITIES


_TODAY = date(2026, 6, 12)

POSITIVE_INDUSTRIES = {
    "software", "technology", "internet", "saas", "product",
    "e-commerce", "fintech", "ai", "machine learning", "analytics", "data",
}
NEGATIVE_INDUSTRIES = {
    "it services", "consulting", "outsourcing", "manufacturing",
    "paper products", "consumer goods", "hardware",
}

SENIORITY_TITLE_MAP = {
    "intern": 0.1, "junior": 0.25, "associate": 0.3,
    "mid": 0.4, "": 0.4,
    "senior": 0.65, "lead": 0.7, "staff": 0.75,
    "principal": 0.85, "manager": 0.7,
    "director": 0.9, "vp": 0.95, "head": 0.88,
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _saturate(value: float, scale: float) -> float:
    """Saturating exponential scorer: grows fast then flattens."""
    if value <= 0:
        return 0.0
    return 1.0 - math.exp(-value / scale)


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# ── Derived Signal Computation ────────────────────────────────────────────────

def _career_velocity(candidate: CandidateProfile) -> float:
    """Score based on trajectory: promotions per year, scope expansion."""
    history = candidate.career_history
    if not history:
        return 0.0
    promotions = 0
    for entry in history:
        title_l = entry.title.lower()
        if any(word in title_l for word in ["senior", "lead", "staff", "principal", "head", "manager", "director"]):
            promotions += 1
    years = max(candidate.years_of_experience, 0.5)
    velocity = promotions / years
    return _clamp(_saturate(velocity, 0.4))


def _avg_tenure(candidate: CandidateProfile) -> float:
    """Average months per role; penalise job-hopping (<6 months)."""
    durations = [e.duration_months for e in candidate.career_history if e.duration_months > 0]
    if not durations:
        return 12.0
    return sum(durations) / len(durations)


def _tenure_consistency(candidate: CandidateProfile) -> float:
    """Score: reward stable tenures, penalise frequent short stints."""
    durations = [e.duration_months for e in candidate.career_history if e.duration_months > 0]
    if not durations:
        return 0.5
    short = sum(1 for d in durations if d < 6)
    ratio_short = short / len(durations)
    avg = sum(durations) / len(durations)
    base = _clamp(_saturate(avg, 18))  # peaks around 18+ months avg
    penalty = ratio_short * 0.4
    return _clamp(base - penalty)


def _domain_depth(candidate: CandidateProfile, jd_domains: Optional[list] = None) -> float:
    """How deeply has the candidate worked in the JD's domain?"""
    industries = [e.industry.lower() for e in candidate.career_history if e.industry]
    industries.append(candidate.current_industry.lower())
    pos_hits = sum(1 for ind in industries if any(pos in ind for pos in POSITIVE_INDUSTRIES))
    neg_hits = sum(1 for ind in industries if any(neg in ind for neg in NEGATIVE_INDUSTRIES))
    score = _saturate(pos_hits, 2.0) - 0.25 * _saturate(neg_hits, 2.0)
    return _clamp(score)


def _platform_activity(candidate: CandidateProfile) -> float:
    """Normalize Redrob platform signals into a 0-1 score."""
    sig = candidate.redrob_signals
    score = 0.0
    score += 0.15 * _clamp(sig.profile_completeness_score / 100)
    github = sig.github_activity_score
    if github >= 0:
        score += 0.20 * _clamp(github / 100)
    score += 0.15 * _clamp(sig.recruiter_response_rate)
    if sig.linkedin_connected:
        score += 0.05
    score += 0.10 * _clamp(sig.interview_completion_rate)
    if sig.offer_acceptance_rate >= 0:
        score += 0.10 * _clamp(sig.offer_acceptance_rate)
    score += 0.10 * _clamp(math.log1p(sig.endorsements_received) / math.log1p(100))
    score += 0.10 * _clamp(math.log1p(sig.connection_count) / math.log1p(1000))
    if sig.verified_email:
        score += 0.025
    if sig.verified_phone:
        score += 0.025
    return _clamp(score)


def _estimate_seniority(candidate: CandidateProfile) -> str:
    title_l = candidate.current_title.lower()
    yoe = candidate.years_of_experience
    if "principal" in title_l or "staff" in title_l:
        return "staff"
    if "senior" in title_l or "lead" in title_l:
        return "senior"
    if "manager" in title_l or "director" in title_l:
        return "manager"
    if yoe >= 8:
        return "senior"
    if yoe >= 4:
        return "mid"
    if yoe >= 1:
        return "junior"
    return "junior"


def compute_derived_signals(candidate: CandidateProfile) -> DerivedSignals:
    return DerivedSignals(
        total_experience_years=candidate.years_of_experience,
        career_velocity_score=_career_velocity(candidate),
        avg_tenure_months=_avg_tenure(candidate),
        tenure_consistency=_tenure_consistency(candidate),
        domain_depth_score=_domain_depth(candidate),
        platform_activity_score=_platform_activity(candidate),
        seniority_estimate=_estimate_seniority(candidate),
    )


# ── Narrative Text Builder ────────────────────────────────────────────────────

def build_narrative(candidate: CandidateProfile) -> str:
    """
    Concatenate all candidate fields into a single narrative text for embedding.
    Maximizes signal coverage for semantic similarity matching.
    """
    parts: list[str] = []

    # Header
    if candidate.current_title:
        parts.append(f"Current role: {candidate.current_title}")
    if candidate.current_company:
        parts.append(f"at {candidate.current_company}")
    if candidate.years_of_experience:
        parts.append(f"with {candidate.years_of_experience:.1f} years of experience.")

    # Headline & Summary
    if candidate.headline:
        parts.append(candidate.headline + ".")
    if candidate.summary:
        parts.append(candidate.summary)

    # Work history
    for entry in candidate.career_history:
        if entry.title or entry.company:
            role_line = f"{entry.title} at {entry.company} ({entry.duration_months} months)."
            parts.append(role_line)
        if entry.description:
            parts.append(entry.description)

    # Skills
    skill_names = [s.name for s in candidate.skills if s.name]
    if skill_names:
        parts.append(f"Skills: {', '.join(skill_names)}.")

    # Education
    for edu in candidate.education:
        edu_line = f"{edu.degree} in {edu.field_of_study} from {edu.institution}."
        parts.append(edu_line)

    # Certifications
    for cert in candidate.certifications:
        cname = cert.get("name", "")
        if cname:
            parts.append(f"Certified: {cname}.")

    # Redrob signals (as natural language)
    sig = candidate.redrob_signals
    github = sig.github_activity_score
    if github >= 0:
        parts.append(f"GitHub activity score: {github:.0f}.")
    if sig.connection_count:
        parts.append(f"Professional network: {sig.connection_count} connections.")

    # Skill assessments
    assessments = sig.skill_assessment_scores
    if assessments:
        top = sorted(assessments.items(), key=lambda x: -x[1])[:5]
        parts.append(f"Skill assessments: {', '.join(f'{k} {v:.0f}%' for k, v in top)}.")

    return " ".join(parts)


def enrich_candidate(candidate: CandidateProfile) -> CandidateProfile:
    """Compute derived signals and narrative text in-place."""
    candidate.derived = compute_derived_signals(candidate)
    candidate.narrative_text = build_narrative(candidate)
    return candidate
