import React from "react";
import {Composition} from "remotion";
import {NewsVideo} from "./NewsVideo";
import {defaultStory, stories} from "./data";

const studioStory = defaultStory;

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="NewsVideo"
        component={NewsVideo}
        durationInFrames={studioStory.durationInFrames}
        fps={studioStory.fps}
        width={1080}
        height={1920}
        defaultProps={studioStory}
        calculateMetadata={({props}) => ({
          durationInFrames: props.durationInFrames ?? studioStory.durationInFrames,
          fps: props.fps ?? studioStory.fps,
          width: 1080,
          height: 1920
        })}
      />
      {Object.values(stories).map((story) => (
        <Composition
          key={story.id}
          id={`NewsVideo-${story.id}`}
          component={NewsVideo}
          durationInFrames={story.durationInFrames}
          fps={story.fps}
          width={1080}
          height={1920}
          defaultProps={story}
        />
      ))}
    </>
  );
};
