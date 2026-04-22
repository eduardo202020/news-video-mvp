import React from "react";
import {makeTransform, scale, translateX, translateY} from "@remotion/animation-utils";
import {Img, staticFile} from "remotion";
import {getNarratorLayout} from "./layouts";

export const NarratorStage = ({
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
  const gestureUrl = staticFile(gestureSrc);
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
