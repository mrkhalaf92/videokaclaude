import React from "react";
import { Composition } from "remotion";
import { Video } from "./Video";
import timeline from "../timeline.json";

export const Root: React.FC = () => (
  <Composition id="Preview" component={Video} fps={timeline.fps}
    durationInFrames={Math.round(timeline.duration * timeline.fps)} width={1080} height={1920} />
);
