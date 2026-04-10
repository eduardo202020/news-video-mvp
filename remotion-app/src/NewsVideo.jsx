import React from "react";
import {
  makeTransform,
  perspective,
  rotateY,
  rotateZ,
  scale,
  translateX,
  translateY
} from "@remotion/animation-utils";
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

const {fontFamily: subtitleFontFamily} = loadBarlowSemiCondensed("normal", {
  weights: ["700"],
  subsets: ["latin"]
});

const CARD_WIDTH = 929;
const COVER_HEIGHT = 1058;
const PAGE_TURN_FRAMES = 16;
const SEGMENT_GAP_FRAMES = 10;
const SUBTITLE_TOP = 1016;
const SUBTITLE_SIDE = 28;
const DEFAULT_MUSIC_SRC = "assets/fondo-musical/noticiero.mpeg";
const DEFAULT_MUSIC_VOLUME = 0.06;
const NARRATOR_LAYOUTS = {
  default: {
    right: 12,
    bottom: 0,
    width: 620,
    height: 880,
    scaleBoost: 1
  },
  magaly: {
    right: -12,
    bottom: 0,
    width: 690,
    height: 940,
    scaleBoost: 1.06
  },
  fedepico: {
    right: 40,
    bottom: 0,
    width: 560,
    height: 790,
    scaleBoost: 0.92
  }
};

const buildWordHighlights = (caption, progress) => {
  const captionWords = caption ? caption.split(" ") : [];
  const spokenWords = Math.floor(captionWords.length * progress);

  return captionWords.map((word, index) => ({
    key: `${word}-${index}`,
    text: `${index > 0 ? " " : ""}${word}`,
    active: index < spokenWords
  }));
};

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

const getNarratorLayout = (name) => {
  const normalized = String(name ?? "")
    .trim()
    .toLowerCase();

  return NARRATOR_LAYOUTS[normalized] ?? NARRATOR_LAYOUTS.default;
};

const CoverStage = ({
  currentSegment,
  nextSegment,
  isTransitioning,
  transitionProgress,
  cardTranslateY,
  coverFloatY
}) => {
  const currentRotateY = interpolate(transitionProgress, [0, 1], [0, 88]);
  const nextRotateY = interpolate(transitionProgress, [0, 1], [-88, 0]);
  const currentTranslateX = interpolate(transitionProgress, [0, 1], [0, -60]);
  const nextTranslateX = interpolate(transitionProgress, [0, 1], [150, 0]);
  const currentShadow = interpolate(transitionProgress, [0, 1], [0.32, 0.08]);
  const nextShadow = interpolate(transitionProgress, [0, 1], [0.04, 0.32]);
  const specularTravel = interpolate(transitionProgress, [0, 1], [-96, 96]);
  const pageCurlWidth = interpolate(transitionProgress, [0, 1], [22, 74]);
  const pageCurlOpacity = interpolate(transitionProgress, [0, 1], [0.08, 0.6]);
  const stageTransform = makeTransform([
    translateY(cardTranslateY + coverFloatY)
  ]);
  const currentCoverTransform = makeTransform([
    perspective(1800),
    translateX(currentTranslateX),
    rotateY(currentRotateY),
    rotateZ(-0.35)
  ]);
  const nextCoverTransform = makeTransform([
    perspective(1800),
    translateX(nextTranslateX),
    rotateY(nextRotateY),
    rotateZ(0.25)
  ]);

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: "50%",
        width: CARD_WIDTH,
        marginLeft: -(CARD_WIDTH / 2),
        transform: stageTransform,
        filter: "drop-shadow(0 34px 52px rgba(0,0,0,0.30))"
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 20,
          left: 30,
          width: CARD_WIDTH - 70,
          height: COVER_HEIGHT - 44,
          borderRadius: 22,
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.05) 16%, rgba(255,255,255,0) 38%)",
          opacity: 0.34,
          transform: makeTransform([translateY(12), scale(0.985)]),
          filter: "blur(10px)"
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 26,
          left: 44,
          width: CARD_WIDTH - 90,
          height: COVER_HEIGHT - 56,
          borderRadius: 26,
          background: "rgba(0,0,0,0.10)",
          transform: makeTransform([translateY(18)]),
          filter: "blur(12px)",
          opacity: 0.42
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 28,
          left: 18,
          width: CARD_WIDTH - 18,
          height: COVER_HEIGHT - 36,
          borderRadius: 20,
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.02) 20%, rgba(255,255,255,0) 40%)",
          opacity: 0.35,
          filter: "blur(16px)"
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
          transform: currentCoverTransform,
          opacity: isTransitioning ? interpolate(transitionProgress, [0, 1], [1, 0.2]) : 1,
          filter: `drop-shadow(0 20px 20px rgba(0,0,0,0.12)) drop-shadow(0 36px 48px rgba(0,0,0,${currentShadow}))`
        }}
      />
      {isTransitioning ? (
        <div
          style={{
            position: "absolute",
            top: 16,
            right: 14,
            width: pageCurlWidth,
            height: COVER_HEIGHT - 36,
            borderTopRightRadius: 18,
            borderBottomRightRadius: 18,
            background:
              "linear-gradient(90deg, rgba(250,246,238,0.08) 0%, rgba(236,228,214,0.54) 38%, rgba(187,177,161,0.92) 100%)",
            opacity: pageCurlOpacity,
            filter: "blur(0.6px)",
            transformOrigin: "right center",
            transform: makeTransform([
              perspective(1200),
              rotateY(interpolate(transitionProgress, [0, 1], [-12, -74]))
            ])
          }}
        />
      ) : null}
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
            transform: nextCoverTransform,
            opacity: interpolate(transitionProgress, [0, 1], [0.4, 1]),
            filter: `drop-shadow(0 18px 18px rgba(0,0,0,0.10)) drop-shadow(0 34px 44px rgba(0,0,0,${nextShadow}))`
          }}
        />
      ) : null}
      <div
        style={{
          position: "absolute",
          top: 18,
          left: 18,
          width: 24,
          height: COVER_HEIGHT - 48,
          borderRadius: 12,
          background:
            "linear-gradient(90deg, rgba(0,0,0,0.18) 0%, rgba(255,255,255,0.10) 52%, rgba(255,255,255,0) 100%)",
          opacity: isTransitioning ? 0.18 : 0.3,
          filter: "blur(1px)"
        }}
      />
      {isTransitioning ? (
        <div
          style={{
            position: "absolute",
            top: 4,
            left: CARD_WIDTH / 2 - 40,
            width: 78,
            height: COVER_HEIGHT - 8,
            background:
              "linear-gradient(90deg, rgba(0,0,0,0.44) 0%, rgba(0,0,0,0.10) 30%, rgba(255,255,255,0.18) 58%, rgba(0,0,0,0.24) 100%)",
            opacity: interpolate(transitionProgress, [0, 1], [0.05, 0.44]),
            transform: makeTransform([translateX(specularTravel * 0.72)]),
            filter: "blur(8px)"
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
            transform: makeTransform([translateX(specularTravel)]),
            filter: "blur(4px)"
          }}
        />
      ) : null}
    </div>
  );
};

