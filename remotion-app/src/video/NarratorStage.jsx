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
      <div
        style={{
          position: "absolute",
          right: 18,
          bottom: -8,
          width: 430,
          height: 92,
          borderRadius: "50%",
          background: "rgba(0,0,0,0.50)",
          filter: "blur(26px)"
        }}
      />
      <div
        style={{
          position: "absolute",
          right: 70,
          bottom: 58,
          width: 360,
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
          right: 12,
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
        src={gestureUrl}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "contain",
          objectPosition: "bottom right",
          filter: "drop-shadow(0 12px 18px rgba(0,0,0,0.16)) drop-shadow(0 28px 38px rgba(0,0,0,0.32)) drop-shadow(0 0 28px rgba(0,0,0,0.06))"
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.30) 0%, rgba(0,0,0,0.18) 24%, rgba(0,0,0,0.05) 48%, rgba(0,0,0,0) 66%)",
          opacity: 0.95,
          pointerEvents: "none",
          WebkitMaskImage: `url(${gestureUrl})`,
          WebkitMaskSize: "contain",
          WebkitMaskRepeat: "no-repeat",
          WebkitMaskPosition: "bottom right",
          maskImage: `url(${gestureUrl})`,
          maskSize: "contain",
          maskRepeat: "no-repeat",
          maskPosition: "bottom right"
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 82% 42%, rgba(0,0,0,0.26) 0%, rgba(0,0,0,0.14) 24%, rgba(0,0,0,0) 52%)",
          opacity: 0.88,
          pointerEvents: "none",
          WebkitMaskImage: `url(${gestureUrl})`,
          WebkitMaskSize: "contain",
          WebkitMaskRepeat: "no-repeat",
          WebkitMaskPosition: "bottom right",
          maskImage: `url(${gestureUrl})`,
          maskSize: "contain",
          maskRepeat: "no-repeat",
          maskPosition: "bottom right"
        }}
      />
    </div>
  );
};
