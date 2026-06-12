"""FastAPI backend for RecruiterIQ — serves the Next.js frontend."""
from __future__ import annotations
import os
import sys

# Suppress TensorFlow / protobuf version noise — we use PyTorch only
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
import io
import uuid
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from recruiteriq.pipeline.jd_parser import parse_jd
from recruiteriq.pipeline.candidate_loader import load_candidates
from recruiteriq.pipeline.feature_extractor import enrich_candidate
from recruiteriq.pipeline.fast_scorer import fast_score_candidate
from recruiteriq.pipeline.embedder import embed_text, embed_batch
from recruiteriq.pipeline.scorer import build_ranked_candidate
from recruiteriq.pipeline.rationale_builder import enrich_with_rationale
from recruiteriq.submission_builder import build_submission_csv, build_submission_xlsx
from recruiteriq.models.schemas import RankedCandidate
from recruiteriq.config import FAST_PATH_TOP_N, SHORTLIST_SIZE, SAMPLE_CANDIDATES, CANDIDATES_JSONL

app = FastAPI(title="RecruiterIQ API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins or specify React port 3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store
jobs: Dict[str, Dict] = {}

# ── Request models ────────────────────────────────────────────────────────────

class ParseJDRequest(BaseModel):
    jd_text: str

class StartRankRequest(BaseModel):
    jd_text: str
    use_sample: bool = True
    dataset_path: Optional[str] = None
    api_provider: Optional[str] = "none"
    api_key: Optional[str] = None

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".json", ".jsonl"]:
        raise HTTPException(400, "Only .json and .jsonl files are supported")
    
    uploads_dir = ROOT / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    
    file_id = str(uuid.uuid4())
    save_path = uploads_dir / f"{file_id}{ext}"
    
    try:
        contents = await file.read()
        save_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(500, f"Failed to save uploaded file: {str(e)}")
        
    return {"dataset_path": str(save_path), "filename": file.filename}


@app.post("/api/parse-jd")
async def parse_jd_endpoint(req: ParseJDRequest):
    if not req.jd_text or len(req.jd_text.split()) < 20:
        raise HTTPException(400, "JD too short — add more detail")
    jd = parse_jd(req.jd_text)
    return {
        "role_title": jd.role_title,
        "seniority_level": jd.seniority_level,
        "seniority_years_min": jd.seniority_years_min,
        "seniority_years_max": jd.seniority_years_max,
        "work_mode": jd.work_mode,
        "domain_industry": jd.domain_industry,
        "must_have_skills": [{"name": s.name} for s in jd.must_have_skills],
        "nice_to_have_skills": [{"name": s.name} for s in jd.nice_to_have_skills],
        "behavioral_signals": jd.behavioral_signals,
        "role_intent_summary": jd.role_intent_summary,
    }


@app.post("/api/rank/start")
async def start_ranking(req: StartRankRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running", "progress": 0, "message": "Starting...",
        "jd_profile": None, "results": None, "total_candidates": 0, "error": None,
    }
    
    if req.dataset_path:
        resolved_path = Path(req.dataset_path).resolve()
        uploads_dir = (ROOT / "uploads").resolve()
        try:
            resolved_path.relative_to(uploads_dir)
        except ValueError:
            raise HTTPException(400, "Invalid dataset path")
        candidates_path = resolved_path
        if not candidates_path.exists():
            raise HTTPException(400, "Uploaded dataset file not found")
    else:
        candidates_path = SAMPLE_CANDIDATES if req.use_sample else CANDIDATES_JSONL
        
    background_tasks.add_task(
        _run_pipeline_bg, 
        job_id, 
        req.jd_text, 
        candidates_path, 
        req.api_provider, 
        req.api_key
    )
    return {"job_id": job_id}


@app.get("/api/rank/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "total_candidates": job["total_candidates"],
        "error": job["error"],
        "jd_profile": job["jd_profile"] if job["status"] == "done" else None,
        "result_count": len(job["results"] or []) if job["status"] == "done" else 0,
    }


@app.get("/api/rank/results/{job_id}")
async def get_results(job_id: str, limit: int = 100):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "done":
        raise HTTPException(400, f"Job not complete: {job['status']}")
    results = job["results"] or []
    return {
        "jd_profile": job["jd_profile"],
        "total_candidates": job["total_candidates"],
        "ranked": [_rc_to_dict(rc) for rc in results[:limit]],
    }


