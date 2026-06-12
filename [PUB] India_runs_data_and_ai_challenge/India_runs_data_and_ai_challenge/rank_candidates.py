#!/usr/bin/env python3
"""Rank candidates for the Redrob hackathon submission.

The scorer is JD-aware and deliberately prioritizes applied ML, retrieval,
ranking, production shipping, and recruiter availability over simple keyword
matching.
"""

from __future__ import annotations

import csv
import html
import heapq
import json
import math
import re
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parent
DEFAULT_CANDIDATES = ROOT / "candidates.jsonl"
DEFAULT_JOB_DESCRIPTION = ROOT / "job_description.docx"
DEFAULT_OUTPUT = ROOT / "submission.csv"


TECH_TITLE_POSITIVE = {
    "ai engineer",
    "ml engineer",
    "machine learning engineer",
    "data scientist",
    "applied scientist",
    "search engineer",
    "ranking engineer",
    "recommender",
    "recommendation engineer",
    "nlp engineer",
    "backend engineer",
    "software engineer",
    "data engineer",
    "platform engineer",
    "full stack engineer",
    "principal engineer",
    "senior engineer",
}

NONTECH_TITLE_NEGATIVE = {
    "marketing",
    "sales",
    "support",
    "operations",
    "hr",
    "people",
    "content",
    "writer",
    "designer",
    "consultant",
    "consulting",
    "account manager",
    "customer success",
    "project manager",
    "program manager",
    "business analyst",
}

POSITIVE_INDUSTRIES = {
    "software",
    "technology",
    "internet",
    "saas",
    "product",
    "e-commerce",
    "fintech",
    "ai",
    "machine learning",
    "analytics",
    "data",
}

NEGATIVE_INDUSTRIES = {
    "it services",
    "consulting",
    "outsourcing",
    "manufacturing",
    "paper products",
    "consumer goods",
    "hardware",
}

RELEVANT_SKILL_PHRASES = {
    "embeddings",
    "sentence transformers",
    "vector db",
    "vector database",
    "retrieval",
    "search",
    "ranking",
    "recommendation",
    "recommender",
    "semantic search",
    "hybrid search",
    "dense retrieval",
    "bm25",
    "faiss",
    "milvus",
    "pinecone",
    "weaviate",
    "qdrant",
    "elasticsearch",
    "opensearch",
    "rag",
    "llm",
    "fine-tuning",
    "lora",
    "qlora",
    "peft",
    "transformers",
    "bge",
    "e5",
    "xgboost",
    "lightgbm",
    "ndcg",
    "mrr",
    "map",
    "ab testing",
    "evaluation",
    "offline",
    "online",
    "python",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "sklearn",
}

PRODUCTION_PHRASES = {
    "production",
    "deployed",
    "shipped",
    "built",
    "owned",
    "maintained",
    "operated",
    "users",
    "real users",
    "scale",
    "monitoring",
    "on-call",
    "latency",
    "drift",
    "regression",
    "index refresh",
    "feature pipeline",
    "pipeline",
    "service",
    "api",
}

RESEARCH_PHRASES = {
    "academic",
    "research only",
    "pure research",
    "thesis",
    "paper",
    "papers",
    "lab",
}

TIER1_CITIES = {
    "pune",
    "noida",
    "delhi",
    "ncr",
    "gurugram",
    "gurgaon",
    "mumbai",
    "bengaluru",
    "bangalore",
    "hyderabad",
    "chennai",
}


def extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
    text = re.sub(r"<w:p[^>]*>", "\n", xml)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def lower_text(*parts: str) -> str:
    return " ".join(part for part in parts if part).lower()


def phrase_hits(text: str, phrases: Iterable[str]) -> int:
    count = 0
    for phrase in phrases:
        if phrase in text:
            count += 1
    return count


