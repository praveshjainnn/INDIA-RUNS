"""Pydantic schemas for all data models in RecruiterIQ."""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ── Job Description Models ────────────────────────────────────────────────────

class SkillRequirement(BaseModel):
    name: str
    proficiency: str = "proficient"  # familiar | proficient | expert
    years_min: Optional[int] = None

class JobDescriptionProfile(BaseModel):
    raw_text: str = ""
    role_title: str = "Unknown Role"
    seniority_level: str = "mid"          # junior|mid|senior|staff|principal|manager
    seniority_years_min: Optional[int] = None
    seniority_years_max: Optional[int] = None
    employment_type: str = "fulltime"
    work_mode: str = "hybrid"
    domain_industry: List[str] = Field(default_factory=list)
    domain_function: str = ""
    must_have_skills: List[SkillRequirement] = Field(default_factory=list)
    nice_to_have_skills: List[SkillRequirement] = Field(default_factory=list)
    behavioral_signals: List[str] = Field(default_factory=list)
    cultural_signals: List[str] = Field(default_factory=list)
    role_intent_summary: str = ""
    embedding_text: str = ""


# ── Candidate Models ──────────────────────────────────────────────────────────

class CareerEntry(BaseModel):
    company: str = ""
    title: str = ""
    industry: str = ""
    company_size: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: int = 0
    is_current: bool = False
    description: str = ""

class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade: Optional[str] = None
    tier: str = "unknown"  # tier_1 | tier_2 | tier_3 | tier_4 | unknown

class Skill(BaseModel):
    name: str = ""
    proficiency: str = "intermediate"
    endorsements: int = 0
    duration_months: int = 0

class RedrobSignals(BaseModel):
    profile_completeness_score: float = 0.0
    open_to_work_flag: bool = False
    last_active_date: Optional[str] = None
    recruiter_response_rate: float = 0.0
    avg_response_time_hours: float = 240.0
    notice_period_days: int = 90
    preferred_work_mode: str = "flexible"
    willing_to_relocate: bool = False
    github_activity_score: float = -1.0
    connection_count: int = 0
    endorsements_received: int = 0
    skill_assessment_scores: Dict[str, float] = Field(default_factory=dict)
    interview_completion_rate: float = 0.0
    offer_acceptance_rate: float = -1.0
    verified_email: bool = False
    verified_phone: bool = False
    linkedin_connected: bool = False
    profile_views_received_30d: int = 0
    saved_by_recruiters_30d: int = 0
    expected_salary_range_inr_lpa: Dict[str, float] = Field(default_factory=lambda: {"min": 0, "max": 0})

class DerivedSignals(BaseModel):
    total_experience_years: float = 0.0
    career_velocity_score: float = 0.0
    avg_tenure_months: float = 0.0
    tenure_consistency: float = 0.0
    domain_depth_score: float = 0.0
    platform_activity_score: float = 0.0
    seniority_estimate: str = "mid"

class CandidateProfile(BaseModel):
    candidate_id: str
    name: str = ""
    current_title: str = ""
    current_company: str = ""
    current_industry: str = ""
    location: str = ""
    country: str = ""
    years_of_experience: float = 0.0
    headline: str = ""
    summary: str = ""
    career_history: List[CareerEntry] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    redrob_signals: RedrobSignals = Field(default_factory=RedrobSignals)
    derived: Optional[DerivedSignals] = None
    narrative_text: str = ""
    embedding_vector: Optional[List[float]] = None


# ── Ranked Candidate (output) ─────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    composite: float = 0.0
    skill_alignment: float = 0.0
    experience_relevance: float = 0.0
    career_signal: float = 0.0
    behavioral_fit: float = 0.0
    cultural_alignment: float = 0.0

class RankedCandidate(BaseModel):
    rank: int = 0
    candidate_id: str
    name: str = ""
    current_title: str = ""
    current_company: str = ""
    total_experience_years: float = 0.0
    top_skills: List[str] = Field(default_factory=list)
    scores: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    score_tier: str = "stretch"           # strong_match|good_match|possible|stretch
    semantic_similarity: float = 0.0
    recruiter_rationale: str = ""
    top_strength: str = ""
    probe_question: str = ""
    career_history: List[CareerEntry] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    redrob_signals: Optional[RedrobSignals] = None
    raw_features: Dict[str, Any] = Field(default_factory=dict)

    def to_csv_row(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "rank": self.rank,
            "score": round(self.scores.composite / 100, 4),
            "reasoning": self.recruiter_rationale,
        }
