import React from "react";
import {makeTransform, scale, translateX, translateY} from "@remotion/animation-utils";
import {Img, staticFile} from "remotion";
import {getNarratorLayout} from "./layouts";
import {SHOW_NARRATOR_ANCHOR_GUIDE} from "./constants";
import {withAssetVersion} from "./asset-src";

export const NarratorStage = ({
  gestureSrc,
  assetVersion,
  narratorVariant,
  narratorTranslateY,
  narratorScale,
  narratorSegmentTranslateX,
  narratorSegmentTranslateY,
  narratorSegmentScale,
  narratorSegmentOpacity
}) => {
  const layout = getNarratorLayout(narratorVariant);
  const gestureUrl = staticFile(withAssetVersion(gestureSrc, assetVersion));
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
      {SHOW_NARRATOR_ANCHOR_GUIDE ? (
        <div
          style={{
            position: "absolute",
            right: 0,
            bottom: 0,
            width: 36,
            height: 36,
            borderRight: "3px solid rgba(255, 80, 80, 0.95)",
            borderBottom: "3px solid rgba(255, 80, 80, 0.95)",
            pointerEvents: "none",
            zIndex: 2
          }}
        />
      ) : null}
      <Img
        src={gestureUrl}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "contain",
          objectPosition: "bottom right"
        }}
      />
    </div>
  );
};
