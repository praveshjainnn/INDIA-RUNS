// API client for RecruiterIQ backend
import type { JDProfile, JobStatus, RankResults } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function parseJD(jdText: string): Promise<JDProfile> {
  const res = await fetch(`${BASE}/api/parse-jd`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd_text: jdText }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startRanking(
  jdText: string,
  useSample: boolean,
  datasetPath?: string,
  apiProvider?: string,
  apiKey?: string
): Promise<string> {
  const res = await fetch(`${BASE}/api/rank/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jd_text: jdText,
      use_sample: useSample,
      dataset_path: datasetPath,
      api_provider: apiProvider || "none",
      api_key: apiKey || null
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.job_id;
}

export async function uploadDataset(file: File): Promise<{ dataset_path: string; filename: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE}/api/upload-dataset`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/api/rank/status/${jobId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getResults(jobId: string, limit = 100): Promise<RankResults> {
  const res = await fetch(`${BASE}/api/rank/results/${jobId}?limit=${limit}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function downloadUrl(jobId: string, format: "csv" | "xlsx"): string {
  return `${BASE}/api/download/${format}/${jobId}`;
}

