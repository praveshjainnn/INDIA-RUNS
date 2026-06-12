"""Rationale Builder — generates recruiter rationale + probe questions.
Free, template-based. Uses 40+ varied templates to avoid repetition.
No API calls needed.
"""
from __future__ import annotations
import random
from typing import List, Optional

from ..models.schemas import RankedCandidate, JobDescriptionProfile


# ── Rationale Templates ───────────────────────────────────────────────────────

STRONG_MATCH_TEMPLATES = [
    "{title} with {yoe}+ years brings exactly the kind of {domain} experience this role demands; "
    "{skill_str} are direct matches against the JD must-haves.",

    "The {yoe}-year track record in {title} roles, particularly with {skill_str}, "
    "maps closely to the core mandate described in the JD.",

    "Strong fit: {title} background with hands-on {skill_str} experience "
    "and a production-oriented history that aligns with role expectations.",

    "{title} at {company} ({yoe} yrs) — the combination of {skill_str} "
    "and demonstrated shipping experience makes this a standout profile.",

    "Direct alignment on the hardest requirements: {skill_str}. "
    "The {yoe}-year {title} trajectory shows scope and impact at the right level.",
]

GOOD_MATCH_TEMPLATES = [
    "{title} with {yoe} years; {skill_str} are credible matches, "
    "though some JD must-haves will need to be validated in screening.",

    "Credible fit: {yoe}-year career in {title} roles with good coverage of {skill_str}. "
    "A few targeted interview questions would confirm depth.",

    "The profile covers {skill_str} well, and the {yoe} years in {title} "
    "suggest the right trajectory — depth on specific tools TBD.",

    "{title} at {company}; {skill_str} appear in the profile with meaningful context. "
    "Worth a screening call to validate production depth.",

    "Good alignment on {skill_str}; the {yoe}-year {title} history shows "
    "relevant domain exposure even if not a perfect technical overlap.",
]

POSSIBLE_TEMPLATES = [
    "{title} with {yoe} years has adjacent skills ({skill_str}) that "
    "could transfer, but this is a development hire, not a ready-made match.",

    "Partial fit: {yoe} years in {title}. {skill_str} appear in the profile "
    "but depth and production exposure are unclear — probe carefully.",

    "The profile shows some {skill_str} exposure, but the {yoe}-year {title} "
    "background is not a direct match. Suitable if the team can invest in onboarding.",

    "Adjacent fit: {title} with {yoe} years. {skill_str} suggest transferable skills "
    "but the JD's core requirements may not be fully met yet.",
]

STRETCH_TEMPLATES = [
    "{title} with {yoe} years: limited overlap with the JD's technical requirements. "
    "Few signals ({skill_str}) of direct relevance.",

    "Stretch candidate: the {yoe}-year {title} profile has minimal coverage of "
    "JD must-haves. Only consider if the pipeline has no stronger options.",

    "Low alignment: {title} background ({yoe} yrs) with limited {skill_str} context. "
    "Significant upskilling would be required.",
]

# ── Probe Question Templates ──────────────────────────────────────────────────

PROBE_QUESTIONS_BY_TIER = {
    "strong_match": [
        "Can you walk me through the largest {skill} system you built in production?",
        "What's the most complex {skill} problem you've solved at scale?",
        "How did you handle model/system drift when running {skill} at scale?",
        "Describe a situation where {skill} performance wasn't meeting SLAs — how did you fix it?",
        "How did you balance engineering velocity with reliability in your {skill} work?",
    ],
    "good_match": [
        "How much hands-on {skill} work have you done versus leading others doing it?",
        "Can you describe a specific {skill} project from ideation through production?",
        "What's your experience taking a {skill} system from prototype to production?",
        "How familiar are you with evaluating and monitoring {skill} systems?",
    ],
    "possible": [
        "How quickly do you typically pick up a new {skill} stack?",
        "What's your learning plan if hired for a role requiring deep {skill} work?",
        "Can you describe any side projects or self-directed work in {skill}?",
        "What parts of {skill} have you worked with most recently?",
    ],
    "stretch": [
        "What steps are you actively taking to build {skill} expertise?",
        "How much of your recent work has involved any {skill} adjacent work?",
        "Why are you interested in moving into a {skill}-heavy role now?",
    ],
}

