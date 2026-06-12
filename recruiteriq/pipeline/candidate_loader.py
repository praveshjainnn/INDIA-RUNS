"""Candidate Loader — streams candidates from JSONL or JSON file.
Handles both the full candidates.jsonl (487MB) and sample_candidates.json.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Generator, List, Optional
from ..models.schemas import (
    CandidateProfile, CareerEntry, Education, Skill, RedrobSignals
)


def _parse_career_history(raw: list) -> List[CareerEntry]:
    entries = []
    for item in (raw or []):
        entries.append(CareerEntry(
            company=str(item.get("company", "") or ""),
            title=str(item.get("title", "") or ""),
            industry=str(item.get("industry", "") or ""),
            company_size=str(item.get("company_size", "") or ""),
            start_date=item.get("start_date"),
            end_date=item.get("end_date"),
            duration_months=int(item.get("duration_months") or 0),
            is_current=bool(item.get("is_current", False)),
            description=str(item.get("description", "") or ""),
        ))
    return entries


def _parse_education(raw: list) -> List[Education]:
    entries = []
    for item in (raw or []):
        entries.append(Education(
            institution=str(item.get("institution", "") or ""),
            degree=str(item.get("degree", "") or ""),
            field_of_study=str(item.get("field_of_study", "") or ""),
            start_year=item.get("start_year"),
            end_year=item.get("end_year"),
            grade=item.get("grade"),
            tier=str(item.get("tier", "unknown") or "unknown"),
        ))
    return entries


def _parse_skills(raw: list) -> List[Skill]:
    entries = []
    for item in (raw or []):
        entries.append(Skill(
            name=str(item.get("name", "") or ""),
            proficiency=str(item.get("proficiency", "intermediate") or "intermediate"),
            endorsements=int(item.get("endorsements") or 0),
            duration_months=int(item.get("duration_months") or 0),
        ))
    return entries


def _parse_redrob_signals(raw: dict) -> RedrobSignals:
    if not raw:
        return RedrobSignals()
    salary = raw.get("expected_salary_range_inr_lpa") or {}
    return RedrobSignals(
        profile_completeness_score=float(raw.get("profile_completeness_score") or 0),
        open_to_work_flag=bool(raw.get("open_to_work_flag", False)),
        last_active_date=raw.get("last_active_date"),
        recruiter_response_rate=float(raw.get("recruiter_response_rate") or 0),
        avg_response_time_hours=float(raw.get("avg_response_time_hours") or 240),
        notice_period_days=int(raw.get("notice_period_days") or 90),
        preferred_work_mode=str(raw.get("preferred_work_mode") or "flexible"),
        willing_to_relocate=bool(raw.get("willing_to_relocate", False)),
        github_activity_score=float(raw.get("github_activity_score") or -1),
        connection_count=int(raw.get("connection_count") or 0),
        endorsements_received=int(raw.get("endorsements_received") or 0),
        skill_assessment_scores=dict(raw.get("skill_assessment_scores") or {}),
        interview_completion_rate=float(raw.get("interview_completion_rate") or 0),
        offer_acceptance_rate=float(raw.get("offer_acceptance_rate") or -1),
        verified_email=bool(raw.get("verified_email", False)),
        verified_phone=bool(raw.get("verified_phone", False)),
        linkedin_connected=bool(raw.get("linkedin_connected", False)),
        profile_views_received_30d=int(raw.get("profile_views_received_30d") or 0),
        saved_by_recruiters_30d=int(raw.get("saved_by_recruiters_30d") or 0),
        expected_salary_range_inr_lpa={
            "min": float(salary.get("min") or 0),
            "max": float(salary.get("max") or 0),
        },
    )


def _parse_candidate(raw: dict) -> Optional[CandidateProfile]:
    """Convert a raw candidate dict to a CandidateProfile."""
    try:
        cid = str(raw.get("candidate_id", "") or "")
        if not cid:
            return None
        profile = raw.get("profile") or {}
        return CandidateProfile(
            candidate_id=cid,
            name=str(profile.get("anonymized_name", "") or ""),
            current_title=str(profile.get("current_title", "") or ""),
            current_company=str(profile.get("current_company", "") or ""),
            current_industry=str(profile.get("current_industry", "") or ""),
            location=str(profile.get("location", "") or ""),
            country=str(profile.get("country", "") or ""),
            years_of_experience=float(profile.get("years_of_experience") or 0),
            headline=str(profile.get("headline", "") or ""),
            summary=str(profile.get("summary", "") or ""),
            career_history=_parse_career_history(raw.get("career_history") or []),
            education=_parse_education(raw.get("education") or []),
            skills=_parse_skills(raw.get("skills") or []),
            certifications=list(raw.get("certifications") or []),
            redrob_signals=_parse_redrob_signals(raw.get("redrob_signals") or {}),
        )
    except Exception:
        return None


def stream_jsonl(path: Path, limit: Optional[int] = None) -> Generator[CandidateProfile, None, None]:
    """Stream candidates from a .jsonl file one at a time (memory efficient)."""
    count = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                candidate = _parse_candidate(raw)
                if candidate:
                    yield candidate
                    count += 1
                    if limit and count >= limit:
                        break
            except (json.JSONDecodeError, Exception):
                continue


def load_json_array(path: Path, limit: Optional[int] = None) -> Generator[CandidateProfile, None, None]:
    """Load candidates from a JSON array file (sample_candidates.json)."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        data = [data]
    for i, raw in enumerate(data):
        if limit and i >= limit:
            break
        candidate = _parse_candidate(raw)
        if candidate:
            yield candidate


def load_candidates(
    path: Path,
    limit: Optional[int] = None,
) -> Generator[CandidateProfile, None, None]:
    """Auto-detect format and stream candidates."""
    path = Path(path)
    if path.suffix == ".jsonl":
        yield from stream_jsonl(path, limit=limit)
    elif path.suffix == ".json":
        yield from load_json_array(path, limit=limit)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


def count_lines(path: Path) -> int:
    """Quickly count lines in a JSONL file for progress tracking."""
    try:
        count = 0
        with open(path, "rb") as fh:
            for _ in fh:
                count += 1
        return count
    except Exception:
        return 0
