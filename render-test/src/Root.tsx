import React from "react";
import { Composition } from "remotion";
import { TestVideo } from "./TestVideo";

// 1080x1920 (TikTok/Reels), 30fps, 150 frame = 5 saat
export const Root: React.FC = () => (
  <Composition id="TestVideo" component={TestVideo}
    durationInFrames={150} fps={30} width={1080} height={1920} />
);
