import React from "react";
import {interpolate, spring} from "remotion";
import {SUBTITLE_SIDE} from "./constants";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  XAxis,
  YAxis
} from "recharts";

const DEFAULT_ACCENT = "#f5c451";
const CARD_WIDTH = 1080 - SUBTITLE_SIDE * 2;
const CARD_HEIGHT = 620;
const CHART_WIDTH = CARD_WIDTH - 44;
const CHART_HEIGHT = CARD_HEIGHT - 176;
const CARD_BG = "rgba(255,255,255,0.40)";
const TEXT_PRIMARY = "#111827";
const TEXT_SECONDARY = "rgba(17,24,39,0.82)";
const TEXT_MUTED = "rgba(17,24,39,0.68)";

const formatMetricValue = (value, unit) => {
  const rounded = Number.isInteger(value) ? `${value}` : `${value.toFixed(1)}`;
  return unit ? `${rounded}${unit}` : rounded;
};

const AnimatedChart = ({supportVisual, segmentFrame, fps}) => {
  const data = Array.isArray(supportVisual?.points) ? supportVisual.points : [];
  const chartType = `${supportVisual?.chart_type ?? "line"}`.toLowerCase();
  const accentColor = supportVisual?.color ?? DEFAULT_ACCENT;
  const unit = supportVisual?.unit ?? "";
  const commonProps = {
    data,
    width: CHART_WIDTH,
    height: CHART_HEIGHT,
    margin: {top: 12, right: 10, left: -12, bottom: 8}
  };

  const labelFormatter = (value) => formatMetricValue(Number(value), unit);
  const renderBarShape = (shapeProps) => {
    const barIndex = Number(shapeProps.index ?? 0);
    const progress = spring({
      fps,
      frame: segmentFrame - 12 - barIndex * 8,
      config: {damping: 20, stiffness: 92}
    });
    const safeHeight = Math.max(0, shapeProps.height ?? 0);
    const animatedHeight = safeHeight * progress;
    const animatedY = (shapeProps.y ?? 0) + (safeHeight - animatedHeight);

    return (
      <g>
        <rect
          x={shapeProps.x}
          y={animatedY}
          width={shapeProps.width}
          height={animatedHeight}
          rx={12}
          ry={12}
          fill={shapeProps.fill}
        />
      </g>
    );
  };

  if (chartType === "bar") {
    return (
      <BarChart {...commonProps}>
        <CartesianGrid stroke="rgba(17,24,39,0.16)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{fill: TEXT_SECONDARY, fontSize: 26, fontWeight: 800}}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{fill: TEXT_MUTED, fontSize: 20, fontWeight: 700}}
          axisLine={false}
          tickLine={false}
          width={66}
        />
        <Bar
          dataKey="value"
          fill={accentColor}
          radius={[12, 12, 4, 4]}
          isAnimationActive={false}
          shape={renderBarShape}
        >
          <LabelList
            dataKey="value"
            position="top"
            formatter={labelFormatter}
            style={{fill: "#553300", fontSize: 21, fontWeight: 900}}
          />
        </Bar>
      </BarChart>
    );
  }

  if (chartType === "area") {
    return (
      <AreaChart {...commonProps}>
        <defs>
          <linearGradient id="supportVisualFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={accentColor} stopOpacity={0.7} />
            <stop offset="100%" stopColor={accentColor} stopOpacity={0.12} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(17,24,39,0.16)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{fill: TEXT_SECONDARY, fontSize: 26, fontWeight: 800}}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{fill: TEXT_MUTED, fontSize: 20, fontWeight: 700}}
          axisLine={false}
          tickLine={false}
          width={66}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={accentColor}
          strokeWidth={5}
          fill="url(#supportVisualFill)"
          isAnimationActive={false}
        />
      </AreaChart>
    );
  }

  return (
    <LineChart {...commonProps}>
      <CartesianGrid stroke="rgba(17,24,39,0.16)" vertical={false} />
      <XAxis
        dataKey="label"
        tick={{fill: TEXT_SECONDARY, fontSize: 26, fontWeight: 800}}
        axisLine={false}
        tickLine={false}
      />
      <YAxis
        tick={{fill: TEXT_MUTED, fontSize: 20, fontWeight: 700}}
        axisLine={false}
        tickLine={false}
        width={66}
      />
      <Line
        type="monotone"
        dataKey="value"
        stroke={accentColor}
        strokeWidth={5}
        dot={{r: 6, strokeWidth: 0, fill: accentColor}}
        activeDot={false}
        isAnimationActive={false}
      >
        <LabelList
          dataKey="value"
          position="top"
          formatter={labelFormatter}
          style={{fill: "#553300", fontSize: 21, fontWeight: 900}}
        />
      </Line>
    </LineChart>
  );
};

