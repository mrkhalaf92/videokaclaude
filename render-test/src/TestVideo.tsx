import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const TestVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 12 } });
  const fadeOut = interpolate(frame, [durationInFrames - 20, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
  const barW = interpolate(frame, [0, durationInFrames], [0, 900]);
  const rot = interpolate(frame, [0, durationInFrames], [0, 360]);
  const sec = Math.floor(frame / fps) + 1;

  return (
    <AbsoluteFill style={{ background: "#082c22", fontFamily: "DejaVu Sans, sans-serif", opacity: fadeOut }}>
      <div style={{ position: "absolute", left: 340, top: 420, width: 400, height: 400,
        borderRadius: "50%", background: "#deb240", transform: `scale(${pop})` }} />
      <div style={{ position: "absolute", left: 440, top: 1050, width: 200, height: 200,
        background: "#187054", transform: `rotate(${rot}deg)` }} />
      <div style={{ position: "absolute", top: 1350, width: "100%", textAlign: "center",
        color: "#f8f1de", fontSize: 96, fontWeight: 700, transform: `scale(${pop})` }}>
        UJIAN RENDER
      </div>
      <div style={{ position: "absolute", top: 1490, width: "100%", textAlign: "center",
        color: "#f5d682", fontSize: 64 }}>
        Saat {sec} / 5
      </div>
      <div style={{ position: "absolute", left: 90, top: 1700, width: barW, height: 24,
        borderRadius: 12, background: "#deb240" }} />
    </AbsoluteFill>
  );
};
