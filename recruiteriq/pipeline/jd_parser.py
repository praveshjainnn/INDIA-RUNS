"""JD Parser — free, local NLP-based job description parser.
No API keys required. Uses regex + keyword matching + skill taxonomy.
"""
from __future__ import annotations
import re
from typing import List, Tuple
from ..config import TECH_SKILLS, BEHAVIORAL_SIGNALS
from ..models.schemas import JobDescriptionProfile, SkillRequirement


# ── Seniority detection ───────────────────────────────────────────────────────
SENIORITY_KEYWORDS = {
    "intern":       ("intern", 0, 1),
    "junior":       ("junior", 0, 2),
    "mid":          ("mid", 2, 5),
    "senior":       ("senior", 5, 10),
    "staff":        ("staff", 7, 12),
    "principal":    ("principal", 10, 15),
    "lead":         ("lead", 6, 12),
    "manager":      ("manager", 5, 12),
    "director":     ("director", 10, 20),
    "vp":           ("vp", 12, 25),
}

YEARS_PATTERNS = [
    r"(\d+)\+?\s*(?:to|-)\s*(\d+)\s*years?",      # "5 to 8 years"
    r"(\d+)\+\s*years?",                            # "5+ years"
    r"minimum\s+(\d+)\s*years?",                    # "minimum 5 years"
    r"at\s+least\s+(\d+)\s*years?",                # "at least 5 years"
    r"(\d+)\s*years?\s+(?:of\s+)?experience",       # "5 years of experience"
]

WORK_MODE_KEYWORDS = {
    "remote":   ["remote", "work from home", "wfh", "fully remote"],
    "hybrid":   ["hybrid"],
    "onsite":   ["onsite", "on-site", "on site", "in-office", "in office"],
    "flexible": ["flexible"],
}

# Must-have signal phrases
MUST_HAVE_PHRASES = [
    "required", "must have", "must-have", "essential", "mandatory",
    "minimum requirement", "you should have", "you must have",
    "we require", "need", "should have", r"\bneeded\b",
]

NICE_TO_HAVE_PHRASES = [
    "nice to have", "nice-to-have", "preferred", "plus", "bonus",
    "advantage", "desirable", "ideal", "would be great", "optional",
    "good to have",
]

# Domain / industry detection
DOMAIN_MAP = {
    "fintech": ["fintech", "finance", "banking", "payments", "lending", "insurance"],
    "ecommerce": ["ecommerce", "e-commerce", "retail", "marketplace", "d2c"],
    "saas": ["saas", "b2b", "software as a service", "enterprise software"],
    "healthtech": ["healthtech", "health", "medical", "healthcare", "pharma"],
    "edtech": ["edtech", "education", "learning", "edtech"],
    "logistics": ["logistics", "supply chain", "delivery", "shipping"],
    "adtech": ["adtech", "advertising", "marketing tech", "dsp", "programmatic"],
    "data": ["data platform", "analytics", "bi", "business intelligence"],
}


def _lower(text: str) -> str:
    return text.lower()


def _detect_seniority(text: str) -> Tuple[str, int, int]:
    """Return (level, years_min, years_max) from JD text."""
    tl = _lower(text)
    for level, (label, ymin, ymax) in SENIORITY_KEYWORDS.items():
        if re.search(rf"\b{level}\b", tl):
            return label, ymin, ymax
    # Fallback: look for explicit year ranges
    for pattern in YEARS_PATTERNS:
        m = re.search(pattern, tl)
        if m:
            groups = [int(g) for g in m.groups() if g is not None]
            if len(groups) == 2:
                ymin, ymax = groups[0], groups[1]
            else:
                ymin = groups[0]
                ymax = ymin + 3
            if ymin <= 2:
                return "junior", ymin, ymax
            elif ymin <= 5:
                return "mid", ymin, ymax
            elif ymin <= 8:
                return "senior", ymin, ymax
            else:
                return "staff", ymin, ymax
    return "mid", 3, 7


def _detect_work_mode(text: str) -> str:
    tl = _lower(text)
    for mode, phrases in WORK_MODE_KEYWORDS.items():
        if any(phrase in tl for phrase in phrases):
            return mode
    return "hybrid"


