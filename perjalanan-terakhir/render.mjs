// node render.mjs            -> out/video_noaudio.mp4 (visual sahaja; audio dimix oleh tools/make_audio.py)
// node render.mjs --stills   -> review/still_*.png pada saat-saat penting (semakan layout cepat)
import path from "node:path";
import fs from "node:fs";
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";

const browserExecutable = [process.env.REMOTION_BROWSER,
  "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell"]
  .filter(Boolean).find((p) => fs.existsSync(p)) ?? null;
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), publicDir: path.resolve("public") });
const composition = await selectComposition({ serveUrl, id: "Preview", browserExecutable });
fs.mkdirSync("out", { recursive: true });

if (process.argv.includes("--stills")) {
  const secs = (process.argv.find((a) => a.startsWith("--at=")) ?? "--at=1,4,9,15,20,29,35,41,47,54,61,67,73,79,84,88").slice(5).split(",").map(Number);
  fs.mkdirSync("review", { recursive: true });
  for (const s of secs) {
    await renderStill({ composition, serveUrl, browserExecutable, frame: Math.round(s * 30), output: `review/still_${String(s).padStart(4, "0")}.png`, scale: 0.5 });
  }
  console.log("stills OK");
} else {
  await renderMedia({ composition, serveUrl, browserExecutable, codec: "h264", pixelFormat: "yuv420p", colorSpace: "bt709",
    muted: true, crf: 18, outputLocation: "out/video_noaudio.mp4",
    onProgress: ({ progress }) => process.stdout.write(`\r${Math.round(progress * 100)}%   `) });
  console.log("\nvideo OK");
}
