"""
llm_engine.py — LLM provider orchestration for RecruiterIQ.
Supports Google Gemini, Anthropic Claude, and OpenAI GPT.
Allows re-ranking the top candidate shortlist and structured JD parsing.
"""
from __future__ import annotations
import json
import re
from typing import List, Optional, Dict, Any

# We load SDKs dynamically to avoid crash if some package is missing
def get_gemini_client(api_key: str):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai

def clean_json_string(text: str) -> str:
    """Helper to extract JSON from markdown code blocks if the LLM wraps it."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text

# ── JD Parsing with LLM ────────────────────────────────────────────────────────

JD_PARSE_PROMPT = """
You are a highly analytical technical recruiter. Your task is to parse the following raw Job Description (JD) and convert it into a strictly structured JSON format matching the schema below.

Job Description text:
\"\"\"
{jd_text}
\"\"\"

Output format must be a single JSON object. Do not include markdown code block formatting (like ```json), do not write any introductions or summaries. Output ONLY the raw JSON string with these fields:
{{
  "role_title": "string (Title of the job)",
  "seniority_level": "string (Must be one of: junior, mid, senior, staff, principal, manager)",
  "seniority_years_min": int or null (minimum required years of experience),
  "seniority_years_max": int or null (maximum expected years of experience),
  "work_mode": "string (Must be one of: remote, hybrid, onsite, flexible)",
  "domain_industry": ["string" (list of industries/domains e.g. Fintech, SaaS, etc.)],
  "must_have_skills": ["string" (list of specific must-have technical/functional skills mentioned)],
  "nice_to_have_skills": ["string" (list of preferred/nice-to-have skills)],
  "behavioral_signals": ["string" (list of soft skills/behavioral expectations like ownership, scale, self-starter)],
  "cultural_signals": ["string" (list of cultural indicators)],
  "role_intent_summary": "string (1-2 sentences capturing the core technical challenge and mandate of this role)"
}}
"""

def parse_jd_with_llm(jd_text: str, provider: str, api_key: str) -> dict:
    prompt = JD_PARSE_PROMPT.format(jd_text=jd_text)
    
    if provider == "gemini":
        genai = get_gemini_client(api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        raw_output = response.text
    
    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw_output = response.choices[0].message.content
        
    elif provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        raw_output = response.content[0].text
        
    elif provider == "grok":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.xai.com/v1")
        response = client.chat.completions.create(
            model="grok-2-1212",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw_output = response.choices[0].message.content
        
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    cleaned = clean_json_string(raw_output)
    try:
        return json.loads(cleaned)
    except Exception as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw output: {raw_output}")


# ── Candidate Re-ranking with LLM ──────────────────────────────────────────────

RERANK_PROMPT = """
You are a Lead Talent Acquisition Partner conducting the final deep-reasoning review of a candidate shortlist.
Below are the details of the Job Description and a list of the top candidates.

Job Description Profile:
- Title: {role_title}
- Seniority: {seniority_level} (Expected Experience: {years_min}-{years_max} yrs)
- Work Mode: {work_mode}
- Intent: {intent_summary}
- Must-Have Skills: {must_skills}
- Nice-to-Have Skills: {nice_skills}

Candidates list (Top 30 candidates to evaluate):
{candidates_json}

Your task:
Evaluate each candidate critically. You must adjust their composite score (0 to 100) based on their actual match, career growth velocity, relative alignment of skills/roles, and sourcing signals (availability, response rates, GitHub activity).
Write a professional 2-sentence recruiter rationale (strictly with ZERO emojis) summarizing:
1. The primary alignment/strength of their profile.
2. A key gap or risk to probe in the interview.
Also generate one targeted interview probe question.

Return a JSON list of objects. Do not include markdown code block formatting (like ```json), do not write any introductory or trailing text. Output ONLY the raw JSON array containing objects matching this schema:
[
  {{
    "candidate_id": "string",
    "new_score": float (adjusted score between 0.0 and 100.0),
    "recruiter_rationale": "string (exactly 2 sentences, no emojis)",
    "interview_probe": "string (one clear interview question)"
  }},
  ...
]
"""

def rerank_candidates_with_llm(
    jd_profile: dict,
    candidates: List[dict],
    provider: str,
    api_key: str
) -> List[dict]:
    # Construct prompt inputs
    must_skills = ", ".join([s.get("name", "") for s in jd_profile.get("must_have_skills", [])])
    nice_skills = ", ".join([s.get("name", "") for s in jd_profile.get("nice_to_have_skills", [])])
    
    # We only feed necessary details to fit context windows efficiently
    candidates_input = []
    for c in candidates:
        sig = c.get("redrob_signals") or {}
        candidates_input.append({
            "candidate_id": c["candidate_id"],
            "name": c["name"],
            "current_title": c["current_title"],
            "current_company": c["current_company"],
            "total_experience_years": c["total_experience_years"],
            "top_skills": c["top_skills"][:10],
            "career_history": [
                {
                    "title": e.get("title"),
                    "company": e.get("company"),
                    "duration_months": e.get("duration_months"),
                    "is_current": e.get("is_current")
                } for e in c.get("career_history", [])[:3]
            ],
            "open_to_work": sig.get("open_to_work_flag", False),
            "notice_period_days": sig.get("notice_period_days", 90),
            "github_score": sig.get("github_activity_score", -1),
        })

    prompt = RERANK_PROMPT.format(
        role_title=jd_profile.get("role_title", "Unknown"),
        seniority_level=jd_profile.get("seniority_level", "mid"),
        years_min=jd_profile.get("seniority_years_min", 3),
        years_max=jd_profile.get("seniority_years_max", 7),
        work_mode=jd_profile.get("work_mode", "hybrid"),
        intent_summary=jd_profile.get("role_intent_summary", ""),
        must_skills=must_skills,
        nice_skills=nice_skills,
        candidates_json=json.dumps(candidates_input, indent=2)
    )

    if provider == "gemini":
        genai = get_gemini_client(api_key)
        # Use gemini-1.5-pro or gemini-2.0-flash for deep reasoning tasks
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        raw_output = response.text

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        raw_output = response.choices[0].message.content

    elif provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        raw_output = response.content[0].text
        
    elif provider == "grok":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.xai.com/v1")
        response = client.chat.completions.create(
            model="grok-2-1212",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        raw_output = response.choices[0].message.content
        
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    cleaned = clean_json_string(raw_output)
    try:
        return json.loads(cleaned)
    except Exception as e:
        raise ValueError(f"LLM reranker returned invalid JSON: {e}\nRaw output: {raw_output}")