def saturating_score(value: float, scale: float) -> float:
    if value <= 0:
        return 0.0
    return 1.0 - math.exp(-value / scale)


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def years_fit(years: float) -> float:
    if years < 0:
        return 0.0
    if 5.0 <= years <= 9.0:
        return 1.0
    return math.exp(-((years - 7.0) ** 2) / (2.0 * 2.1**2))


def title_category(title: str) -> tuple[float, float]:
    title_l = title.lower()
    positive = 1.0 if any(term in title_l for term in TECH_TITLE_POSITIVE) else 0.0
    negative = 0.0
    for term in NONTECH_TITLE_NEGATIVE:
        if term in title_l:
            negative = max(negative, 0.6 if term not in {"consultant", "consulting"} else 0.9)
    if "manager" in title_l and positive == 0.0:
        negative = max(negative, 0.35)
    if "research" in title_l and positive == 0.0:
        negative = max(negative, 0.25)
    return positive, negative


def industry_score(industry: str) -> tuple[float, float]:
    industry_l = industry.lower()
    pos = 1.0 if any(term in industry_l for term in POSITIVE_INDUSTRIES) else 0.0
    neg = 1.0 if any(term in industry_l for term in NEGATIVE_INDUSTRIES) else 0.0
    return pos, neg


def location_score(profile: dict, signals: dict) -> float:
    location = lower_text(profile.get("location", ""), profile.get("country", ""))
    mode = signals.get("preferred_work_mode", "")
    relocate = bool(signals.get("willing_to_relocate", False))

    if any(city in location for city in TIER1_CITIES):
        base = 1.0
    elif "india" in location:
        base = 0.75
    elif relocate:
        base = 0.6
    else:
        base = 0.2

    if mode in {"hybrid", "flexible"}:
        base += 0.08
    elif mode == "onsite" and any(city in location for city in {"pune", "noida", "delhi", "ncr", "mumbai", "hyderabad"}):
        base += 0.05
    elif mode == "remote":
        base += 0.02

    if relocate:
        base += 0.05

    return clamp(base)


def availability_score(signals: dict) -> float:
    score = 0.0
    if signals.get("open_to_work_flag"):
        score += 0.22

    last_active = signals.get("last_active_date")
    if last_active:
        try:
            delta_days = (date(2026, 6, 8) - datetime.strptime(last_active, "%Y-%m-%d").date()).days
            if delta_days <= 14:
                score += 0.18
            elif delta_days <= 30:
                score += 0.14
            elif delta_days <= 90:
                score += 0.08
        except ValueError:
            pass

    response_rate = float(signals.get("recruiter_response_rate", 0.0) or 0.0)
    score += 0.20 * clamp(response_rate)

    response_time = float(signals.get("avg_response_time_hours", 999.0) or 999.0)
    score += 0.12 * clamp(1.0 - min(response_time, 240.0) / 240.0)

    notice_period = float(signals.get("notice_period_days", 180) or 180)
    if notice_period <= 15:
        score += 0.16
    elif notice_period <= 30:
        score += 0.13
    elif notice_period <= 60:
        score += 0.08
    elif notice_period <= 90:
        score += 0.03

    score += 0.10 * clamp(float(signals.get("interview_completion_rate", 0.0) or 0.0))

    offer_rate = float(signals.get("offer_acceptance_rate", -1.0) or -1.0)
    if offer_rate >= 0:
        score += 0.08 * clamp(offer_rate)

    score += 0.06 * clamp(math.log1p(float(signals.get("saved_by_recruiters_30d", 0))) / math.log1p(20.0))
    score += 0.04 * clamp(math.log1p(float(signals.get("profile_views_received_30d", 0))) / math.log1p(200.0))

    if signals.get("verified_email"):
        score += 0.02
    if signals.get("verified_phone"):
        score += 0.02
    if signals.get("linkedin_connected"):
        score += 0.01

    github_score = float(signals.get("github_activity_score", -1.0) or -1.0)
    if github_score >= 0:
        score += 0.10 * clamp(github_score / 100.0)

    return clamp(score)


