"use client";
import { useState } from "react";
import LandingPage from "@/components/LandingPage";
import ProcessingPage from "@/components/ProcessingPage";
import ResultsPage from "@/components/ResultsPage";

type Screen = "landing" | "processing" | "results";

export default function Home() {
  const [screen, setScreen] = useState<Screen>("landing");
  const [jobId, setJobId] = useState("");
  const [useSample, setUseSample] = useState(true);
  const [error, setError] = useState("");

  function handleJobStarted(id: string, sample: boolean) {
    setJobId(id);
    setUseSample(sample);
    setScreen("processing");
  }

  function handleDone() {
    setScreen("results");
  }

  function handleError(msg: string) {
    setError(msg);
    setScreen("landing");
  }

  function handleReset() {
    setJobId("");
    setError("");
    setScreen("landing");
  }

  return (
    <>
      {error && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 max-w-md w-full mx-4">
          <div className="rounded-2xl p-4 text-sm font-medium shadow-riq-lg"
            style={{ background: "white", border: "1.5px solid rgba(254,158,199,0.5)", color: "#BE185D" }}>
            ❌ {error}
            <button onClick={() => setError("")} className="ml-3 text-gray-400 hover:text-gray-600">✕</button>
          </div>
        </div>
      )}

      {screen === "landing" && (
        <LandingPage onJobStarted={handleJobStarted} />
      )}
      {screen === "processing" && jobId && (
        <ProcessingPage
          jobId={jobId}
          useSample={useSample}
          onDone={handleDone}
          onError={handleError}
        />
      )}
      {screen === "results" && jobId && (
        <ResultsPage jobId={jobId} onReset={handleReset} />
      )}
    </>
  );
}
