"use client";
import { useState, useRef } from "react";
import { startRanking, uploadDataset } from "@/lib/api";

const SAMPLE_JD = `Senior AI/ML Engineer — Search & Ranking

We're building next-generation intelligent search and recommendation systems at scale.
You will own the full ML lifecycle: from designing ranking models and evaluation frameworks
to shipping production services serving millions of users.

Requirements:
- 5+ years experience in Machine Learning or AI Engineering
- Strong Python skills with PyTorch or TensorFlow
- Hands-on experience with embeddings, semantic search, vector databases (Faiss, Milvus, Qdrant)
- Experience building and deploying retrieval or ranking systems in production
- Familiarity with LLMs, RAG, fine-tuning (LoRA, PEFT)
- NDCG, MRR, A/B testing experience
- BM25, Elasticsearch, OpenSearch experience is a plus

Nice to Have:
- Kafka, Airflow for feature pipelines
- MLflow for experiment tracking
- Product company experience (not consulting/IT services)

We value ownership, cross-functional collaboration, scale mindset.
Location: Pune or Noida preferred. Hybrid. Open to remote for exceptional candidates.`;

interface Props {
  onJobStarted: (jobId: string, useSample: boolean) => void;
}

export default function LandingPage({ onJobStarted }: Props) {
  const [jdText, setJdText] = useState(SAMPLE_JD);
  const [useSample, setUseSample] = useState(true);
  const [customFile, setCustomFile] = useState<File | null>(null);
  const [customDatasetPath, setCustomDatasetPath] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [profileOpen, setProfileOpen] = useState(false);
  
  const [apiProvider, setApiProvider] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("riq_api_provider") || "none";
    }
    return "none";
  });
  const [apiKey, setApiKey] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("riq_api_key") || "";
    }
    return "";
  });

  const updateApiSettings = (provider: string, key: string) => {
    setApiProvider(provider);
    setApiKey(key);
    if (typeof window !== "undefined") {
      localStorage.setItem("riq_api_provider", provider);
      localStorage.setItem("riq_api_key", key);
    }
  };

  const fileInputRef = useRef<HTMLInputElement>(null);
  const wordCount = jdText.trim().split(/\s+/).filter(Boolean).length;

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setCustomFile(file);
    setError("");
    setUploading(true);
    try {
      const res = await uploadDataset(file);
      setCustomDatasetPath(res.dataset_path);
    } catch (err: any) {
      setError(err.message || "Failed to upload candidate file. Make sure backend is running.");
      setCustomFile(null);
      setCustomDatasetPath(null);
    } finally {
      setUploading(false);
    }
  }

  async function handleAnalyse() {
    if (wordCount < 30) {
      setError("Please add more detail to your job description (minimum 30 words).");
      return;
    }
    setError("");
    setLoading(true);
    try {
      // If we have custom dataset path, start ranking with it
      const jobId = await startRanking(jdText, useSample, customDatasetPath || undefined, apiProvider, apiKey);
      onJobStarted(jobId, useSample);
    } catch (e: any) {
      setError(e.message || "Failed to start analysis. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans antialiased relative">
      {/* Header Nav */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold"
              style={{ background: "#44ACFF" }}>
              R
            </div>
            <div>
              <span className="font-bold text-lg text-slate-900 tracking-tight">RecruiterIQ</span>
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                Enterprise
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500 font-medium">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Local Scoring Engine Active
            </div>
            <button 
              onClick={() => setProfileOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 text-sm font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-50 transition-all">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              Profile
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Title */}
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold mb-4 bg-slate-100 text-slate-600 border border-slate-200">
            India Runs Data & AI Challenge — Redrob Hackathon
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl mb-3">
            AI-Assisted Candidate Shortlist Ranking
          </h1>
          <p className="text-base text-slate-500">
            Evaluate and rank candidates using local vector embeddings and multi-dimensional scoring models. No external API keys required.
          </p>
        </div>

        {/* Content Layout */}
        <div className="grid lg:grid-cols-12 gap-8 max-w-6xl mx-auto">
          {/* Left Panel: JD Input */}
          <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <label className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                Job Description
              </label>
              <button 
                onClick={() => setJdText(SAMPLE_JD)}
                className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-600 font-semibold hover:bg-slate-100 transition-all">
                Load Sample JD
              </button>
            </div>
            
            <textarea 
              value={jdText} 
              onChange={e => setJdText(e.target.value)}
              rows={16} 
              placeholder="Paste job description here..."
              className="w-full flex-1 rounded-lg p-4 text-sm text-slate-700 bg-slate-50 border border-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400 resize-none font-mono transition-all"
            />
            
            <div className="flex items-center justify-between mt-3 text-xs text-slate-400">
              <span className={wordCount < 30 ? "text-pink-600 font-medium" : ""}>
                {wordCount} words {wordCount < 30 && "(minimum 30 required)"}
              </span>
              <span>{jdText.length} characters</span>
            </div>
          </div>

          {/* Right Panel: Settings & Upload */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            {/* Custom Dataset Upload */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">
                Candidate Dataset
              </h3>
              
              {/* File Drop Area */}
              <div 
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center ${
                  customFile 
                    ? "border-emerald-300 bg-emerald-50/50" 
                    : "border-slate-300 hover:border-slate-400 bg-slate-50"
                }`}>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  accept=".json,.jsonl" 
                  className="hidden" 
                />
                
                {uploading ? (
                  <div className="flex flex-col items-center">
                    <div className="w-6 h-6 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin mb-2" />
                    <span className="text-xs font-semibold text-slate-500">Uploading dataset...</span>
                  </div>
                ) : customFile ? (
                  <div className="flex flex-col items-center">
                    <svg className="w-8 h-8 text-emerald-500 mb-2" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-xs font-bold text-slate-700 max-w-xs truncate">{customFile.name}</span>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        setCustomFile(null);
                        setCustomDatasetPath(null);
                      }} 
                      className="mt-2 text-xs font-semibold text-rose-500 hover:underline">
                      Remove file
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <svg className="w-8 h-8 text-slate-400 mb-2" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <span className="text-xs font-bold text-slate-600 mb-1">Click or drag candidate file here</span>
                    <span className="text-[10px] text-slate-400">Accepts .json or .jsonl candidate schemas</span>
                  </div>
                )}
              </div>
              
              {/* Dataset option fallback */}
              {!customFile && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block mb-2">Or use default local files:</span>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { val: true,  title: "Sample Dataset", desc: "~100 profiles" },
                      { val: false, title: "Full Dataset",   desc: "~487K profiles" },
                    ].map(opt => (
                      <button 
                        key={String(opt.val)} 
                        onClick={() => setUseSample(opt.val)}
                        className={`p-3 rounded-lg border text-left transition-all ${
                          useSample === opt.val 
                            ? "border-blue-500 bg-blue-50/20" 
                            : "border-slate-200 hover:bg-slate-50"
                        }`}>
                        <span className="text-xs font-bold text-slate-700 block">{opt.title}</span>
                        <span className="text-[10px] text-slate-400">{opt.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Weights Configuration */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">
                Scoring Weights
              </h3>
              <div className="space-y-3">
                {[
                  { label: "Skill Alignment",     w: 30, color: "#FE9EC7" },
                  { label: "Experience Relevance", w: 25, color: "#44ACFF" },
                  { label: "Career Signal",        w: 20, color: "#89D4FF" },
                  { label: "Behavioral Fit",       w: 15, color: "#FC6FA8" },
                  { label: "Cultural Alignment",   w: 10, color: "#F9F6C4" },
                ].map(d => (
                  <div key={d.label} className="flex items-center gap-2">
                    <span className="text-xs text-slate-500 w-36 shrink-0">{d.label}</span>
                    <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div 
                        className="h-full rounded-full" 
                        style={{ width: `${d.w}%`, background: d.color }} 
                      />
                    </div>
                    <span className="text-xs font-mono font-bold text-slate-500 w-8 text-right">{d.w}%</span>
                  </div>
                ))}
              </div>
            </div>
            
            {/* CTA */}
            <div className="flex flex-col gap-2">
              <button 
                onClick={handleAnalyse} 
                disabled={loading || uploading || wordCount < 30}
                className="w-full py-4 rounded-xl font-bold text-white transition-all text-base bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow active:scale-[0.99]"
                style={{ background: "#44ACFF" }}>
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Analyzing candidates...
                  </span>
                ) : "Analyse & Rank Candidates"}
              </button>
              
              <span className="text-center text-[10px] text-slate-400">
                Scoring is performed locally in-browser and local FastAPI server.
              </span>
            </div>
          </div>
        </div>
      </main>

      {/* Profile Slide-out Panel */}
      {profileOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm">
          {/* Overlay click */}
          <div className="absolute inset-0" onClick={() => setProfileOpen(false)} />
          
          <div className="relative w-full max-w-md bg-white h-screen shadow-2xl border-l border-slate-200 flex flex-col p-6 z-10 animate-slide-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-bold text-slate-900">Lead Talent Partner</h4>
                  <span className="text-xs text-slate-500">Enterprise Recruiter Profile</span>
                </div>
              </div>
              <button 
                onClick={() => setProfileOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1.5 hover:bg-slate-50 rounded-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="space-y-6 flex-1 overflow-y-auto">
              <div>
                <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Challenge Context</h5>
                <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                  <div className="text-sm font-semibold text-slate-700">India Runs Data & AI Challenge</div>
                  <div className="text-xs text-slate-500 mt-1">Host: Redrob AI candidate sourcing</div>
                  <div className="text-xs text-slate-500 mt-1">Goal: Extract and rank 100 best candidates</div>
                </div>
              </div>
              
              <div>
                <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">LLM Engine Configuration</h5>
                <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 space-y-3">
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Model Provider</label>
                    <select 
                      value={apiProvider} 
                      onChange={e => updateApiSettings(e.target.value, apiKey)}
                      className="w-full text-xs rounded border border-slate-200 bg-white p-2 text-slate-700 outline-none">
                      <option value="none">Local Engine (Default / Offline)</option>
                      <option value="grok">xAI Grok API (Grok-2-1212)</option>
                      <option value="gemini">Google Gemini API (Free Tier)</option>
                      <option value="openai">OpenAI GPT-4o API</option>
                      <option value="anthropic">Anthropic Claude API</option>
                    </select>
                  </div>
                  {apiProvider !== "none" && (
                    <div>
                      <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">API Key</label>
                      <input 
                        type="password" 
                        value={apiKey} 
                        onChange={e => updateApiSettings(apiProvider, e.target.value)}
                        placeholder="Enter API Key..."
                        className="w-full text-xs rounded border border-slate-200 bg-white p-2 text-slate-700 outline-none focus:border-blue-400"
                      />
                      <span className="text-[9px] text-slate-400 mt-1.5 block leading-normal">
                        Your key is stored securely in your local browser storage and is only passed directly to the local scoring backend.
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Local Infrastructure</h5>
                <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Embedding Model</span>
                    <span className="font-mono font-semibold text-slate-700">all-MiniLM-L6-v2</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Local Vector Store</span>
                    <span className="font-semibold text-slate-700">In-Memory NumPy Matrix</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Active Uploads Dir</span>
                    <span className="font-mono text-slate-700 text-[10px]">/uploads/*</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Hardware Accel</span>
                    <span className="font-semibold text-amber-600">CPU (Fallback)</span>
                  </div>
                </div>
              </div>

              <div>
                <h5 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Security & Isolation</h5>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Candidate ranking runs entirely inside your local network. No profile data or parsed resume content is sent to third-party endpoints or cloud LLMs unless an API provider key is explicitly configured.
                </p>
              </div>
            </div>
            
            <div className="border-t border-slate-100 pt-4 text-center">
              <span className="text-[10px] text-slate-400">RecruiterIQ v2.0.0 · Released June 2026</span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="fixed bottom-4 left-4 z-40 max-w-sm w-full bg-white border border-rose-200 rounded-lg shadow-lg p-4 flex gap-3">
          <svg className="w-5 h-5 text-rose-500 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <h4 className="text-xs font-bold text-rose-900">Error</h4>
            <p className="text-xs text-rose-700 mt-0.5">{error}</p>
          </div>
          <button onClick={() => setError("")} className="ml-auto text-slate-400 hover:text-slate-600 text-xs font-semibold">✕</button>
        </div>
      )}
    </div>
  );
}