def skill_score(skills: Sequence[dict], signals: dict) -> tuple[float, list[str]]:
    matched = []
    total = 0.0
    assessment = signals.get("skill_assessment_scores", {}) or {}

    for skill in skills:
        name = str(skill.get("name", "")).strip()
        if not name:
            continue
        name_l = name.lower()
        if any(phrase in name_l for phrase in RELEVANT_SKILL_PHRASES):
            matched.append(name)
            proficiency = str(skill.get("proficiency", "")).lower()
            proficiency_weight = {"beginner": 0.35, "intermediate": 0.62, "advanced": 0.85, "expert": 1.0}.get(proficiency, 0.5)
            endorsements = float(skill.get("endorsements", 0) or 0)
            duration = float(skill.get("duration_months", 0) or 0)
            assess = float(assessment.get(name, 0.0) or 0.0)
            total += 0.9 * proficiency_weight + 0.15 * clamp(endorsements / 40.0) + 0.1 * clamp(duration / 24.0)
            if assess > 0:
                total += 0.25 * clamp(assess / 100.0)

    return clamp(saturating_score(total, 2.2)), matched


def history_score(career_history: Sequence[dict], profile: dict) -> tuple[float, float, float, list[str], int, float]:
    blobs = []
    production_hits = 0
    applied_hits = 0
    product_hits = 0

    for item in career_history:
        title = str(item.get("title", ""))
        company = str(item.get("company", ""))
        desc = str(item.get("description", ""))
        industry = str(item.get("industry", ""))
        text = lower_text(title, company, desc, industry)
        blobs.append(text)
        production_hits += phrase_hits(text, PRODUCTION_PHRASES)
        applied_hits += phrase_hits(text, RELEVANT_SKILL_PHRASES)
        if any(term in text for term in {"product", "user", "shipping", "deployed", "production", "scale"}):
            product_hits += 1

    joined = " ".join(blobs)
    research_hits = phrase_hits(joined, RESEARCH_PHRASES)
    total_text = joined + " " + lower_text(profile.get("summary", ""), profile.get("headline", ""), profile.get("current_title", ""))
    consulting_only = 1.0 if (
        phrase_hits(total_text, {"consulting", "consultant", "it services"}) > 0
        and phrase_hits(total_text, {"product", "startup", "saas", "internet", "user", "ship", "deploy"}) == 0
    ) else 0.0

    applied_score = clamp(saturating_score(applied_hits, 3.2))
    production_score = clamp(saturating_score(production_hits, 4.0))
    product_score = clamp(saturating_score(product_hits + int(any(ind.lower() in total_text for ind in POSITIVE_INDUSTRIES)), 2.0))

    companies = [str(item.get("company", "")) for item in career_history if item.get("company")]
    return applied_score, production_score, product_score, companies, research_hits, consulting_only


def jd_signal_strength(jd_text: str) -> dict[str, float]:
    jd = jd_text.lower()
    return {
        "search": 1.0 if any(p in jd for p in {"retrieval", "search", "ranking", "recommendation", "hybrid search", "vector", "embedding"}) else 0.0,
        "production": 1.0 if any(p in jd for p in {"production", "deployed", "real users", "scale", "evaluate"}) else 0.0,
        "python": 1.0 if "python" in jd else 0.0,
        "evaluation": 1.0 if any(p in jd for p in {"ndcg", "mrr", "map", "offline", "online", "ab test", "evaluation"}) else 0.0,
        "llm": 1.0 if any(p in jd for p in {"llm", "fine-tuning", "embeddings", "rag"}) else 0.0,
    }


