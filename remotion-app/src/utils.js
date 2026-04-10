export const splitIntoCaptionChunks = (text, maxChars = 140) => {
  const clean = text.replace(/\s+/g, " ").trim();
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

  if (current) chunks.push(current);
  return chunks;
};

export const getCaptionStateForFrame = ({text, frame, durationInFrames}) => {
  const chunks = splitIntoCaptionChunks(text);
  if (chunks.length === 0) {
    return {
      text: "",
      progress: 0
    };
  }
  const chunkDuration = durationInFrames / chunks.length;
  const index = Math.min(chunks.length - 1, Math.floor(frame / chunkDuration));
  const chunkStart = index * chunkDuration;
  const localProgress = Math.min(1, Math.max(0, (frame - chunkStart) / Math.max(chunkDuration, 1)));

  return {
    text: chunks[index],
    progress: localProgress
  };
};

export const getCaptionForFrame = ({text, frame, durationInFrames}) =>
  getCaptionStateForFrame({text, frame, durationInFrames}).text;