def _extract_role_title(text: str) -> str:
    """Extract the job title from the first non-empty lines."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return "Unknown Role"
    # First line is often the title, or look for "Role:" / "Position:"
    for line in lines[:5]:
        if re.search(r"(role|position|title|job)\s*:", line, re.I):
            return re.sub(r".*(role|position|title|job)\s*:", "", line, flags=re.I).strip()
    # Use first substantial line if short enough
    if len(lines[0]) < 80:
        return lines[0]
    return "Unknown Role"


def _extract_skills(text: str) -> Tuple[List[SkillRequirement], List[SkillRequirement]]:
    """Split JD into must-have and nice-to-have sections, then extract skills."""
    tl = _lower(text)

    # Try to split into sections
    nice_section = ""
    must_section = text

    # Find a nice-to-have section boundary
    nice_markers = ["nice to have", "nice-to-have", "preferred qualifications",
                    "bonus", "good to have", "plus if you have"]
    for marker in nice_markers:
        idx = tl.find(marker)
        if idx != -1:
            must_section = text[:idx]
            nice_section = text[idx:]
            break

    must_skills: List[SkillRequirement] = []
    nice_skills: List[SkillRequirement] = []

    seen_must: set = set()
    seen_nice: set = set()

    for skill in TECH_SKILLS:
        skill_l = skill.lower()
        # Check must-have section
        if re.search(rf"\b{re.escape(skill_l)}\b", must_section.lower()):
            if skill_l not in seen_must:
                seen_must.add(skill_l)
                must_skills.append(SkillRequirement(name=skill.title()))
        # Check nice-to-have section (only if a section was found)
        if nice_section and re.search(rf"\b{re.escape(skill_l)}\b", nice_section.lower()):
            if skill_l not in seen_nice and skill_l not in seen_must:
                seen_nice.add(skill_l)
                nice_skills.append(SkillRequirement(name=skill.title()))

    return must_skills, nice_skills


def _extract_behavioral_signals(text: str) -> List[str]:
    """Find behavioral/cultural signal words mentioned in the JD."""
    tl = _lower(text)
    found = []
    for signal in BEHAVIORAL_SIGNALS:
        if signal in tl:
            found.append(signal)
    return found


def _detect_domain(text: str) -> List[str]:
    tl = _lower(text)
    domains = []
    for domain, phrases in DOMAIN_MAP.items():
        if any(p in tl for p in phrases):
            domains.append(domain)
    return domains if domains else ["technology"]


def _build_embedding_text(jd: JobDescriptionProfile) -> str:
    """Construct a rich narrative from the parsed JD for embedding."""
    parts = [
        f"Job title: {jd.role_title}.",
        f"Seniority: {jd.seniority_level}.",
        f"Work mode: {jd.work_mode}.",
        f"Domain: {', '.join(jd.domain_industry)}.",
        f"Required skills: {', '.join(s.name for s in jd.must_have_skills[:15])}.",
        f"Preferred skills: {', '.join(s.name for s in jd.nice_to_have_skills[:10])}.",
        f"Behavioral expectations: {', '.join(jd.behavioral_signals[:8])}.",
        jd.role_intent_summary,
    ]
    return " ".join(p for p in parts if p and p != ".")


def _build_intent_summary(text: str, role_title: str, must_skills: List[SkillRequirement]) -> str:
    """Generate a 1-2 sentence role intent summary."""
    skill_names = [s.name for s in must_skills[:5]]
    skill_str = ", ".join(skill_names) if skill_names else "relevant technologies"

    # Look for key phrases in JD
    tl = _lower(text)
    intent_phrases = []
    if any(k in tl for k in ["build", "scale", "architect"]):
        intent_phrases.append("build and scale systems")
    if any(k in tl for k in ["ml", "machine learning", "model"]):
        intent_phrases.append("develop ML solutions")
    if any(k in tl for k in ["data", "pipeline", "etl"]):
        intent_phrases.append("design data pipelines")
    if any(k in tl for k in ["research", "innovate", "state of the art"]):
        intent_phrases.append("drive research and innovation")

    intent_str = " and ".join(intent_phrases[:2]) if intent_phrases else "deliver technical outcomes"
    return (
        f"Seeking a {role_title} to {intent_str} "
        f"using {skill_str}. "
        f"Strong emphasis on hands-on engineering and production impact."
    )


def parse_jd(raw_text: str) -> JobDescriptionProfile:
    """
    Parse a raw job description string into a structured JobDescriptionProfile.
    Pure Python / regex — no API calls required.
    """
    if not raw_text or not raw_text.strip():
        return JobDescriptionProfile(raw_text=raw_text)

    role_title = _extract_role_title(raw_text)
    seniority_level, ymin, ymax = _detect_seniority(raw_text)
    work_mode = _detect_work_mode(raw_text)
    domain_industry = _detect_domain(raw_text)
    must_skills, nice_skills = _extract_skills(raw_text)
    behavioral_signals = _extract_behavioral_signals(raw_text)
    cultural_signals = [s for s in behavioral_signals
                        if s in {"ownership", "collaboration", "startup", "product mindset"}]

    intent_summary = _build_intent_summary(raw_text, role_title, must_skills)

    jd = JobDescriptionProfile(
        raw_text=raw_text,
        role_title=role_title,
        seniority_level=seniority_level,
        seniority_years_min=ymin,
        seniority_years_max=ymax,
        work_mode=work_mode,
        domain_industry=domain_industry,
        must_have_skills=must_skills,
        nice_to_have_skills=nice_skills,
        behavioral_signals=behavioral_signals,
        cultural_signals=cultural_signals,
        role_intent_summary=intent_summary,
    )
    jd.embedding_text = _build_embedding_text(jd)
    return jd