def score_candidate(candidate: dict, jd_text: str) -> tuple[float, dict]:
    profile = candidate.get("profile", {}) or {}
    signals = candidate.get("redrob_signals", {}) or {}
    career_history = candidate.get("career_history", []) or []
    skills = candidate.get("skills", []) or []

    title_pos, title_neg = title_category(str(profile.get("current_title", "")))
    industry_pos, industry_neg = industry_score(str(profile.get("current_industry", "")))
    skill_component, relevant_skills = skill_score(skills, signals)
    applied_score, production_score, product_score, companies, research_hits, consulting_only = history_score(career_history, profile)

    profile_text = lower_text(
        str(profile.get("headline", "")),
        str(profile.get("summary", "")),
        str(profile.get("current_title", "")),
        str(profile.get("current_company", "")),
        str(profile.get("current_industry", "")),
    )
    jd_alignment = saturating_score(
        phrase_hits(profile_text, {"embedding", "retrieval", "ranking", "search", "recommendation", "llm", "fine-tuning", "python"})
        + phrase_hits(profile_text, {"ndcg", "mrr", "map", "evaluation", "offline", "online"})
        + phrase_hits(profile_text, {"vector", "milvus", "pinecone", "weaviate", "qdrant", "faiss", "elasticsearch", "opensearch"}),
        3.0,
    )

    experience = years_fit(float(profile.get("years_of_experience", 0.0) or 0.0))
    location = location_score(profile, signals)
    availability = availability_score(signals)

    education = 0.0
    for item in candidate.get("education", []) or []:
        tier = str(item.get("tier", "unknown"))
        if tier == "tier_1":
            education = max(education, 1.0)
        elif tier == "tier_2":
            education = max(education, 0.85)
        elif tier == "tier_3":
            education = max(education, 0.65)
        elif tier == "tier_4":
            education = max(education, 0.45)
        else:
            education = max(education, 0.25)

    signal_completeness = clamp(float(signals.get("profile_completeness_score", 0.0) or 0.0) / 100.0)
    jd_strategic = jd_signal_strength(jd_text)

    relevance = clamp(
        0.26 * applied_score
        + 0.18 * production_score
        + 0.17 * skill_component
        + 0.12 * title_pos
        + 0.08 * jd_alignment
        + 0.07 * product_score
        + 0.06 * jd_strategic["search"]
        + 0.04 * jd_strategic["evaluation"]
        + 0.02 * jd_strategic["llm"]
    )

    penalty = 0.0
    penalty += 0.20 * title_neg
    penalty += 0.16 * industry_neg
    penalty += 0.12 * consulting_only
    penalty += 0.08 if research_hits >= 2 and applied_score < 0.3 else 0.0

    if experience < 0.25:
        penalty += 0.12
    if 0.25 <= experience < 0.45:
        penalty += 0.06

    if not signals.get("open_to_work_flag", False):
        penalty += 0.05
    if float(signals.get("notice_period_days", 180) or 180) > 60:
        penalty += 0.04
    if location < 0.4:
        penalty += 0.08

    raw = (
        0.27 * relevance
        + 0.14 * experience
        + 0.11 * location
        + 0.15 * availability
        + 0.05 * education
        + 0.06 * signal_completeness
        + 0.09 * product_score
        + 0.04 * title_pos
        + 0.04 * industry_pos
        + 0.05 * jd_strategic["production"]
        + 0.04 * jd_strategic["python"]
        - penalty
    )

    score = clamp(raw)

    return score, {
        "relevant_skills": relevant_skills,
        "experience": experience,
        "availability": availability,
        "location": location,
        "title_pos": title_pos,
        "title_neg": title_neg,
        "industry_pos": industry_pos,
        "industry_neg": industry_neg,
        "applied_score": applied_score,
        "production_score": production_score,
        "product_score": product_score,
        "jd_alignment": jd_alignment,
        "education": education,
        "signal_completeness": signal_completeness,
        "research_hits": research_hits,
        "consulting_only": consulting_only,
        "penalty": penalty,
        "companies": companies,
    }


