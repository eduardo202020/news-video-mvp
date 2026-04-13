import {interpolate} from "remotion";
import {getCaptionStateForFrame} from "../utils.js";
import {PAGE_TURN_FRAMES, SEGMENT_GAP_FRAMES} from "./constants.js";
import {buildWordHighlights} from "./helpers.js";

export const resolveTimeline = ({frame, fps, durationInFrames, story}) => {
  const sequence = story.segments;
  const segmentDuration = Math.max(
    1,
    Math.floor((durationInFrames - PAGE_TURN_FRAMES * Math.max(sequence.length - 1, 0)) / sequence.length)
  );
  const totalSegmentBlock = segmentDuration + PAGE_TURN_FRAMES;
  const segmentStride = Math.max(1, totalSegmentBlock - SEGMENT_GAP_FRAMES);
  const activeIndex = Math.min(sequence.length - 1, Math.floor(frame / segmentStride));
  const currentSegment = sequence[activeIndex];
  const nextSegment = sequence[Math.min(sequence.length - 1, activeIndex + 1)];
  const localBlockStart = activeIndex * segmentStride;
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
    durationInFrames: isTransitioning ? segmentDuration : Math.max(1, segmentDuration - SEGMENT_GAP_FRAMES),
    fps
  });

  const activeGestures = currentSegment.gestures?.length ? currentSegment.gestures : story.gestures;
  const gestureIndex = Math.floor(frame / fps) % activeGestures.length;
  const activeNarratorName = currentSegment.narratorName ?? story.narratorName;
  const subtitleLength = captionState.text.length;

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
    captionWords: buildWordHighlights(captionState.text, captionState.progress),
    subtitleFontSize:
      subtitleLength > 120 ? 47 : subtitleLength > 90 ? 52 : subtitleLength > 65 ? 57 : 62,
    subtitleLineHeight: subtitleLength > 120 ? 1.08 : 1.12
  };
};