export const SupportVisualStage = ({supportVisual, segmentFrame, fps, segmentDuration}) => {
  if (!supportVisual || supportVisual.type !== "numeric_chart") {
    return null;
  }

  const entrance = spring({
    fps,
    frame: segmentFrame - 6,
    config: {damping: 16, stiffness: 130}
  });
  const revealProgress = interpolate(
    segmentFrame,
    [6, Math.min(segmentDuration - 8, 24)],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }
  );
  const exitFade = interpolate(
    segmentFrame,
    [Math.max(0, segmentDuration - 10), segmentDuration],
    [1, 0.82],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }
  );
  const translateY = interpolate(entrance, [0, 1], [26, 0]);
  const opacity = interpolate(entrance, [0, 1], [0, 1]) * exitFade;
  const clipWidth = Math.round(CARD_WIDTH * revealProgress);

  return (
    <div
      style={{
        position: "absolute",
        left: SUBTITLE_SIDE,
        right: SUBTITLE_SIDE,
        top: 1310,
        width: "auto",
        height: CARD_HEIGHT,
        borderRadius: 42,
        padding: "30px 22px 18px",
        background: CARD_BG,
        border: "1px solid rgba(255,255,255,0.16)",
        boxShadow: "0 20px 56px rgba(0,0,0,0.14)",
        transform: `translateY(${translateY}px)`,
        opacity,
        overflow: "hidden",
        zIndex: 180,
        backdropFilter: "blur(5px)"
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
          alignItems: "flex-start",
          marginBottom: 10
        }}
      >
        <div>
          <div
            style={{
              color: TEXT_PRIMARY,
              fontSize: 48,
              fontWeight: 900,
              lineHeight: 1.05
            }}
          >
            {supportVisual.title ?? "Contexto numerico"}
          </div>
          {supportVisual.subtitle ? (
            <div
              style={{
                marginTop: 6,
                color: TEXT_SECONDARY,
                fontSize: 26,
                fontWeight: 600,
                lineHeight: 1.2
              }}
            >
              {supportVisual.subtitle}
            </div>
          ) : null}
        </div>
        {supportVisual.highlight_label ? (
          <div
            style={{
              color: "#8f6800",
              fontSize: 22,
              fontWeight: 900,
              textTransform: "uppercase",
              letterSpacing: 0.8,
              paddingTop: 4
            }}
          >
            {supportVisual.highlight_label}
          </div>
        ) : null}
      </div>

      <div
        style={{
          width: clipWidth,
          height: CARD_HEIGHT - 118,
          overflow: "hidden",
          borderRadius: 28,
          background: "transparent",
          border: "none",
          boxShadow: "none"
        }}
      >
        <AnimatedChart supportVisual={supportVisual} segmentFrame={segmentFrame} fps={fps} />
      </div>

      {supportVisual.data_source_note ? (
        <div
          style={{
            position: "absolute",
            left: 24,
            right: 24,
            bottom: 14,
            color: "rgba(17,24,39,0.72)",
            fontSize: 18,
            fontWeight: 600,
            lineHeight: 1.2
          }}
        >
          {supportVisual.data_source_note}
        </div>
      ) : null}
    </div>
  );
};