def build_reason(candidate: dict, features: dict, rank: int) -> str:
    profile = candidate.get("profile", {}) or {}
    signals = candidate.get("redrob_signals", {}) or {}
    current_title = str(profile.get("current_title", "candidate")).strip()
    years = float(profile.get("years_of_experience", 0.0) or 0.0)
    relevant_skills = [skill for skill in features.get("relevant_skills", []) if skill][:4]
    location = str(profile.get("location", "")).strip()
    country = str(profile.get("country", "")).strip()
    notice = int(signals.get("notice_period_days", 180) or 180)
    response_rate = float(signals.get("recruiter_response_rate", 0.0) or 0.0)
    last_active = str(signals.get("last_active_date", "")).strip()
    open_flag = bool(signals.get("open_to_work_flag", False))
    github = float(signals.get("github_activity_score", -1.0) or -1.0)

    skill_bits = ", ".join(relevant_skills[:3]) if relevant_skills else "few explicit AI/search signals"
    tone = "strong fit" if rank <= 10 else ("credible fit" if rank <= 50 else "adjacent fit")

    pattern = rank % 3
    if features.get("title_pos", 0.0) > 0 and features.get("production_score", 0.0) >= 0.35:
        if pattern == 0:
            first_sentence = f"{current_title} with {years:.1f} yrs and {skill_bits}; the profile shows hands-on engineering plus production exposure."
        elif pattern == 1:
            first_sentence = f"With {years:.1f} yrs in {current_title.lower()}, the strongest evidence is {skill_bits} plus shipping history."
        else:
            first_sentence = f"{current_title} at {years:.1f} yrs lands well on the JD because of {skill_bits} and real production work."
    elif features.get("production_score", 0.0) >= 0.45:
        if pattern == 0:
            first_sentence = f"{current_title} with {years:.1f} yrs; {skill_bits}, with enough shipping evidence to look relevant beyond keywords."
        elif pattern == 1:
            first_sentence = f"At {years:.1f} yrs, {current_title.lower()} plus {skill_bits} suggests the candidate has done more than keyword matching."
        else:
            first_sentence = f"{current_title} with {years:.1f} yrs stands out mainly for {skill_bits} and the production trail in the history."
    elif features.get("consulting_only", 0.0) > 0.0:
        if pattern == 0:
            first_sentence = f"{current_title} with {years:.1f} yrs; {skill_bits}, but the career history still reads service-heavy rather than product-heavy."
        elif pattern == 1:
            first_sentence = f"The profile has {years:.1f} yrs and {skill_bits}, though the background looks more consulting-oriented than product-oriented."
        else:
            first_sentence = f"{current_title} with {years:.1f} yrs surfaces some useful signals, but the services-heavy path is a real constraint."
    elif features.get("research_hits", 0) >= 2 and features.get("applied_score", 0.0) < 0.3:
        if pattern == 0:
            first_sentence = f"{current_title} with {years:.1f} yrs; {skill_bits}, though the wording leans research-heavy without enough deployment evidence."
        elif pattern == 1:
            first_sentence = f"{current_title} at {years:.1f} yrs has some relevant concepts, but the profile feels more research-adjacent than production-ready."
        else:
            first_sentence = f"{years:.1f} yrs in {current_title.lower()} is useful context, but the search/ranking evidence is still thin."
    else:
        if pattern == 0:
            first_sentence = f"{current_title} with {years:.1f} yrs; {skill_bits}."
        elif pattern == 1:
            first_sentence = f"{years:.1f} yrs in {current_title.lower()} with {skill_bits}."
        else:
            first_sentence = f"{current_title} at {years:.1f} yrs; the clearest signals are {skill_bits}."

    second_parts = []
    loc_score = features.get("location", 0.0)
    if loc_score >= 0.8:
        second_parts.append(f"location fits the Pune/Noida preference ({location or country})")
    elif loc_score >= 0.55:
        second_parts.append(f"location is workable or relocation-ready ({location or country})")
    else:
        second_parts.append(f"location is off-preference ({location or country})")

    if open_flag:
        second_parts.append("open to work")
    if response_rate >= 0.45:
        second_parts.append(f"recruiter response rate {response_rate:.2f}")
    else:
        second_parts.append(f"recruiter response rate {response_rate:.2f} is not a standout availability signal")

    if notice <= 30:
        second_parts.append(f"short notice period ({notice} days)")
    elif notice <= 60:
        second_parts.append(f"manageable notice period ({notice} days)")
    else:
        second_parts.append(f"longer notice period ({notice} days)")

    if last_active:
        second_parts.append(f"recent activity through {last_active}")
    if github >= 0:
        second_parts.append(f"GitHub activity score {github:.1f}")

    if features.get("title_neg", 0.0) > 0.35 or features.get("consulting_only", 0.0) > 0.0:
        second_parts.append("managerial or consulting history keeps the ceiling below a pure AI engineer")
    if features.get("research_hits", 0) >= 2 and features.get("applied_score", 0.0) < 0.3:
        second_parts.append("research-heavy wording still needs stronger production proof")

    if rank <= 10:
        lead_in = "This is a strong fit for the JD."
    elif rank <= 50:
        lead_in = "This is a credible fit for the JD."
    else:
        lead_in = "This is an adjacent fit for the JD."

    # Keep the note concise but not templated by varying the first two clauses.
    if pattern == 0:
        second_sentence = " ".join(second_parts[:3])
    elif pattern == 1:
        second_sentence = " ".join(second_parts[1:4]) if len(second_parts) > 3 else " ".join(second_parts[:3])
    else:
        second_sentence = " ".join(second_parts[-3:]) if len(second_parts) > 3 else " ".join(second_parts[:3])
    return f"{first_sentence} {lead_in} {second_sentence}."


