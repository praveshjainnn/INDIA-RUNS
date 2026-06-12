"use client";
import { useState } from "react";
import type { RankedCandidate, JDProfile } from "@/lib/types";
import { TIER_CONFIG } from "@/lib/types";
import RadarChart from "./RadarChart";

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="text-[10px] uppercase font-bold text-slate-400 w-32 shrink-0">{label}</span>
      <div className="flex-1 h-2 rounded bg-slate-100 overflow-hidden">
        <div className="h-full rounded transition-all duration-500"
          style={{ width: `${Math.min(100, value)}%`, background: color }} />
      </div>
      <span className="text-xs font-mono font-bold text-slate-500 w-8 text-right">{value.toFixed(0)}</span>
    </div>
  );
}

function TierBadge({ tier }: { tier: RankedCandidate["score_tier"] }) {
  const cfg = TIER_CONFIG[tier];
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
      style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: cfg.color }} />
      {cfg.label}
    </span>
  );
}

function SkillChip({ label, matched }: { label: string; matched?: boolean }) {
  return (
    <span className="inline-block px-2.5 py-0.5 rounded text-[10px] font-semibold mr-1.5 mb-1.5 border"
      style={matched
        ? { background: "rgba(68,172,255,0.06)", color: "#1A8FE8", borderColor: "rgba(68,172,255,0.2)" }
        : { background: "rgba(254,158,199,0.06)", color: "#FC6FA8", borderColor: "rgba(254,158,199,0.2)" }}>
      {label}
    </span>
  );
}

