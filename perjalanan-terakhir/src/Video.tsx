import React from "react";
import {
  AbsoluteFill, Easing, Img, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame,
} from "remotion";
import timeline from "../timeline.json";
import manifest from "./manifest.json";
import { C, FONT_HEAD, FONT_NOTE, LAYOUT } from "./theme";
import { stepped, Tape, tornPolygon } from "./paper";

const FPS = timeline.fps;
const f = (s: number) => Math.round(s * FPS);

type SceneT = (typeof timeline.scenes)[number] & {
  noteAt?: number; still?: { src: string; at: number }; stillAt?: number; cta?: string; ctaAt?: number;
};
type Man = { clips: { file: string; offset: number; len: number }[]; still?: string };

const fontFace = `@font-face { font-family: 'Caveat'; src: url('${staticFile("fonts/Caveat-Bold.ttf")}') format('truetype'); font-weight: 700; }`;

// Satu baris headline: masuk dengan 3 lompatan kecil (stop-start), kemudian diam.
const HeadLine: React.FC<{ text: string; at: number; big?: boolean }> = ({ text, at, big }) => {
  const fr = useCurrentFrame();
  const p = stepped(interpolate(fr, [f(at), f(at) + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }), 3);
  return (
    <div style={{ fontFamily: FONT_HEAD, fontWeight: 900, fontSize: big ? 128 : 98, lineHeight: 1.04,
      letterSpacing: big ? -2 : -1, color: C.ink, opacity: p > 0 ? 1 : 0, transform: `translateY(${(1 - p) * 26}px)` }}>
      {text}
    </div>
  );
};

// Anotasi marker + garis tangan yang dilukis.
const Note: React.FC<{ text: string; at: number; seed: string }> = ({ text, at, seed }) => {
  const fr = useCurrentFrame();
  const t = fr - f(at);
  if (t < 0) return null;
  const draw = interpolate(t, [0, 10], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.quad) });
  const txt = stepped(interpolate(t, [4, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }), 2);
  return (
    <div style={{ position: "absolute", left: LAYOUT.headLeft + 10, top: LAYOUT.noteTop, width: 880 }}>
      <svg width="110" height="80" style={{ position: "absolute", left: 0, top: -6, overflow: "visible" }}>
        <path d="M10 70 C 30 40, 60 20, 96 6 M96 6 l -22 2 M96 6 l -8 20" fill="none" stroke={C.accent} strokeWidth={6}
          strokeLinecap="round" strokeDasharray={200} strokeDashoffset={200 * (1 - draw)} />
      </svg>
      <div style={{ marginLeft: 120, fontFamily: FONT_NOTE, fontWeight: 700, fontSize: 92, color: C.accent,
        transform: `rotate(-2deg) translateY(${(1 - txt) * 12}px)`, opacity: txt > 0 ? 1 : 0, whiteSpace: "nowrap" }}>
        {text}
      </div>
    </div>
  );
};

const Photo: React.FC<{ scene: SceneT; man: Man; idx: number; dim: number }> = ({ scene, man, idx, dim }) => {
  const fr = useCurrentFrame();
  const { x, y, w, h } = LAYOUT.frame;
  const rot = idx % 2 === 0 ? -1.2 : 1.1;
  // Mendarat dari bawah dalam 4 langkah (stop-start), kemudian tahan.
  const land = stepped(interpolate(fr, [0, 9], [0, 1], { extrapolateRight: "clamp" }), 4);
  const dy = (1 - land) * 140;
  const tapeShow = fr >= 10 ? 1 : 0;
  // Parallax kecil: foto naik 10px sepanjang babak.
  const drift = interpolate(fr, [0, f(scene.end - scene.start)], [0, -10]);
  const torn = tornPolygon(scene.id);
  return (
    <div style={{ position: "absolute", left: x, top: y + dy + drift, width: w, height: h, transform: `rotate(${rot}deg)`,
      filter: "drop-shadow(0 10px 14px rgba(40,30,20,0.28))" }}>
      <div style={{ position: "absolute", inset: 0, background: C.photoEdge, clipPath: torn }} />
      <div style={{ position: "absolute", inset: 16, clipPath: tornPolygon(scene.id + "in", 0.8), overflow: "hidden", background: "#000" }}>
        {man.clips.map((c, i) => (
          <Sequence key={c.file} from={f(c.offset)} durationInFrames={f(c.len)} layout="none">
            <OffthreadVideo src={staticFile(c.file)} muted
              style={{ width: "100%", height: "100%", objectFit: "cover", filter: "saturate(0.88) contrast(1.04) sepia(0.08)" }} />
          </Sequence>
        ))}
        <AbsoluteFill style={{ background: C.paper, opacity: dim }} />
      </div>
      <Tape x={-40} y={-22} rot={-28} seed={scene.id + "a"} show={tapeShow} />
      <Tape x={w - 150} y={h - 34} rot={-24} seed={scene.id + "b"} show={tapeShow} />
    </div>
  );
};

