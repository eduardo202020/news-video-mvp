import {interpolate} from "remotion";
import {PAGE_TURN_FRAMES} from "./constants.js";
import {buildWordHighlights} from "./helpers.js";

const GESTURE_SWITCH_SECONDS = 0.8;

const hashString = (value) => {
  const text = String(value ?? "");
  let hash = 2166136261;

  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return hash >>> 0;
};

const createSeededRandom = (seed) => {
  let state = seed >>> 0;

  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
};

const shuffleGestures = (gestures, seedSource) => {
  if (!Array.isArray(gestures) || gestures.length <= 1) {
    return Array.isArray(gestures) ? gestures : [];
  }

  const shuffled = [...gestures];
  const random = createSeededRandom(hashString(seedSource));

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
  }

  return shuffled;
};

export const resolveTimeline = ({frame, fps, durationInFrames, story}) => {
  const sequence = story.segments;
  const transitionFlags = sequence.map((segment, index) => {
    if (index >= sequence.length - 1) {
      return false;
    }

    return (segment.newspaperName ?? "") !== (sequence[index + 1]?.newspaperName ?? "");
  });
  const transitionCount = transitionFlags.filter(Boolean).length;
  const resolvedDurations = sequence.map((segment) =>
    Math.max(
      1,
      Math.round(
        (segment.durationSeconds ?? durationInFrames / Math.max(1, fps * sequence.length)) * fps
      )
    )
  );
  const segmentStarts = [];
  let cursor = 0;

  for (let index = 0; index < sequence.length; index += 1) {
    segmentStarts.push(cursor);
    cursor += resolvedDurations[index];
  }

  let activeIndex = sequence.length - 1;
  for (let index = 0; index < segmentStarts.length; index += 1) {
    const start = segmentStarts[index];
    const nextStart = segmentStarts[index + 1] ?? Number.POSITIVE_INFINITY;
    if (frame >= start && frame < nextStart) {
      activeIndex = index;
      break;
    }
  }
  const currentSegment = sequence[activeIndex];
  const nextSegment = sequence[Math.min(sequence.length - 1, activeIndex + 1)];
  const localBlockStart = segmentStarts[activeIndex];
  const segmentFrame = frame - localBlockStart;
  const segmentDuration = resolvedDurations[activeIndex];
  const spokenSegmentDuration = Math.max(
    1,
    Math.round((currentSegment.audioDurationSeconds ?? currentSegment.durationSeconds ?? 0) * fps)
  );
  const isInSegmentPause = segmentFrame >= spokenSegmentDuration && segmentDuration > spokenSegmentDuration;
  const shouldTransition = transitionFlags[activeIndex];
  const isTransitioning =
    shouldTransition && activeIndex < sequence.length - 1 && segmentFrame >= segmentDuration - PAGE_TURN_FRAMES;

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

  const subtitleSegments = Array.isArray(story.subtitleSegments) ? story.subtitleSegments : [];
  const activeSubtitle =
    subtitleSegments.find((item) => {
      const startFrame = Math.round((item.start ?? 0) * fps);
      const endFrame = Math.max(startFrame + 1, Math.round((item.end ?? 0) * fps));
      return frame >= startFrame && frame < endFrame;
    }) ?? null;
  const subtitleStartFrame = activeSubtitle ? Math.round((activeSubtitle.start ?? 0) * fps) : 0;
  const subtitleEndFrame = activeSubtitle
    ? Math.max(subtitleStartFrame + 1, Math.round((activeSubtitle.end ?? 0) * fps))
    : Math.max(1, segmentDuration);
  const subtitleProgress = activeSubtitle
    ? Math.max(0, Math.min(1, (frame - subtitleStartFrame) / Math.max(1, subtitleEndFrame - subtitleStartFrame)))
    : Math.max(0, Math.min(1, segmentFrame / Math.max(1, segmentDuration)));
  const captionText = isInSegmentPause ? "" : activeSubtitle?.text ?? currentSegment.text;

  const baseGestures = currentSegment.gestures?.length ? currentSegment.gestures : story.gestures;
  const gestureSeed = [
    activeIndex,
    currentSegment.narratorName ?? story.narratorName,
    currentSegment.headline ?? "",
    currentSegment.text ?? ""
  ].join("|");
  const activeGestures = shuffleGestures(baseGestures, gestureSeed);
  const gestureIntervalFrames = Math.max(1, Math.round(fps * GESTURE_SWITCH_SECONDS));
  const gestureFrame = isInSegmentPause
    ? Math.max(0, spokenSegmentDuration - 1)
    : Math.max(0, Math.min(segmentFrame, spokenSegmentDuration - 1));
  const gestureIndex = Math.floor(gestureFrame / gestureIntervalFrames) % activeGestures.length;
  const activeNarratorName = currentSegment.narratorName ?? story.narratorName;
  const subtitleLength = captionText.length;

  return {
    sequence,
    segmentDuration,
    activeIndex,
    currentSegment,
    nextSegment,
    segmentFrame,
    isTransitioning,
    transitionProgress,
    activeGestures,
    activeNarratorName,
    activeGestureSrc: activeGestures[gestureIndex],
    captionWords: buildWordHighlights(captionText, subtitleProgress),
    subtitleFontSize:
      subtitleLength > 120 ? 54 : subtitleLength > 100 ? 58 : subtitleLength > 82 ? 64 : subtitleLength > 64 ? 72 : 78,
    subtitleLineHeight: subtitleLength > 96 ? 1.02 : 1.04
  };
};
