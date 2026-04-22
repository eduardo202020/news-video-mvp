import React from "react";
import {SUBTITLE_SIDE, SUBTITLE_TOP} from "./constants";

export const CaptionBar = ({captionWords, subtitleFontSize, subtitleLineHeight}) => {
  const verticalPadding = 42;
  const minCaptionHeight = Math.ceil(subtitleFontSize * subtitleLineHeight * 2 + verticalPadding);

  return (
    <div
      style={{
        position: "absolute",
        left: SUBTITLE_SIDE,
        right: SUBTITLE_SIDE,
        top: SUBTITLE_TOP,
        zIndex: 200,
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
          padding: "15px 28px",
          fontSize: subtitleFontSize,
          fontWeight: 700,
          lineHeight: subtitleLineHeight,
          textAlign: "center",
          minHeight: minCaptionHeight,
          overflow: "visible",
          whiteSpace: "normal",
          wordBreak: "break-word",
          boxShadow: "0 14px 30px rgba(0,0,0,0.16)",
          letterSpacing: 0
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