const NarratorStage = ({
  gestureSrc,
  narratorVariant,
  narratorTranslateY,
  narratorScale,
  narratorSegmentTranslateX,
  narratorSegmentTranslateY,
  narratorSegmentScale,
  narratorSegmentOpacity
}) => {
  const layout = getNarratorLayout(narratorVariant);
  const narratorTransform = makeTransform([
    translateX(narratorSegmentTranslateX),
    translateY(narratorTranslateY + narratorSegmentTranslateY),
    scale(narratorScale * narratorSegmentScale * layout.scaleBoost)
  ]);

  return (
    <div
      style={{
        position: "absolute",
        right: layout.right,
        bottom: layout.bottom,
        width: layout.width,
        height: layout.height,
        transform: narratorTransform,
        opacity: narratorSegmentOpacity,
        transformOrigin: "bottom right"
      }}
    >
        <div
          style={{
            position: "absolute",
            left: 74,
            bottom: -8,
            width: 500,
            height: 92,
            borderRadius: "50%",
            background: "rgba(0,0,0,0.50)",
            filter: "blur(26px)"
          }}
        />
      <div
        style={{
          position: "absolute",
          left: 98,
          bottom: 58,
          width: 420,
          height: 540,
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.01) 34%, rgba(255,255,255,0) 100%)",
          filter: "blur(24px)",
          opacity: 0.36
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
      <div
        style={{
          position: "absolute",
          inset: "11% 11% 7% 11%",
          borderRadius: "50%",
          background: "radial-gradient(circle at 52% 44%, rgba(255,82,58,0.12) 0%, rgba(255,82,58,0.05) 26%, rgba(255,82,58,0) 70%)",
          filter: "blur(34px)"
        }}
      />
        <Img
          src={staticFile(gestureSrc)}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "contain",
            objectPosition: "bottom center",
            filter: "drop-shadow(0 12px 18px rgba(0,0,0,0.16)) drop-shadow(0 28px 38px rgba(0,0,0,0.32)) drop-shadow(0 0 28px rgba(0,0,0,0.06))"
          }}
        />
    </div>
  );
};

const CaptionBar = ({captionWords, subtitleFontSize, subtitleLineHeight}) => {
  return (
    <div
      style={{
        position: "absolute",
        left: SUBTITLE_SIDE,
        right: SUBTITLE_SIDE,
        top: SUBTITLE_TOP,
        display: "flex",
        justifyContent: "center"
      }}
    >
      <div
        style={{
          width: "100%",
          background:
            "linear-gradient(180deg, rgba(14,12,16,0.42) 0%, rgba(10,9,13,0.52) 100%)",
          color: "white",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 30,
          padding: "20px 34px",
          fontSize: subtitleFontSize,
          fontWeight: 700,
          lineHeight: subtitleLineHeight,
          textAlign: "center",
          boxShadow: "0 14px 30px rgba(0,0,0,0.16)",
          backdropFilter: "blur(8px)",
          letterSpacing: 0.15
        }}
      >
        {captionWords.map((word) => (
          <span
            key={word.key}
            style={{
              color: word.active ? "#ffd84d" : "#ffffff",
              textShadow: word.active
                ? "0 0 10px rgba(255,216,77,0.18)"
                : "0 0 8px rgba(0,0,0,0.18)"
            }}
          >
            {word.text}
          </span>
        ))}
      </div>
    </div>
  );
};

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
  const gestureIndex = Math.floor(frame / (fps * 2)) % activeGestures.length;
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
