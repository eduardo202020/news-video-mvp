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
import {getCaptionStateForFrame} from "./utils";
import {CaptionBar} from "./video/CaptionBar";
import {CoverStage} from "./video/CoverStage";
import {
  DEFAULT_MUSIC_SRC,
  DEFAULT_MUSIC_VOLUME,
  PAGE_TURN_FRAMES,
  SEGMENT_GAP_FRAMES
} from "./video/constants";
import {buildSegments, buildWordHighlights} from "./video/helpers";
import {NarratorStage} from "./video/NarratorStage";

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
  const sequence = buildSegments({segments, newspaperName, coverSrc, text});

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

  const segmentDuration = Math.max(
    1,
    Math.floor((durationInFrames - PAGE_TURN_FRAMES * Math.max(sequence.length - 1, 0)) / sequence.length)
  );
  const totalSegmentBlock = segmentDuration + PAGE_TURN_FRAMES;
  const activeIndex = Math.min(
    sequence.length - 1,
    Math.floor(frame / Math.max(1, totalSegmentBlock - SEGMENT_GAP_FRAMES))
  );
  const currentSegment = sequence[activeIndex];
  const nextSegment = sequence[Math.min(sequence.length - 1, activeIndex + 1)];
  const localBlockStart = activeIndex * Math.max(1, totalSegmentBlock - SEGMENT_GAP_FRAMES);
  const segmentFrame = frame - localBlockStart;
  const isTransitioning =
    activeIndex < sequence.length - 1 && segmentFrame >= segmentDuration - PAGE_TURN_FRAMES;

  const transitionProgress = isTransitioning
    ? interpolate(
        segmentFrame,
        [segmentDuration - PAGE_TURN_FRAMES, segmentDuration],
        [0, 1],
        {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp"
        }
      )
    : 0;

  const captionState = getCaptionStateForFrame({
    text: currentSegment.text,
    frame: Math.max(0, segmentFrame),
    durationInFrames: isTransitioning ? segmentDuration : Math.max(1, segmentDuration - SEGMENT_GAP_FRAMES)
  });

  const caption = captionState.text;
  const activeGestures = currentSegment.gestures?.length ? currentSegment.gestures : gestures;
  const gestureIndex = Math.floor(frame / fps) % activeGestures.length;
  const activeNarratorName = currentSegment.narratorName ?? narratorName;
  const subtitleLength = caption.length;
  const subtitleFontSize =
    subtitleLength > 120 ? 47 : subtitleLength > 90 ? 52 : subtitleLength > 65 ? 57 : 62;
  const subtitleLineHeight = subtitleLength > 120 ? 1.08 : 1.12;
  const captionWords = buildWordHighlights(caption, captionState.progress);

  const narratorSegmentProgress = interpolate(
    segmentFrame,
    [0, 12, Math.max(18, segmentDuration - 14), segmentDuration],
    [0, 1, 1, activeIndex < sequence.length - 1 ? 0.88 : 1],
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
  const bedVolume = (musicVolume ?? DEFAULT_MUSIC_VOLUME) * musicFade;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#120d12",
        fontFamily: `"${subtitleFontFamily}", Arial, sans-serif`
      }}
    >
      <Audio src={staticFile(audioSrc)} />
      <Audio src={staticFile(musicSrc ?? DEFAULT_MUSIC_SRC)} volume={bedVolume} loop />

      <AbsoluteFill>
        <Img
          src={staticFile(backgroundSrc)}
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
        currentSegment={currentSegment}
        nextSegment={nextSegment}
        isTransitioning={isTransitioning}
        transitionProgress={transitionProgress}
        cardTranslateY={cardTranslateY}
        coverFloatY={coverFloatY}
      />

      <CaptionBar
        captionWords={captionWords}
        subtitleFontSize={subtitleFontSize}
        subtitleLineHeight={subtitleLineHeight}
      />

      <NarratorStage
        gestureSrc={activeGestures[gestureIndex]}
        narratorVariant={activeNarratorName}
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
