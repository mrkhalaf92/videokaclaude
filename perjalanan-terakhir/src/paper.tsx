import React from "react";
import { random } from "remotion";

// Langkah stop-start: progress licin -> beberapa lompatan kecil, kemudian berhenti.
export const stepped = (p: number, steps = 4) => Math.min(1, Math.floor(Math.max(0, p) * steps + 1e-6) / steps);

// Polygon tepi koyak (deterministik ikut seed), dalam %.
export const tornPolygon = (seed: string, amp = 1.2, n = 26) => {
  const pts: string[] = [];
  const j = (i: number, k: string) => (random(`${seed}-${k}-${i}`) - 0.5) * 2 * amp;
  for (let i = 0; i <= n; i++) pts.push(`${(i / n) * 100}% ${Math.abs(j(i, "t"))}%`);
  for (let i = 0; i <= n; i++) pts.push(`${100 - Math.abs(j(i, "r")) * 0.7}% ${(i / n) * 100}%`);
  for (let i = n; i >= 0; i--) pts.push(`${(i / n) * 100}% ${100 - Math.abs(j(i, "b"))}%`);
  for (let i = n; i >= 0; i--) pts.push(`${Math.abs(j(i, "l")) * 0.7}% ${(i / n) * 100}%`);
  return `polygon(${pts.join(",")})`;
};

export const Tape: React.FC<{ x: number; y: number; w?: number; rot: number; seed: string; show: number }> = ({ x, y, w = 190, rot, seed, show }) => {
  const zig = (side: "l" | "r") =>
    Array.from({ length: 7 }, (_, i) => `${side === "l" ? 3 * random(`${seed}${side}${i}`) : 100 - 3 * random(`${seed}${side}${i}`)}% ${(i / 6) * 100}%`);
  const clip = `polygon(${[...zig("l"), ...zig("r").reverse()].join(",")})`;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: 54, background: "rgba(236,226,196,0.82)",
      clipPath: clip, transform: `rotate(${rot}deg) scale(${show})`, boxShadow: "0 1px 2px rgba(0,0,0,0.15)",
      mixBlendMode: "multiply" }} />
  );
};
