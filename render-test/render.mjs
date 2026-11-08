// Render TestVideo -> out/test-video.mp4 guna Chromium sedia ada (tak download browser baru).
import path from "node:path";
import fs from "node:fs";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

const candidates = [
  process.env.REMOTION_BROWSER,
  "/opt/pw-browsers/chromium_headless_shell-1243/chrome-linux/headless_shell",
  "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell",
].filter(Boolean);
const browserExecutable = candidates.find((p) => fs.existsSync(p)) ?? null; // null = Remotion urus sendiri

const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const composition = await selectComposition({ serveUrl, id: "TestVideo", browserExecutable });
fs.mkdirSync("out", { recursive: true });
await renderMedia({
  composition, serveUrl, codec: "h264", pixelFormat: "yuv420p", colorSpace: "bt709", browserExecutable,
  outputLocation: "out/test-video.mp4",
  onProgress: ({ progress }) => process.stdout.write(`\r${Math.round(progress * 100)}%`),
});
console.log("\nSiap: out/test-video.mp4 (browser:", browserExecutable ?? "Remotion default", ")");
