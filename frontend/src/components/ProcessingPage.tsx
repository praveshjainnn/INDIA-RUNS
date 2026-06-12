"use client";
import { useEffect, useState } from "react";
import { getJobStatus } from "@/lib/api";
import type { JobStatus } from "@/lib/types";

interface StepConfig {
  pct: number;
  label: string;
  renderIcon: (active: boolean, done: boolean) => React.ReactNode;
}

const STEPS: StepConfig[] = [
  { 
    pct: 5,  
    label: "Parsing job description", 
    renderIcon: (active, done) => (
      <svg className={`w-4 h-4 ${done ? "text-emerald-500" : active ? "text-blue-500" : "text-slate-400"}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    )
  },
  { 
    pct: 10, 
    label: "Fast-scoring all candidates", 
    renderIcon: (active, done) => (
      <svg className={`w-4 h-4 ${done ? "text-emerald-500" : active ? "text-blue-500" : "text-slate-400"}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
      </svg>
    )
  },
  { 
    pct: 48, 
    label: "Top candidates shortlisted", 
    renderIcon: (active, done) => (
      <svg className={`w-4 h-4 ${done ? "text-emerald-500" : active ? "text-blue-500" : "text-slate-400"}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )
  },
  { 
    pct: 52, 
    label: "Computing semantic similarity", 
    renderIcon: (active, done) => (
      <svg className={`w-4 h-4 ${done ? "text-emerald-500" : active ? "text-blue-500" : "text-slate-400"}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    )
  },
  { 
    pct: 75, 
    label: "Multi-dimensional scoring", 
    renderIcon: (active, done) => (
      <svg className={`w-4 h-4 ${done ? "text-emerald-500" : active ? "text-blue-500" : "text-slate-400"}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.907c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.907a1 1 0 00.95-.69l1.519-4.674z" />
      </svg>
    )
  },
  { 
    pct: 90, 
    label: "Generating rationale & probe questions", 
    renderIcon: (active, done) => (
      <svg className={`w-4 h-4 ${done ? "text-emerald-500" : active ? "text-blue-500" : "text-slate-400"}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      </svg>
    )
  },
  { 
    pct: 100, 
    label: "Analysis complete", 
    renderIcon: (active, done) => (
      <svg className={`w-4 h-4 ${done ? "text-emerald-500" : active ? "text-blue-500" : "text-slate-400"}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    )
  },
];

interface Props {
  jobId: string;
  useSample: boolean;
  onDone: () => void;
  onError: (msg: string) => void;
}

export default function ProcessingPage({ jobId, useSample, onDone, onError }: Props) {
  const [status, setStatus] = useState<JobStatus>({ status: "running", progress: 0, message: "Starting...", total_candidates: 0, error: null });

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      while (!cancelled) {
        try {
          const s = await getJobStatus(jobId);
          if (!cancelled) setStatus(s);
          if (s.status === "done") { onDone(); return; }
          if (s.status === "error") { onError(s.error || "Unknown error"); return; }
        } catch (e: any) {
          if (!cancelled) onError(e.message);
          return;
        }
        await new Promise(r => setTimeout(r, 1200));
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [jobId]);

  const pct = status.progress;

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center relative">
      <div className="w-full max-w-xl mx-auto px-6 z-10">
        <div className="bg-white rounded-xl border border-slate-200 p-8 shadow-sm text-center">
          
          {/* Animated Spinner Icon */}
          <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center relative">
            <div className="absolute inset-0 rounded-full border-4 border-slate-100 border-t-blue-500 animate-spin" />
            <svg className="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>

          <h2 className="text-xl font-bold text-slate-800 mb-1">Analyzing Candidates</h2>
          <p className="text-xs text-slate-400 mb-6 font-semibold uppercase tracking-wider">
            {useSample ? "Sample dataset (~100 profiles)" : "Full dataset (487K profiles)"}
            {status.total_candidates > 0 && ` · ${status.total_candidates.toLocaleString()} profiles loaded`}
          </p>

          {/* Progress bar */}
          <div className="relative mb-6">
            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div 
                className="h-full rounded-full transition-all duration-700 ease-out"
                style={{ width: `${pct}%`, background: "#44ACFF" }}
              />
            </div>
            <div className="flex justify-between mt-2 text-xs">
              <span className="font-bold text-blue-500">{pct}%</span>
              <span className="text-slate-400 italic">{status.message}</span>
            </div>
          </div>

          {/* Steps */}
          <div className="text-left space-y-2 border-t border-slate-100 pt-6">
            {STEPS.map((step, i) => {
              const done = pct >= step.pct && (i < STEPS.length - 1 ? pct < STEPS[i + 1]?.pct || pct >= 100 : true);
              const active = pct >= step.pct && (i === STEPS.length - 1 || pct < STEPS[i + 1]?.pct);
              const isDone = i < STEPS.length - 1 && pct >= STEPS[i + 1]?.pct;
              const isPending = pct < step.pct;

              return (
                <div key={i} className={`flex items-center gap-3 py-2 px-3 rounded-lg transition-all ${
                    isDone ? "bg-emerald-50/35" : active ? "bg-blue-50/30" : "transparent"
                  }`}
                  style={{ opacity: isPending ? 0.45 : 1 }}>
                  
                  {step.renderIcon(active, isDone)}
                  
                  <span className={`text-xs font-semibold ${
                      isDone ? "text-emerald-700" : active ? "text-blue-700" : "text-slate-500"
                    }`}>
                    {step.label}
                  </span>
                  
                  {isDone && (
                    <span className="ml-auto text-emerald-600 text-xs font-bold">✓</span>
                  )}
                  {active && (
                    <span className="ml-auto w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  )}
                </div>
              );
            })}
          </div>

          {/* ETA */}
          {!useSample && (
            <div className="mt-6 text-[10px] text-slate-500 leading-normal bg-slate-50 rounded-lg p-3 border border-slate-200 flex items-center justify-center gap-2">
              <svg className="w-4 h-4 text-slate-400 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Full dataset process runs strictly locally on CPU, taking 2-3 minutes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