# ── Top Strength Templates ────────────────────────────────────────────────────

STRENGTH_TEMPLATES = [
    "Demonstrated {skill} expertise with {yoe} years of hands-on, production-grade experience.",
    "Strong track record of shipping {skill} systems in {domain}-adjacent environments.",
    "{yoe}-year career trajectory shows consistent growth in scope and technical depth.",
    "High recruiter availability signals (open to work, fast response) combined with relevant {skill} background.",
    "Proven production experience with {skill} — a rare combination in the candidate pool.",
    "Deep {skill} skill set validated through endorsements, assessments, and work history.",
    "Career velocity above average: multiple promotions in a {yoe}-year span with growing scope.",
]


def _pick(templates: list, seed: str) -> str:
    """Deterministic template pick based on candidate_id."""
    idx = abs(hash(seed)) % len(templates)
    return templates[idx]


def _format_template(template: str, rc: RankedCandidate, jd: JobDescriptionProfile) -> str:
    top_skill = rc.top_skills[0] if rc.top_skills else (
        jd.must_have_skills[0].name if jd.must_have_skills else "the required skills"
    )
    skill_str = ", ".join(rc.top_skills[:3]) if rc.top_skills else "core technical skills"
    domain = jd.domain_industry[0] if jd.domain_industry else "technology"
    company = rc.current_company if rc.current_company else "their current company"

    return template.format(
        title=rc.current_title or "Candidate",
        yoe=f"{rc.total_experience_years:.1f}",
        skill=top_skill,
        skill_str=skill_str,
        domain=domain,
        company=company,
    )


def build_rationale(rc: RankedCandidate, jd: JobDescriptionProfile) -> str:
    """Generate a 2-sentence recruiter rationale."""
    tier = rc.score_tier

    if tier == "strong_match":
        templates = STRONG_MATCH_TEMPLATES
    elif tier == "good_match":
        templates = GOOD_MATCH_TEMPLATES
    elif tier == "possible":
        templates = POSSIBLE_TEMPLATES
    else:
        templates = STRETCH_TEMPLATES

    first = _pick(templates, rc.candidate_id)
    sentence1 = _format_template(first, rc, jd)

    # Add availability context as second sentence
    sig = rc.redrob_signals
    parts = []
    if sig:
        if sig.open_to_work_flag:
            parts.append("Currently open to work")
        notice = sig.notice_period_days
        if notice <= 30:
            parts.append(f"notice period is just {notice} days")
        elif notice <= 60:
            parts.append(f"can join within {notice} days")
        else:
            parts.append(f"notice period is {notice} days — factor into timeline")
        if sig.recruiter_response_rate >= 0.5:
            parts.append(f"high recruiter response rate ({sig.recruiter_response_rate:.0%})")
        location = f"{rc.raw_features.get('location', '')} {rc.raw_features.get('country', '')}".strip()
        if location:
            parts.append(f"based in {location}")

    sentence2 = ("; ".join(parts[:3]) + ".") if parts else ""
    return f"{sentence1} {sentence2}".strip()


def build_top_strength(rc: RankedCandidate, jd: JobDescriptionProfile) -> str:
    """One-line top strength statement."""
    template = _pick(STRENGTH_TEMPLATES, rc.candidate_id + "_strength")
    return _format_template(template, rc, jd)


def build_probe_question(rc: RankedCandidate, jd: JobDescriptionProfile) -> str:
    """One targeted interview probe question."""
    tier = rc.score_tier
    probes = PROBE_QUESTIONS_BY_TIER.get(tier, PROBE_QUESTIONS_BY_TIER["good_match"])
    probe = _pick(probes, rc.candidate_id + "_probe")
    top_skill = rc.top_skills[0] if rc.top_skills else (
        jd.must_have_skills[0].name if jd.must_have_skills else "key technical areas"
    )
    return probe.format(skill=top_skill)


def enrich_with_rationale(rc: RankedCandidate, jd: JobDescriptionProfile) -> RankedCandidate:
    """Adds rationale, strength, and probe question to a RankedCandidate."""
    rc.recruiter_rationale = build_rationale(rc, jd)
    rc.top_strength = build_top_strength(rc, jd)
    rc.probe_question = build_probe_question(rc, jd)
    return rc