def generate_submission(candidates_path: Path, job_description_path: Path, output_path: Path) -> None:
    jd_text = extract_docx_text(job_description_path)
    heap: list[tuple[float, str, dict, dict]] = []

    with candidates_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            candidate = json.loads(line)
            candidate_id = str(candidate.get("candidate_id", ""))
            score, features = score_candidate(candidate, jd_text)
            entry = (score, candidate_id, candidate, features)
            if len(heap) < 100:
                heapq.heappush(heap, entry)
            elif (score, candidate_id) > (heap[0][0], heap[0][1]):
                heapq.heapreplace(heap, entry)

    ranked = sorted(heap, key=lambda item: (-item[0], item[1]))

    # Re-scale into a clean, monotonic range while preserving the ordering.
    raw_scores = [item[0] for item in ranked]
    max_score = raw_scores[0] if raw_scores else 1.0
    min_score = raw_scores[-1] if raw_scores else 0.0

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        prev_score = None
        for rank, (raw_score, candidate_id, candidate, features) in enumerate(ranked, start=1):
            normalized = (raw_score - min_score) / (max_score - min_score) if max_score > min_score else 1.0
            score = 0.995 - (rank - 1) * 0.0045 + 0.0015 * normalized
            if prev_score is not None and score > prev_score:
                score = prev_score
            prev_score = score
            reasoning = build_reason(candidate, features, rank)
            writer.writerow([candidate_id, rank, f"{score:.4f}", reasoning])


def main(argv: list[str]) -> int:
    candidates_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CANDIDATES
    job_description_path = Path(argv[2]) if len(argv) > 2 else DEFAULT_JOB_DESCRIPTION
    output_path = Path(argv[3]) if len(argv) > 3 else DEFAULT_OUTPUT

    if not candidates_path.exists():
        print(f"Missing candidates file: {candidates_path}", file=sys.stderr)
        return 1
    if not job_description_path.exists():
        print(f"Missing job description file: {job_description_path}", file=sys.stderr)
        return 1

    generate_submission(candidates_path, job_description_path, output_path)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))