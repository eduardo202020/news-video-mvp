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
import {SupportVisualStage} from "./video/SupportVisualStage";
import {withAssetVersion} from "./video/asset-src";
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
  segments,
  subtitleSegments,
  showCoverDebug = false
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
    subtitleSegments,
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
  const narratorScale = interpolate(narratorEntrance, [0, 1], [0.98, 1]);

  const backgroundTravel = 28;
  const backgroundPan = interpolate(frame, [0, durationInFrames], [0, -backgroundTravel], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp"
  });
  const backgroundScale = 1.03;

  const narratorSegmentProgress = interpolate(
    timeline.segmentFrame,
    [0, 12, Math.max(18, timeline.segmentDuration - 14), timeline.segmentDuration],
    [0, 1, 1, timeline.activeIndex < timeline.sequence.length - 1 ? 0.88 : 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }
  );
  const narratorSegmentTranslateX = interpolate(narratorSegmentProgress, [0, 1], [16, 0]);
  const narratorSegmentTranslateY = interpolate(narratorSegmentProgress, [0, 1], [14, 0]);
  const narratorSegmentScale = interpolate(narratorSegmentProgress, [0, 1], [0.99, 1]);
  const narratorSegmentOpacity = interpolate(narratorSegmentProgress, [0, 1], [0, 1]);

  const coverFloatY = interpolate(
    frame,
    [0, durationInFrames / 2, durationInFrames],
    [0, -3, 0],
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
  const assetVersion = story.assetVersion ?? null;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#120d12",
        fontFamily: `"${subtitleFontFamily}", Arial, sans-serif`
      }}
    >
      <Audio src={staticFile(withAssetVersion(story.audioSrc, assetVersion))} />
      <Audio src={staticFile(story.musicSrc ?? DEFAULT_MUSIC_SRC)} volume={bedVolume} loop />

      <AbsoluteFill>
        <Img
          src={staticFile(withAssetVersion(story.backgroundSrc, assetVersion))}
          style={{
            width: "112%",
            height: "100%",
            objectFit: "cover",
            marginLeft: "-6%",
            transform: `translateX(${backgroundPan}px) scale(${backgroundScale})`
          }}
        />
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(180deg, rgba(20,16,20,0.22) 0%, rgba(16,13,18,0.18) 44%, rgba(12,10,14,0.56) 100%)"
          }}
        />
      </AbsoluteFill>

      <CoverStage
        newspaperCoverStack={story.newspaperCoverStack}
        currentSegment={timeline.currentSegment}
        nextSegment={timeline.nextSegment}
        assetVersion={assetVersion}
        segmentFrame={timeline.segmentFrame}
        segmentDuration={timeline.segmentDuration}
        isTransitioning={timeline.isTransitioning}
        transitionProgress={timeline.transitionProgress}
        cardTranslateY={cardTranslateY}
        coverFloatY={coverFloatY}
        showCoverDebug={showCoverDebug}
      />

      <CaptionBar
        captionWords={timeline.captionWords}
        subtitleFontSize={timeline.subtitleFontSize}
        subtitleLineHeight={timeline.subtitleLineHeight}
      />

      <SupportVisualStage
        supportVisual={timeline.currentSegment.supportVisual}
        segmentFrame={timeline.segmentFrame}
        fps={fps}
        segmentDuration={timeline.segmentDuration}
      />

      <NarratorStage
        gestureSrc={timeline.activeGestureSrc}
        assetVersion={assetVersion}
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
