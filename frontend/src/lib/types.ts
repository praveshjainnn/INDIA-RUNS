// Shared TypeScript types for RecruiterIQ

export interface Skill { name: string; proficiency?: string; }

export interface JDProfile {
  role_title: string;
  seniority_level: string;
  seniority_years_min: number | null;
  seniority_years_max: number | null;
  work_mode: string;
  domain_industry: string[];
  must_have_skills: Skill[];
  nice_to_have_skills: Skill[];
  behavioral_signals: string[];
  role_intent_summary?: string;
}

export interface CareerEntry {
  title: string;
  company: string;
  duration_months: number;
  industry: string;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
}

export interface Education {
  degree: string;
  field: string;
  institution: string;
  tier: string;
  end_year: number | null;
}

export interface RankedCandidate {
  rank: number;
  candidate_id: string;
  name: string;
  current_title: string;
  current_company: string;
  total_experience_years: number;
  composite_score: number;
  skill_alignment: number;
  experience_relevance: number;
  career_signal: number;
  behavioral_fit: number;
  cultural_alignment: number;
  score_tier: "strong_match" | "good_match" | "possible" | "stretch";
  top_skills: string[];
  recruiter_rationale: string;
  top_strength: string;
  probe_question: string;
  semantic_similarity: number;
  location: string;
  country: string;
  open_to_work: boolean;
  notice_period_days: number;
  github_score: number;
  response_rate: number;
  preferred_mode: string;
  career_history: CareerEntry[];
  education: Education[];
}

export interface JobStatus {
  status: "running" | "done" | "error";
  progress: number;
  message: string;
  total_candidates: number;
  error: string | null;
  jd_profile?: JDProfile;
  result_count?: number;
}

export interface RankResults {
  jd_profile: JDProfile;
  total_candidates: number;
  ranked: RankedCandidate[];
}

export type ScoreTier = "strong_match" | "good_match" | "possible" | "stretch";

export const TIER_CONFIG: Record<ScoreTier, { label: string; color: string; bg: string; border: string }> = {
  strong_match: { label: "Strong Match", color: "#16A34A", bg: "rgba(34,197,94,0.1)",  border: "rgba(34,197,94,0.3)"  },
  good_match:   { label: "Good Match",   color: "#44ACFF", bg: "rgba(68,172,255,0.1)", border: "rgba(68,172,255,0.3)" },
  possible:     { label: "Possible",     color: "#D97706", bg: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.3)" },
  stretch:      { label: "Stretch",      color: "#9CA3AF", bg: "rgba(156,163,175,0.1)",border: "rgba(156,163,175,0.3)"},
};

export const SCORE_DIMS = [
  { key: "skill_alignment",      label: "Skill Alignment",      color: "#FE9EC7", weight: "30%" },
  { key: "experience_relevance", label: "Experience Relevance",  color: "#44ACFF", weight: "25%" },
  { key: "career_signal",        label: "Career Signal",         color: "#89D4FF", weight: "20%" },
  { key: "behavioral_fit",       label: "Behavioral Fit",        color: "#F9F6C4", weight: "15%", textColor: "#92400E" },
  { key: "cultural_alignment",   label: "Cultural Alignment",    color: "#FC6FA8", weight: "10%" },
] as const;
