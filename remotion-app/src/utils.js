const MAX_CAPTION_CHARS = 72;
const SENTENCE_WRAP_CHARS = 90;
const MIN_CAPTION_SECONDS = 1.4;

const normalizeWhitespace = (text) => text.replace(/\s+/g, " ").trim();

const wrapWords = (text, maxChars) => {
  const clean = normalizeWhitespace(text);
  if (!clean) return [];

  const words = clean.split(" ");
  const chunks = [];
  let current = "";

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > maxChars) {
      if (current) chunks.push(current);
      current = word;
    } else {
      current = candidate;
    }
  }

  if (current) {
    chunks.push(current);
  }

  return chunks;
};

export const splitIntoCaptionChunks = (text, maxChars = MAX_CAPTION_CHARS) => {
  const clean = normalizeWhitespace(text);
  if (!clean) return [];

  const sentences = [];
  let current = "";
  for (const char of clean) {
    current += char;
    if (".!?;".includes(char)) {
      const sentence = current.trim();
      if (sentence) {
        sentences.push(sentence);
      }
      current = "";
    }
  }

  if (current.trim()) {
    sentences.push(...wrapWords(current.trim(), SENTENCE_WRAP_CHARS));
  }

  return sentences.flatMap((sentence) =>
    sentence.length <= maxChars ? [sentence] : wrapWords(sentence, maxChars)
  );
};

const rebalanceCaptionSegments = (segments, totalFrames) => {
  if (segments.length === 0) {
    return [];
  }

  const balanced = [];
  let cursor = 0;

  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];
    const remaining = segments.length - index;
    const remainingFrames = Math.max(totalFrames - cursor, remaining);
    const minSlice = remainingFrames / remaining;
    const segmentDuration = Math.max(segment.endFrame - segment.startFrame, Math.min(42, minSlice));
    const endFrame = Math.min(totalFrames, cursor + segmentDuration);

    balanced.push({
      ...segment,
      startFrame: cursor,
      endFrame
    });
    cursor = endFrame;
  }

  balanced[balanced.length - 1].endFrame = totalFrames;
  return balanced;
};

export const buildCaptionSegments = ({text, durationInFrames, fps}) => {
  const chunks = splitIntoCaptionChunks(text);
  if (chunks.length === 0) {
    return [];
  }

  const totalChars = chunks.reduce((sum, chunk) => sum + Math.max(chunk.length, 1), 0);
  const totalDurationSeconds = durationInFrames / fps;

  let cursorSeconds = 0;
  const segments = chunks.map((chunk, index) => {
    const weight = Math.max(chunk.length, 1) / totalChars;
    const durationSeconds =
      index === chunks.length - 1
        ? Math.max(totalDurationSeconds - cursorSeconds, MIN_CAPTION_SECONDS)
        : Math.max(MIN_CAPTION_SECONDS, totalDurationSeconds * weight);
    const startFrame = Math.round(cursorSeconds * fps);
    const endFrame =
      index === chunks.length - 1
        ? durationInFrames
        : Math.min(durationInFrames, Math.round((cursorSeconds + durationSeconds) * fps));

    cursorSeconds += durationSeconds;
    return {
      text: chunk,
      startFrame,
      endFrame
    };
  });

  return rebalanceCaptionSegments(segments, durationInFrames);
};

export const getCaptionStateForFrame = ({text, frame, durationInFrames, fps = 30}) => {
  const segments = buildCaptionSegments({text, durationInFrames, fps});
  if (segments.length === 0) {
    return {
      text: "",
      progress: 0
    };
  }

  const segment =
    segments.find((item) => frame >= item.startFrame && frame < item.endFrame) ??
    segments[segments.length - 1];
  const segmentDuration = Math.max(1, segment.endFrame - segment.startFrame);
  const localProgress = Math.min(
    1,
    Math.max(0, (frame - segment.startFrame) / segmentDuration)
  );

  return {
    text: segment.text,
    progress: localProgress
  };
};

export const getCaptionForFrame = ({text, frame, durationInFrames}) =>
  getCaptionStateForFrame({text, frame, durationInFrames}).text;