@app.get("/api/download/csv/{job_id}")
async def download_csv(job_id: str):
    job = jobs.get(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Results not ready")
    results: List[RankedCandidate] = job["results"] or []
    
    csv_content = build_submission_csv(results)
    role = (job.get("jd_profile") or {}).get("role_title", "results")
    clean_role = re.sub(r"[^\w\-]", "_", role.lower())
    clean_role = re.sub(r"_+", "_", clean_role).strip("_")
    filename = f"submission_{clean_role}.csv"
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/download/xlsx/{job_id}")
async def download_xlsx(job_id: str):
    job = jobs.get(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Results not ready")
    results: List[RankedCandidate] = job["results"] or []
    
    xlsx_bytes = build_submission_xlsx(results)
    role = (job.get("jd_profile") or {}).get("role_title", "results")
    clean_role = re.sub(r"[^\w\-]", "_", role.lower())
    clean_role = re.sub(r"_+", "_", clean_role).strip("_")
    filename = f"recruiteriq_{clean_role}.xlsx"
    
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Background pipeline ───────────────────────────────────────────────────────

async def _run_pipeline_bg(
    job_id: str,
    jd_text: str,
    candidates_path: Path,
    llm_provider: Optional[str] = None,
    api_key: Optional[str] = None
):
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _sync_pipeline, job_id, jd_text, candidates_path, llm_provider, api_key)
    except Exception as e:
        jobs[job_id].update({"status": "error", "error": str(e), "message": f"Error: {e}"})


def _upd(job_id: str, pct: int, msg: str, **kw):
    if job_id in jobs:
        jobs[job_id].update({"progress": pct, "message": msg, **kw})


def _sync_pipeline(
    job_id: str,
    jd_text: str,
    candidates_path: Path,
    llm_provider: Optional[str] = None,
    api_key: Optional[str] = None
):
    import re
    from recruiteriq.pipeline.pipeline import run_pipeline

    def on_progress(msg: str, pct_0_to_1: float):
        total_candidates = 0
        if "process" in msg.lower() or "score" in msg.lower():
            try:
                nums = re.findall(r"[\d,]+", msg)
                if nums:
                    total_candidates = int(nums[0].replace(",", ""))
            except:
                pass
        
        kwargs = {}
        if total_candidates > 0:
            kwargs["total_candidates"] = total_candidates
            
        _upd(job_id, int(pct_0_to_1 * 100), msg, **kwargs)

    jd, ranked = run_pipeline(
        jd_text=jd_text,
        candidates_path=candidates_path,
        shortlist_size=SHORTLIST_SIZE,
        on_progress=on_progress,
        llm_provider=llm_provider,
        api_key=api_key
    )

    jd_dict = {
        "role_title": jd.role_title,
        "seniority_level": jd.seniority_level,
        "work_mode": jd.work_mode,
        "domain_industry": jd.domain_industry,
        "must_have_skills": [{"name": s.name} for s in jd.must_have_skills],
        "nice_to_have_skills": [{"name": s.name} for s in jd.nice_to_have_skills],
        "behavioral_signals": jd.behavioral_signals,
        "seniority_years_min": jd.seniority_years_min,
        "seniority_years_max": jd.seniority_years_max,
    }
    
    # Extract total_candidates from final run status or fallback to length of dataset
    fallback_total = 100 if "sample" in str(candidates_path).lower() else 487259
    total = jobs[job_id].get("total_candidates", 0) or fallback_total

    jobs[job_id].update({
        "status": "done", "progress": 100, "message": "Analysis complete!",
        "results": ranked, "jd_profile": jd_dict, "total_candidates": total,
    })


def _rc_to_dict(rc: RankedCandidate) -> dict:
    sig = rc.redrob_signals
    return {
        "rank": rc.rank,
        "candidate_id": rc.candidate_id,
        "name": rc.name,
        "current_title": rc.current_title,
        "current_company": rc.current_company,
        "total_experience_years": rc.total_experience_years,
        "composite_score": round(rc.scores.composite, 2),
        "skill_alignment": round(rc.scores.skill_alignment, 2),
        "experience_relevance": round(rc.scores.experience_relevance, 2),
        "career_signal": round(rc.scores.career_signal, 2),
        "behavioral_fit": round(rc.scores.behavioral_fit, 2),
        "cultural_alignment": round(rc.scores.cultural_alignment, 2),
        "score_tier": rc.score_tier,
        "top_skills": rc.top_skills,
        "recruiter_rationale": rc.recruiter_rationale,
        "top_strength": rc.top_strength,
        "probe_question": rc.probe_question,
        "semantic_similarity": round(rc.semantic_similarity, 4),
        "location": rc.raw_features.get("location", ""),
        "country": rc.raw_features.get("country", ""),
        "open_to_work": sig.open_to_work_flag if sig else False,
        "notice_period_days": sig.notice_period_days if sig else 90,
        "github_score": sig.github_activity_score if sig else -1,
        "response_rate": round(sig.recruiter_response_rate, 2) if sig else 0,
        "preferred_mode": sig.preferred_work_mode if sig else "flexible",
        "career_history": [
            {"title": e.title, "company": e.company, "duration_months": e.duration_months,
             "industry": e.industry, "start_date": e.start_date, "end_date": e.end_date,
             "is_current": e.is_current}
            for e in rc.career_history[:5]
        ],
        "education": [
            {"degree": e.degree, "field": e.field_of_study,
             "institution": e.institution, "tier": e.tier, "end_year": e.end_year}
            for e in rc.education
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