const Polaroid: React.FC<{ src: string; at: number; seed: string }> = ({ src, at, seed }) => {
  const fr = useCurrentFrame();
  const t = fr - f(at);
  if (t < 0) return null;
  const p = stepped(interpolate(t, [0, 8], [0, 1], { extrapolateRight: "clamp" }), 3);
  return (
    <div style={{ position: "absolute", left: 640, top: 1150 + (1 - p) * 90, width: 330, height: 400, background: C.photoEdge,
      transform: `rotate(${6 - (1 - p) * 4}deg)`, boxShadow: "0 12px 18px rgba(40,30,20,0.32)", padding: "16px 16px 64px" }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "saturate(0.85) sepia(0.1)" }} />
      <Tape x={100} y={-26} w={130} rot={4} seed={seed + "p"} show={t >= 9 ? 1 : 0} />
    </div>
  );
};

const Scene: React.FC<{ scene: SceneT; idx: number }> = ({ scene, idx }) => {
  const fr = useCurrentFrame();
  const man = (manifest as Record<string, Man>)[scene.id];
  const ctaF = scene.cta ? f(scene.ctaAt!) : Infinity;
  const dim = scene.cta ? stepped(interpolate(fr, [ctaF - 6, ctaF + 6], [0, 0.9], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }), 4) : 0;
  return (
    <AbsoluteFill>
      <Photo scene={scene} man={man} idx={idx} dim={dim} />
      <div style={{ position: "absolute", left: LAYOUT.headLeft, top: LAYOUT.headTop, width: LAYOUT.headWidth }}>
        {scene.head.map((h, i) => <HeadLine key={i} text={h} at={scene.headAt[i]} big={scene.head.length === 1 && h === h.toUpperCase()} />)}
      </div>
      {scene.note && <Note text={scene.note} at={scene.noteAt!} seed={scene.id} />}
      {man.still && <Polaroid src={man.still} at={scene.stillAt!} seed={scene.id} />}
      {scene.cta && fr >= ctaF && (
        <div style={{ position: "absolute", left: LAYOUT.frame.x, top: 840, width: LAYOUT.frame.w, textAlign: "center" }}>
          <div style={{ fontFamily: FONT_HEAD, fontWeight: 900, fontSize: 132, lineHeight: 1.02, color: C.ink, letterSpacing: -2,
            transform: `translateY(${(1 - stepped(interpolate(fr - ctaF, [0, 8], [0, 1], { extrapolateRight: "clamp" }), 3)) * 30}px)` }}>
            {scene.cta}
          </div>
          <svg width="600" height="40" style={{ marginTop: 6 }}>
            <path d="M10 26 C 150 8, 420 34, 590 14" fill="none" stroke={C.accent} strokeWidth={10} strokeLinecap="round"
              strokeDasharray={640} strokeDashoffset={640 * (1 - interpolate(fr - ctaF, [10, 26], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))} />
          </svg>
        </div>
      )}
    </AbsoluteFill>
  );
};

export const Video: React.FC = () => {
  const fr = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <style>{fontFace}</style>
      {/* Kertas latar: parallax sangat kecil */}
      <Img src={staticFile("paper.png")} style={{ position: "absolute", width: 1100, height: 1960, left: -10,
        top: interpolate(fr, [0, f(timeline.duration)], [-10, -30]) }} />
      {(timeline.scenes as SceneT[]).map((s, i) => (
        <Sequence key={s.id} from={f(s.start)} durationInFrames={f(s.end) - f(s.start)} name={s.id}>
          <Scene scene={s} idx={i} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