function CareerTimeline({ history }: { history: RankedCandidate["career_history"] }) {
  return (
    <div className="relative pl-5">
      <div className="absolute left-1.5 top-1 bottom-1 w-0.5 rounded bg-slate-200" />
      {history.map((e, i) => (
        <div key={i} className="relative mb-4">
          <div className="absolute -left-[18px] top-1.5 w-2 h-2 rounded-full border-2 border-white"
            style={{ background: i === 0 ? "#44ACFF" : "#cbd5e1" }} />
          <div className="font-semibold text-xs text-slate-700">{e.title}</div>
          <div className="text-[10px] text-slate-400 font-semibold mt-0.5">
            {e.company} · {e.industry} · {e.duration_months > 0 ? `${e.duration_months} months` : ""}
            {e.is_current && <span className="ml-1 text-emerald-600 font-bold">· Current</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

interface Props { rc: RankedCandidate; jd: JDProfile; }

export default function CandidateCard({ rc, jd }: Props) {
  const [expanded, setExpanded] = useState(false);
  const tier = TIER_CONFIG[rc.score_tier];
  const jdSkillNames = new Set(jd.must_have_skills.map(s => s.name.toLowerCase()));

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200">
      
      {/* Top tier color stripe */}
      <div className="h-1.5 w-full" style={{ background: tier.color }} />

      {/* Main Container */}
      <div className="p-6">
        <div className="flex items-start gap-4">
          {/* Rank ID */}
          <div className="shrink-0 w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm bg-slate-100 text-slate-600 border border-slate-200">
            #{rc.rank}
          </div>

          <div className="flex-1 min-w-0">
            {/* Header / Meta */}
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <h3 className="font-bold text-slate-800 text-base">{rc.name || rc.candidate_id}</h3>
                <div className="flex items-center gap-2 flex-wrap text-xs text-slate-500 mt-1">
                  <span>{rc.current_title}</span>
                  {rc.current_company && <span>at {rc.current_company}</span>}
                  <span>·</span>
                  <span>{rc.total_experience_years.toFixed(1)} yrs experience</span>
                  {rc.location && (
                    <>
                      <span>·</span>
                      <span className="flex items-center gap-1">
                        <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        {rc.location}
                      </span>
                    </>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-3 shrink-0">
                <TierBadge tier={rc.score_tier} />
                <div className="text-right">
                  <div className="font-mono font-bold text-lg text-slate-800">
                    {rc.composite_score.toFixed(1)}
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase font-semibold">/ 100</div>
                </div>
              </div>
            </div>

            {/* Quick Metrics */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1">
              <ScoreBar label="Skill Alignment" value={rc.skill_alignment} color="#FE9EC7" />
              <ScoreBar label="Experience" value={rc.experience_relevance} color="#44ACFF" />
              <ScoreBar label="Career Signal" value={rc.career_signal} color="#89D4FF" />
              <ScoreBar label="Behavioral Fit" value={rc.behavioral_fit} color="#FC6FA8" />
            </div>

            {/* Rationale text preview */}
            {rc.recruiter_rationale && (
              <div className="mt-4 border-l-2 pl-3 py-0.5 text-xs text-slate-500 leading-relaxed italic"
                style={{ borderColor: tier.color }}>
                {rc.recruiter_rationale}
              </div>
            )}

            {/* Badges / Signals */}
            <div className="mt-4 flex flex-wrap gap-2">
              {rc.open_to_work && (
                <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-200">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  Open to Work
                </span>
              )}
              {rc.notice_period_days <= 30 && (
                <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-50 text-amber-600 border border-amber-200">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {rc.notice_period_days}d notice
                </span>
              )}
              {rc.github_score >= 0 && (
                <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-200">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  GitHub {rc.github_score.toFixed(0)}
                </span>
              )}
              {rc.preferred_mode && (
                <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-pink-50 text-pink-600 border border-pink-200">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                  {rc.preferred_mode}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Expand Trigger Button */}
        <button 
          onClick={() => setExpanded(!expanded)}
          className="mt-5 w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-bold bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-600 transition-all">
          {expanded ? (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
              </svg>
              Collapse Profile
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
              View Full Profile
            </>
          )}
        </button>
      </div>

      {/* Expanded Profile Details */}
      {expanded && (
        <div className="border-t border-slate-150 bg-slate-50/40 px-6 pb-6">
          <div className="grid md:grid-cols-2 gap-8 pt-6">
            
            {/* Left Column: Skill chart & chips */}
            <div className="space-y-4">
              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <RadarChart rc={rc} />
              </div>
              <div>
                <h4 className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-2">Matched Skills</h4>
                <div className="flex flex-wrap">
                  {rc.top_skills.map(s => (
                    <SkillChip key={s} label={s} matched={jdSkillNames.has(s.toLowerCase())} />
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column: Detailed parameters */}
            <div className="space-y-5">
              {/* Career timeline */}
              {rc.career_history.length > 0 && (
                <div>
                  <h4 className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-3">Career History</h4>
                  <CareerTimeline history={rc.career_history} />
                </div>
              )}

              {/* Education */}
              {rc.education.length > 0 && (
                <div>
                  <h4 className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-2">Education</h4>
                  <div className="space-y-2">
                    {rc.education.map((e, i) => (
                      <div key={i} className="text-xs text-slate-600 bg-white border border-slate-200 rounded-lg p-2.5">
                        <div className="font-semibold text-slate-800">{e.degree} in {e.field_of_study || e.field}</div>
                        <div className="text-[10px] text-slate-500 font-semibold mt-0.5">
                          {e.institution} {e.end_year ? `· Graduated ${e.end_year}` : ""}
                          {e.tier !== "unknown" && (
                            <span className="ml-2 inline-block px-1.5 py-0.5 rounded text-[8px] font-bold bg-blue-50 text-blue-600 border border-blue-150 uppercase tracking-wider">
                              {e.tier}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Detailed platform rates */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-2.5">
                <h4 className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Sourcing Metrics</h4>
                <div className="grid grid-cols-2 gap-y-2 text-xs">
                  <span className="text-slate-400 font-semibold">Response Rate</span>
                  <span className="font-bold text-slate-700 text-right">{(rc.response_rate * 100).toFixed(0)}%</span>
                  
                  <span className="text-slate-400 font-semibold">Notice Period</span>
                  <span className="font-bold text-slate-700 text-right">{rc.notice_period_days} days</span>
                  
                  {rc.github_score >= 0 && (
                    <>
                      <span className="text-slate-400 font-semibold">GitHub Activity</span>
                      <span className="font-bold text-slate-700 text-right">{rc.github_score.toFixed(0)}</span>
                    </>
                  )}
                  
                  <span className="text-slate-400 font-semibold">Semantic Sim.</span>
                  <span className="font-mono font-bold text-slate-700 text-right">{(rc.semantic_similarity * 100).toFixed(1)}%</span>
                </div>
              </div>

              {/* Notes */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 border-l-4" style={{ borderLeftColor: "#44ACFF" }}>
                <h4 className="text-[10px] uppercase font-bold text-blue-500 tracking-wider mb-1">Recruiter Notes</h4>
                <p className="text-xs text-slate-600 leading-relaxed italic">{rc.recruiter_rationale}</p>
              </div>

              {/* Probe */}
              {rc.probe_question && (
                <div className="bg-white border border-slate-200 rounded-lg p-4 border-l-4" style={{ borderLeftColor: "#F59E0B" }}>
                  <h4 className="text-[10px] uppercase font-bold text-amber-600 tracking-wider mb-1">Interview Probe</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">{rc.probe_question}</p>
                </div>
              )}

              {/* Top Strength */}
              {rc.top_strength && (
                <div className="text-xs text-slate-500 font-medium flex gap-2 items-start bg-white border border-slate-200 rounded-lg p-3">
                  <svg className="w-4 h-4 text-emerald-500 shrink-0" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  <span><strong>Primary Strength:</strong> {rc.top_strength}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
