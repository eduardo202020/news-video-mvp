import React from "react";
import {
  makeTransform,
  scale,
  translateX,
  translateY
} from "@remotion/animation-utils";
import {Img, interpolate, staticFile} from "remotion";
import {CARD_WIDTH, COVER_HEIGHT} from "./constants";

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
  const isWideRegion = width > 0.5;
  const paddedWidth = Math.min(1, width + (isBannerRegion ? 0.05 : isWideRegion ? 0.03 : 0.045));
  const paddedHeight = Math.min(1, height + (isBannerRegion ? 0.05 : 0.045));
  const largeRegionBoost = isBannerRegion ? 1.02 : isWideRegion ? 1.08 : width > 0.38 || height > 0.18 ? 1.04 : 1.1;
  const horizontalFit = isBannerRegion ? 0.88 / paddedWidth : isWideRegion ? 0.92 / paddedWidth : 0.8 / paddedWidth;
  const verticalFit = isBannerRegion ? 0.78 / paddedHeight : 0.64 / paddedHeight;
  const baseScale = Math.min(horizontalFit, verticalFit);
  const targetScale = Math.max(1, Math.min(isBannerRegion ? 2.15 : 2.75, baseScale * largeRegionBoost));
  const zoomScale = 1 + (targetScale - 1) * focusProgress;
  const maxTranslateX = Math.max(0, (CARD_WIDTH * (zoomScale - 1)) / 2);
  const maxTranslateY = Math.max(0, (COVER_HEIGHT * (zoomScale - 1)) / 2);
  const rawTranslateX = (0.5 - centerX) * CARD_WIDTH * zoomScale;
  const rawTranslateY = (0.5 - centerY) * COVER_HEIGHT * zoomScale;
  const translateFocusX = Math.max(-maxTranslateX, Math.min(maxTranslateX, rawTranslateX)) * focusProgress;
  const translateFocusY = Math.max(-maxTranslateY, Math.min(maxTranslateY, rawTranslateY)) * focusProgress;

  return makeTransform([translateX(translateFocusX), translateY(translateFocusY), scale(zoomScale)]);
};

export const CoverStage = ({
  newspaperCoverStack,
  currentSegment,
  nextSegment,
  segmentFrame,
  segmentDuration,
  isTransitioning,
  transitionProgress,
  cardTranslateY,
  coverFloatY
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
  const connectorProgress =
    currentSegment.segmentType === "connector"
      ? interpolate(segmentFrame, [0, Math.max(18, segmentDuration - 18), segmentDuration], [0, 1, 0.92], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp"
        })
      : 0;
  const connectorOverlayOpacity =
    currentSegment.segmentType === "connector"
      ? interpolate(segmentFrame, [0, 10, Math.max(16, segmentDuration - 18), segmentDuration], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp"
        })
      : 0;
  const connectorScale = interpolate(connectorProgress, [0, 1], [1.035, 1]);

  if (currentSegment.segmentType === "intro" && Array.isArray(newspaperCoverStack) && newspaperCoverStack.length > 0) {
    const introStack = newspaperCoverStack.slice(0, 6);
    const stackScale =
      introStack.length >= 5 ? 0.96 : introStack.length === 4 ? 1.05 : introStack.length === 3 ? 1.14 : introStack.length === 2 ? 1.26 : 1.38;
    const stackOffsetX =
      introStack.length >= 5 ? 156 : introStack.length === 4 ? 198 : introStack.length === 3 ? 238 : introStack.length === 2 ? 304 : 0;
    const stackWidth = CARD_WIDTH * stackScale + stackOffsetX * Math.max(0, introStack.length - 1);
    const stackHeight = COVER_HEIGHT * stackScale;
    const introRevealFrames = Math.max(18, Math.floor(segmentDuration / Math.max(1, introStack.length + 1)));
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
        {introStack
          .slice()
          .reverse()
          .map((item, reverseIndex) => {
            const index = introStack.length - 1 - reverseIndex;
            const offsetX = index * stackOffsetX;
            const offsetY = 0;
            const revealStart = index * introRevealFrames;
            const revealProgress = interpolate(
              segmentFrame,
              [revealStart, revealStart + Math.min(18, introRevealFrames)],
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
                  top: offsetY,
                  left: offsetX,
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
                  src={staticFile(item.coverSrc)}
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
            transform:
              currentSegment.segmentType === "connector"
                ? makeTransform([translateX(currentTranslateX), scale(connectorScale)])
                : currentCoverTransform,
            opacity: isTransitioning ? interpolate(transitionProgress, [0, 1], [1, 0.1]) : 1,
            overflow: "hidden"
          }}
        >
        <Img
          src={staticFile(currentSegment.coverSrc)}
          style={{
            width: CARD_WIDTH,
            height: COVER_HEIGHT,
            objectFit: "contain",
            display: "block",
            transform: currentFocusTransform
          }}
        />
          {currentSegment.segmentType === "connector" ? (
            <>
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background:
                    "linear-gradient(180deg, rgba(11,10,14,0.16) 0%, rgba(11,10,14,0.02) 32%, rgba(11,10,14,0.56) 100%)"
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 34,
                  right: 34,
                  bottom: 38,
                  opacity: connectorOverlayOpacity,
                  display: "flex",
                  justifyContent: "center"
                }}
              >
                <div
                  style={{
                    maxWidth: 840,
                    padding: "24px 30px",
                    borderRadius: 28,
                    background: "rgba(10,10,14,0.68)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    boxShadow: "0 24px 54px rgba(0,0,0,0.28)",
                    textAlign: "center",
                    backdropFilter: "blur(8px)"
                  }}
                >
                  <div
                    style={{
                      color: "#f8cf52",
                      fontSize: 34,
                      fontWeight: 700,
                      letterSpacing: 1.4,
                      textTransform: "uppercase"
                    }}
                  >
                    {currentSegment.newspaperName}
                  </div>
                  <div
                    style={{
                      marginTop: 10,
                      color: "white",
                      fontSize: 56,
                      fontWeight: 700,
                      lineHeight: 1.02
                    }}
                  >
                    {currentSegment.headline || `Entramos a ${currentSegment.newspaperName}`}
                  </div>
                </div>
              </div>
            </>
          ) : null}
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
            src={staticFile(nextSegment.coverSrc)}
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
