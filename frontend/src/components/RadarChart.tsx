"use client";
import { useEffect, useRef } from "react";
import type { RankedCandidate } from "@/lib/types";

const DIMS = [
  { key: "skill_alignment",      label: "Skills",      color: "#FE9EC7" },
  { key: "experience_relevance", label: "Experience",  color: "#44ACFF" },
  { key: "career_signal",        label: "Career",      color: "#89D4FF" },
  { key: "behavioral_fit",       label: "Behavioral",  color: "#FC6FA8" },
  { key: "cultural_alignment",   label: "Cultural",    color: "#F9A825" },
] as const;

export default function RadarChart({ rc }: { rc: RankedCandidate }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const values = DIMS.map(d => (rc as any)[d.key] as number);
  const n = DIMS.length;
  const size = 220;
  const cx = size / 2, cy = size / 2;
  const R = 80;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, size, size);

    const angle = (i: number) => (Math.PI * 2 * i) / n - Math.PI / 2;
    const pt = (i: number, r: number) => ({
      x: cx + r * Math.cos(angle(i)),
      y: cy + r * Math.sin(angle(i)),
    });

    // Draw grid rings
    [0.25, 0.5, 0.75, 1].forEach(frac => {
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const p = pt(i, R * frac);
        i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
      }
      ctx.closePath();
      ctx.strokeStyle = frac === 1 ? "rgba(68,172,255,0.25)" : "rgba(137,212,255,0.15)";
      ctx.lineWidth = frac === 1 ? 1.5 : 1;
      ctx.stroke();
    });

    // Draw axes
    for (let i = 0; i < n; i++) {
      const p = pt(i, R);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(p.x, p.y);
      ctx.strokeStyle = "rgba(137,212,255,0.2)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw filled polygon
    ctx.beginPath();
    values.forEach((v, i) => {
      const p = pt(i, R * (v / 100));
      i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
    });
    ctx.closePath();

    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
    grad.addColorStop(0, "rgba(254,158,199,0.5)");
    grad.addColorStop(0.5, "rgba(137,212,255,0.3)");
    grad.addColorStop(1, "rgba(68,172,255,0.2)");
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = "#FE9EC7";
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Draw dots at vertices
    values.forEach((v, i) => {
      const p = pt(i, R * (v / 100));
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = DIMS[i].color;
      ctx.fill();
      ctx.strokeStyle = "white";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });

    // Labels
    ctx.font = "bold 10px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let i = 0; i < n; i++) {
      const p = pt(i, R + 18);
      ctx.fillStyle = "#374151";
      ctx.fillText(DIMS[i].label, p.x, p.y);
      const pv = pt(i, R * (values[i] / 100) - 12);
      ctx.font = "9px JetBrains Mono, monospace";
      ctx.fillStyle = DIMS[i].color;
      ctx.fillText(`${values[i].toFixed(0)}`, pv.x, pv.y);
      ctx.font = "bold 10px Inter, sans-serif";
    }
  }, [rc]);

  return (
    <div className="flex flex-col items-center">
      <canvas ref={canvasRef} width={size} height={size} style={{ maxWidth: "100%" }} />
      <div className="flex flex-wrap justify-center gap-2 mt-1">
        {DIMS.map(d => (
          <div key={d.key} className="flex items-center gap-1">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: d.color }} />
            <span className="text-xs text-gray-500">{d.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
