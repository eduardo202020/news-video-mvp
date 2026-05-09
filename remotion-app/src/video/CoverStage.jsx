import React from "react";
import {
  makeTransform,
  scale,
  translateX,
  translateY
} from "@remotion/animation-utils";
import {Img, interpolate, staticFile} from "remotion";
import {CARD_WIDTH, COVER_HEIGHT} from "./constants";
import {withAssetVersion} from "./asset-src";

const buildCoverFocusTransform = (coverRegion, focusProgress) => {
  if (!coverRegion) {
    return makeTransform([scale(1)]);
  }

  const x = Number(coverRegion.x ?? 0);
  const y = Number(coverRegion.y ?? 0);
  const width = Math.max(0.06, Number(coverRegion.width ?? 1));
  const height = Math.max(0.06, Number(coverRegion.height ?? 1));
  const centerX = x + width / 2;
  const centerY = y + height / 2;
  const isBannerRegion = width > 0.5 && height < 0.18;
  const isWideRegion = width > height * 1.08;
  const isTallRegion = height > width * 1.08;
  const horizontalContext = isBannerRegion ? 0.04 : isWideRegion ? 0.05 : isTallRegion ? 0.08 : 0.065;
  const verticalContext = isBannerRegion ? 0.05 : isTallRegion ? 0.06 : isWideRegion ? 0.08 : 0.07;
  const paddedWidth = Math.min(1, width + horizontalContext);
  const paddedHeight = Math.min(1, height + verticalContext);

  let baseScale;
  if (isBannerRegion || isWideRegion) {
    // Wide stories should almost fill the newspaper width while keeping a little context.
    baseScale = 0.93 / paddedWidth;
  } else if (isTallRegion) {
    // Tall stories should almost fill the newspaper height while keeping top/bottom context.
    baseScale = 0.9 / paddedHeight;
  } else {
    // Near-square stories should stay conservative and preserve context on both axes.
    baseScale = Math.min(0.88 / paddedWidth, 0.84 / paddedHeight);
  }

  const targetScale = Math.max(1, Math.min(isBannerRegion ? 2.2 : 2.85, baseScale));
  const zoomScale = 1 + (targetScale - 1) * focusProgress;
  const maxTranslateX = Math.max(0, (CARD_WIDTH * (zoomScale - 1)) / 2);
  const maxTranslateY = Math.max(0, (COVER_HEIGHT * (zoomScale - 1)) / 2);
  const rawTranslateX = (0.5 - centerX) * CARD_WIDTH * zoomScale;
  const rawTranslateY = (0.5 - centerY) * COVER_HEIGHT * zoomScale;
  const translateFocusX = Math.max(-maxTranslateX, Math.min(maxTranslateX, rawTranslateX)) * focusProgress;
  const translateFocusY = Math.max(-maxTranslateY, Math.min(maxTranslateY, rawTranslateY)) * focusProgress;

  return makeTransform([translateX(translateFocusX), translateY(translateFocusY), scale(zoomScale)]);
};

const renderCoverStackStage = ({
  newspaperCoverStack,
  currentSegment,
  assetVersion,
  segmentFrame,
  segmentDuration,
  stageTransform
}) => {
  const visibleStack = newspaperCoverStack.slice(0, 6);
  const stackScale =
    visibleStack.length >= 5 ? 0.96 : visibleStack.length === 4 ? 1.05 : visibleStack.length === 3 ? 1.14 : visibleStack.length === 2 ? 1.26 : 1.38;
  const stackOffsetX =
    visibleStack.length >= 5 ? 156 : visibleStack.length === 4 ? 198 : visibleStack.length === 3 ? 238 : visibleStack.length === 2 ? 304 : 0;
  const stackWidth = CARD_WIDTH * stackScale + stackOffsetX * Math.max(0, visibleStack.length - 1);
  const stackHeight = COVER_HEIGHT * stackScale;
  const revealFrames = Math.max(18, Math.floor(segmentDuration / Math.max(1, visibleStack.length + 1)));

  return (
    <div
      style={{
        position: "absolute",
        top: -26,
        left: "50%",
        width: stackWidth,
        height: stackHeight,
        marginLeft: -(stackWidth / 2),
        transform: stageTransform
      }}
    >
      {currentSegment.headline ? (
        <div
          style={{
            position: "absolute",
            top: -72,
            left: 0,
            zIndex: 20,
            padding: "14px 22px",
            borderRadius: 999,
            background: "rgba(10,10,14,0.78)",
            border: "1px solid rgba(255,255,255,0.1)",
            boxShadow: "0 18px 48px rgba(0,0,0,0.2)",
            color: "#f8cf52",
            fontSize: 34,
            fontWeight: 700,
            letterSpacing: 1.1,
            textTransform: "uppercase"
          }}
        >
          {currentSegment.headline}
        </div>
      ) : null}
      {visibleStack
        .slice()
        .reverse()
        .map((item, reverseIndex) => {
          const index = visibleStack.length - 1 - reverseIndex;
          const revealStart = index * revealFrames;
          const revealProgress = interpolate(
            segmentFrame,
            [revealStart, revealStart + Math.min(18, revealFrames)],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp"
            }
          );
          const introTranslateX = interpolate(revealProgress, [0, 1], [72, 0]);
          const introTranslateY = interpolate(revealProgress, [0, 1], [12, 0]);
          const introOpacity = interpolate(revealProgress, [0, 1], [0, 1]);

          return (
            <div
              key={`${item.newspaperName}-${index}`}
              style={{
                position: "absolute",
                top: 0,
                left: index * stackOffsetX,
                zIndex: index + 1,
                width: CARD_WIDTH,
                height: COVER_HEIGHT,
                opacity: introOpacity,
                transform: makeTransform([
                  translateX(introTranslateX),
                  translateY(introTranslateY),
                  scale(stackScale)
                ]),
                transformOrigin: "top left",
                overflow: "hidden",
                border: "1px solid rgba(255,255,255,0.08)",
                backgroundColor: "rgba(255,255,255,0.02)"
              }}
            >
              <Img
                src={staticFile(withAssetVersion(item.coverSrc, assetVersion))}
                style={{
                  width: CARD_WIDTH,
                  height: COVER_HEIGHT,
                  objectFit: "contain",
                  display: "block"
                }}
              />
            </div>
          );
        })}
    </div>
  );
};

