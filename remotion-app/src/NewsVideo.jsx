import React from "react";
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

const CARD_WIDTH = 929;
const COVER_HEIGHT = 1058;
const PAGE_TURN_FRAMES = 16;
const SEGMENT_GAP_FRAMES = 10;

const buildSegments = ({segments, newspaperName, coverSrc, text}) => {
  if (segments && segments.length > 0) {
    return segments;
  }

  return [
    {
      newspaperName,
      coverSrc,
      text
    }
  ];
};

export const NewsVideo = ({
  newspaperName,
  coverSrc,
  backgroundSrc,
  audioSrc,
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
  const gestureIndex = Math.floor(frame / (fps * 2)) % activeGestures.length;
  const currentRotateY = interpolate(transitionProgress, [0, 1], [0, 88]);
  const nextRotateY = interpolate(transitionProgress, [0, 1], [-88, 0]);
  const currentTranslateX = interpolate(transitionProgress, [0, 1], [0, -60]);
  const nextTranslateX = interpolate(transitionProgress, [0, 1], [150, 0]);
  const currentShadow = interpolate(transitionProgress, [0, 1], [0.32, 0.08]);
  const nextShadow = interpolate(transitionProgress, [0, 1], [0.04, 0.32]);
  const subtitleLength = caption.length;
  const subtitleFontSize =
    subtitleLength > 120 ? 47 : subtitleLength > 90 ? 52 : subtitleLength > 65 ? 57 : 62;
  const subtitleLineHeight = subtitleLength > 120 ? 1.08 : 1.12;
  const captionWords = caption ? caption.split(" ") : [];
  const spokenWords = Math.floor(captionWords.length * captionState.progress);
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

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#120d12",
        fontFamily: "Arial, sans-serif"
      }}
    >
      <Audio src={staticFile(audioSrc)} />
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

      <div
        style={{
          position: "absolute",
          top: 0,
          left: "50%",
          width: CARD_WIDTH,
          marginLeft: -(CARD_WIDTH / 2),
          transform: `translateY(${cardTranslateY + coverFloatY}px)`,
          filter: "drop-shadow(0 34px 52px rgba(0,0,0,0.30))"
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 22,
            left: 30,
            width: CARD_WIDTH - 76,
            height: COVER_HEIGHT - 48,
            borderRadius: 24,
            background: "linear-gradient(180deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.04) 16%, rgba(255,255,255,0) 36%)",
            opacity: 0.34,
            transform: "translateY(12px) scale(0.985)",
            filter: "blur(10px)"
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 26,
            left: 46,
            width: CARD_WIDTH - 92,
            height: COVER_HEIGHT - 54,
            borderRadius: 28,
            background: "rgba(0,0,0,0.10)",
            transform: "translateY(18px) skewX(-1.2deg)",
            filter: "blur(12px)",
            opacity: 0.42
          }}
        />
        <Img
          src={staticFile(currentSegment.coverSrc)}
          style={{
            width: CARD_WIDTH,
            height: COVER_HEIGHT,
            objectFit: "contain",
            display: "block",
            transformOrigin: "left center",
            transform: `perspective(1800px) translateX(${currentTranslateX}px) rotateY(${currentRotateY}deg) rotateZ(-0.35deg)`,
            opacity: isTransitioning ? interpolate(transitionProgress, [0, 1], [1, 0.2]) : 1,
            filter: `drop-shadow(0 20px 20px rgba(0,0,0,0.12)) drop-shadow(0 36px 48px rgba(0,0,0,${currentShadow}))`
          }}
        />
        {isTransitioning ? (
          <Img
            src={staticFile(nextSegment.coverSrc)}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: CARD_WIDTH,
              height: COVER_HEIGHT,
              objectFit: "contain",
              display: "block",
              transformOrigin: "right center",
              transform: `perspective(1800px) translateX(${nextTranslateX}px) rotateY(${nextRotateY}deg) rotateZ(0.25deg)`,
              opacity: interpolate(transitionProgress, [0, 1], [0.4, 1]),
              filter: `drop-shadow(0 18px 18px rgba(0,0,0,0.10)) drop-shadow(0 34px 44px rgba(0,0,0,${nextShadow}))`
            }}
          />
        ) : null}
        {isTransitioning ? (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: CARD_WIDTH / 2 - 16,
              width: 32,
              height: COVER_HEIGHT,
              background:
                "linear-gradient(90deg, rgba(0,0,0,0.28) 0%, rgba(255,255,255,0.16) 50%, rgba(0,0,0,0.24) 100%)",
              opacity: interpolate(transitionProgress, [0, 1], [0.1, 0.85]),
              transform: `translateX(${interpolate(transitionProgress, [0, 1], [-90, 90])}px)`,
              filter: "blur(4px)"
            }}
          />
        ) : null}
      </div>

      <div
        style={{
          position: "absolute",
          right: 12,
          bottom: -10,
          width: 620,
          height: 880,
          transform: `translateX(${narratorSegmentTranslateX}px) translateY(${narratorTranslateY + narratorSegmentTranslateY}px) scale(${narratorScale * narratorSegmentScale})`,
          opacity: narratorSegmentOpacity,
          transformOrigin: "bottom right"
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 74,
            bottom: 6,
            width: 500,
            height: 110,
            borderRadius: "50%",
            background: "rgba(0,0,0,0.48)",
            filter: "blur(22px)"
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 80,
            bottom: 110,
            width: 430,
            height: 430,
            borderRadius: "50%",
            background: "rgba(255,96,58,0.09)",
            filter: "blur(34px)"
          }}
        />
        <div
          style={{
            position: "absolute",
            right: 84,
            bottom: 46,
            width: 310,
            height: 520,
            background: "linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)",
            filter: "blur(20px)",
            opacity: 0.45
          }}
        />
        <Img
          src={staticFile(activeGestures[gestureIndex])}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "contain",
            objectPosition: "bottom center",
            filter: "drop-shadow(0 16px 18px rgba(0,0,0,0.20)) drop-shadow(0 40px 42px rgba(0,0,0,0.34))"
          }}
        />
      </div>

      <div
        style={{
          position: "absolute",
          left: 26,
          right: 26,
          top: 1008,
          display: "flex",
          justifyContent: "flex-start"
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: "100%",
            background: "rgba(10, 9, 13, 0.46)",
            color: "white",
            border: "1px solid rgba(255,255,255,0.05)",
            borderRadius: 30,
            padding: "22px 30px",
            fontSize: subtitleFontSize,
            fontWeight: 800,
            lineHeight: subtitleLineHeight,
            textAlign: "center",
            boxShadow: "0 10px 24px rgba(0,0,0,0.16)",
            backdropFilter: "blur(6px)"
          }}
        >
          {captionWords.map((word, index) => {
            const isActive = index < spokenWords;
            return (
              <span
                key={`${word}-${index}`}
                style={{
                  color: isActive ? "#ffd84d" : "#ffffff",
                  textShadow: isActive
                    ? "0 0 10px rgba(255,216,77,0.18)"
                    : "0 0 8px rgba(0,0,0,0.18)"
                }}
              >
                {index > 0 ? " " : ""}
                {word}
              </span>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
