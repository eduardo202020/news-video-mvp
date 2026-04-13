import {generatedStory} from "../generated-story.js";
import {defaultStory, stories} from "./demo-stories.js";
import {DEFAULT_MUSIC_SRC, DEFAULT_MUSIC_VOLUME, VIDEO_SPEC} from "./defaults.js";

const normalizeSegment = (segment, fallbackStory) => ({
  newspaperName: segment.newspaperName ?? fallbackStory.newspaperName,
  coverSrc: segment.coverSrc ?? fallbackStory.coverSrc,
  text: segment.text ?? fallbackStory.text,
  narratorName: segment.narratorName ?? fallbackStory.narratorName,
  gestures: segment.gestures?.length ? segment.gestures : fallbackStory.gestures
});

export const normalizeStory = (story) => {
  const baseStory = {
    ...story,
    fps: story.fps ?? VIDEO_SPEC.fps,
    musicSrc: story.musicSrc ?? DEFAULT_MUSIC_SRC,
    musicVolume: story.musicVolume ?? DEFAULT_MUSIC_VOLUME
  };

  const segments =
    baseStory.segments?.length > 0
      ? baseStory.segments.map((segment) => normalizeSegment(segment, baseStory))
      : [normalizeSegment(baseStory, baseStory)];

  return {
    ...baseStory,
    segments,
    newspaperName: segments[0].newspaperName,
    coverSrc: segments[0].coverSrc,
    narratorName: segments[0].narratorName,
    text: baseStory.text ?? segments.map((segment) => segment.text).join(" "),
    gestures: baseStory.gestures?.length ? baseStory.gestures : segments[0].gestures
  };
};

export const studioStories = Object.fromEntries(
  Object.entries(stories).map(([key, story]) => [key, normalizeStory(story)])
);

export const studioDefaultStory = normalizeStory(defaultStory);
export const latestGeneratedStory = normalizeStory(generatedStory);
