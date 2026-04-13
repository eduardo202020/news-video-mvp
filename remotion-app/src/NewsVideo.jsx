import React from "react";
import {loadFont as loadBarlowSemiCondensed} from "@remotion/google-fonts/BarlowSemiCondensed";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig
} from "remotion";
import {DEFAULT_MUSIC_SRC, DEFAULT_MUSIC_VOLUME} from "./story/defaults.js";
import {normalizeStory} from "./story/normalize.js";
import {CaptionBar} from "./video/CaptionBar";
import {CoverStage} from "./video/CoverStage";
import {NarratorStage} from "./video/NarratorStage";
import {resolveTimeline} from "./video/timeline.js";

const {fontFamily: subtitleFontFamily} = loadBarlowSemiCondensed("normal", {
  weights: ["700"],
  subsets: ["latin"]
});

export const NewsVideo = ({
  newspaperName,
  coverSrc,
  backgroundSrc,
  audioSrc,
  musicSrc,
  musicVolume,
  narratorName,
  text,
  gestures,
  segments
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const story = normalizeStory({
    newspaperName,
    coverSrc,
    backgroundSrc,
    audioSrc,
    musicSrc,
    musicVolume,
    narratorName,
    text,
    gestures,
    segments,
    fps,
    durationInFrames
  });
  const timeline = resolveTimeline({
    frame,
    fps,
    durationInFrames,
    story
  });

  const cardEntrance = spring({
    fps,
    frame,
    config: {
      damping: 18,
      stiffness: 95
    }
  });

  const narratorEntrance = spring({
    fps,
    frame: frame - 8,
    config: {
      damping: 18,
      stiffness: 110
    }
  });

  const cardTranslateY = interpolate(cardEntrance, [0, 1], [80, 0]);
  const narratorTranslateY = interpolate(narratorEntrance, [0, 1], [200, 0]);
  const narratorScale = interpolate(narratorEntrance, [0, 1], [0.94, 1]);

  const backgroundTravel = 190;
  const backgroundCycleFrames = Math.max(120, Math.floor(durationInFrames * 0.65));
  const cycleFrame = frame % backgroundCycleFrames;
  const backgroundPan = interpolate(
    cycleFrame,
    [0, backgroundCycleFrames / 2, backgroundCycleFrames],
    [backgroundTravel, -backgroundTravel, backgroundTravel],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }
  );
  const backgroundScale = interpolate(
    frame,
    [0, durationInFrames / 2, durationInFrames],
    [1.08, 1.12, 1.08],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }
  );

  const narratorSegmentProgress = interpolate(
    timeline.segmentFrame,
    [0, 12, Math.max(18, timeline.segmentDuration - 14), timeline.segmentDuration],
    [0, 1, 1, timeline.activeIndex < timeline.sequence.length - 1 ? 0.88 : 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }
  );
  const narratorSegmentTranslateX = interpolate(narratorSegmentProgress, [0, 1], [32, 0]);
  const narratorSegmentTranslateY = interpolate(narratorSegmentProgress, [0, 1], [30, 0]);
  const narratorSegmentScale = interpolate(narratorSegmentProgress, [0, 1], [0.97, 1]);
  const narratorSegmentOpacity = interpolate(narratorSegmentProgress, [0, 1], [0, 1]);

  const coverFloatY = interpolate(
    frame,
    [0, durationInFrames / 2, durationInFrames],
    [0, -10, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }
  );

  const musicFade = interpolate(
    frame,
    [0, 18, Math.max(24, durationInFrames - 18), durationInFrames],
    [0, 1, 1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }
  );
  const bedVolume = (story.musicVolume ?? DEFAULT_MUSIC_VOLUME) * musicFade;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#120d12",
        fontFamily: `"${subtitleFontFamily}", Arial, sans-serif`
      }}
    >
      <Audio src={staticFile(story.audioSrc)} />
      <Audio src={staticFile(story.musicSrc ?? DEFAULT_MUSIC_SRC)} volume={bedVolume} loop />

      <AbsoluteFill>
        <Img
          src={staticFile(story.backgroundSrc)}
          style={{
            width: "142%",
            height: "100%",
            objectFit: "cover",
            filter: "blur(6px) saturate(1.15)",
            marginLeft: "-21%",
            transform: `translateX(${backgroundPan}px) scale(${backgroundScale})`
          }}
        />
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(180deg, rgba(28,16,24,0.18) 0%, rgba(22,16,21,0.08) 32%, rgba(17,12,18,0.42) 68%, rgba(13,9,13,0.78) 100%)"
          }}
        />
        <AbsoluteFill
          style={{
            background:
              "radial-gradient(circle at 32% 28%, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.04) 20%, rgba(255,255,255,0) 44%)"
          }}
        />
        <AbsoluteFill
          style={{
            boxShadow: "inset 0 0 220px rgba(0,0,0,0.28)"
          }}
        />
      </AbsoluteFill>

      <CoverStage
        currentSegment={timeline.currentSegment}
        nextSegment={timeline.nextSegment}
        isTransitioning={timeline.isTransitioning}
        transitionProgress={timeline.transitionProgress}
        cardTranslateY={cardTranslateY}
        coverFloatY={coverFloatY}
      />

      <CaptionBar
        captionWords={timeline.captionWords}
        subtitleFontSize={timeline.subtitleFontSize}
        subtitleLineHeight={timeline.subtitleLineHeight}
      />

      <NarratorStage
        gestureSrc={timeline.activeGestureSrc}
        narratorVariant={timeline.activeNarratorName}
        narratorTranslateY={narratorTranslateY}
        narratorScale={narratorScale}
        narratorSegmentTranslateX={narratorSegmentTranslateX}
        narratorSegmentTranslateY={narratorSegmentTranslateY}
        narratorSegmentScale={narratorSegmentScale}
        narratorSegmentOpacity={narratorSegmentOpacity}
      />
    </AbsoluteFill>
  );
};