export const CoverStage = ({
  newspaperCoverStack,
  currentSegment,
  nextSegment,
  assetVersion,
  segmentFrame,
  segmentDuration,
  isTransitioning,
  transitionProgress,
  cardTranslateY,
  coverFloatY,
  showCoverDebug = false
}) => {
  const currentTranslateX = interpolate(transitionProgress, [0, 1], [0, -28]);
  const nextTranslateX = interpolate(transitionProgress, [0, 1], [28, 0]);
  const stageTransform = makeTransform([translateY(cardTranslateY + coverFloatY)]);
  const currentFocusProgress =
    currentSegment.segmentType === "story" && currentSegment.coverRegion
      ? interpolate(
          segmentFrame,
          [0, 18, Math.max(24, segmentDuration - 24), segmentDuration],
          [0, 1, 1, 0],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp"
          }
        )
      : 0;
  const nextFocusProgress =
    nextSegment?.segmentType === "story" && nextSegment?.coverRegion ? transitionProgress : 0;
  const currentFocusTransform = buildCoverFocusTransform(currentSegment.coverRegion, currentFocusProgress);
  const nextFocusTransform = buildCoverFocusTransform(nextSegment?.coverRegion, nextFocusProgress);
  const currentCoverTransform = makeTransform([translateX(currentTranslateX)]);
  const nextCoverTransform = makeTransform([translateX(nextTranslateX)]);

  if (
    ["intro", "outro"].includes(currentSegment.segmentType) &&
    Array.isArray(newspaperCoverStack) &&
    newspaperCoverStack.length > 0
  ) {
    return renderCoverStackStage({
      newspaperCoverStack,
      currentSegment,
      assetVersion,
      segmentFrame,
      segmentDuration,
      stageTransform
    });
  }

  return (
      <div
        style={{
          position: "absolute",
          top: -42,
        left: "50%",
        width: CARD_WIDTH,
        marginLeft: -(CARD_WIDTH / 2),
        transform: stageTransform
      }}
      >
        <div
          style={{
            position: "relative",
            width: CARD_WIDTH,
            height: COVER_HEIGHT,
            transformOrigin: "left center",
            transform: currentCoverTransform,
            opacity: isTransitioning ? interpolate(transitionProgress, [0, 1], [1, 0.1]) : 1,
            overflow: "hidden"
          }}
        >
        <Img
          src={staticFile(withAssetVersion(currentSegment.coverSrc, assetVersion))}
          style={{
            width: CARD_WIDTH,
            height: COVER_HEIGHT,
            objectFit: "contain",
            display: "block",
            transform: currentFocusTransform
          }}
        />
          </div>
      {isTransitioning ? (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: CARD_WIDTH,
            height: COVER_HEIGHT,
            transformOrigin: "right center",
            transform: nextCoverTransform,
            opacity: interpolate(transitionProgress, [0, 1], [0.2, 1]),
            overflow: "hidden"
          }}
        >
          <Img
            src={staticFile(withAssetVersion(nextSegment.coverSrc, assetVersion))}
            style={{
              width: CARD_WIDTH,
              height: COVER_HEIGHT,
              objectFit: "contain",
              display: "block",
              transform: nextFocusTransform
            }}
          />
        </div>
      ) : null}
    </div>
  );
};
