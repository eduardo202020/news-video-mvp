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
import {Img, interpolate, staticFile} from "remotion";
import {CARD_WIDTH, COVER_HEIGHT} from "./constants";

export const CoverStage = ({
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
  const stageTransform = makeTransform([translateY(cardTranslateY + coverFloatY)]);
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
        top: -42,
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
