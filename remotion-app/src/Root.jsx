import React from "react";
import {Composition} from "remotion";
import {NewsVideo} from "./NewsVideo";
import {VIDEO_SPEC} from "./story/defaults.js";
import {
  latestGeneratedStory,
  studioDefaultStory,
  studioStories
} from "./story/normalize.js";

const studioStory = studioDefaultStory;

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="NewsVideo"
        component={NewsVideo}
        durationInFrames={studioStory.durationInFrames}
        fps={studioStory.fps}
        width={VIDEO_SPEC.width}
        height={VIDEO_SPEC.height}
        defaultProps={studioStory}
        calculateMetadata={({props}) => ({
          durationInFrames: props.durationInFrames ?? studioStory.durationInFrames,
          fps: props.fps ?? studioStory.fps,
          width: VIDEO_SPEC.width,
          height: VIDEO_SPEC.height
        })}
      />
      <Composition
        id="NewsVideo-generated"
        component={NewsVideo}
        durationInFrames={latestGeneratedStory.durationInFrames}
        fps={latestGeneratedStory.fps}
        width={VIDEO_SPEC.width}
        height={VIDEO_SPEC.height}
        defaultProps={latestGeneratedStory}
      />
      {Object.values(studioStories).map((story) => (
        <Composition
          key={story.id}
          id={`NewsVideo-${story.id}`}
          component={NewsVideo}
          durationInFrames={story.durationInFrames}
          fps={story.fps}
          width={VIDEO_SPEC.width}
          height={VIDEO_SPEC.height}
          defaultProps={story}
        />
      ))}
    </>
  );
};
