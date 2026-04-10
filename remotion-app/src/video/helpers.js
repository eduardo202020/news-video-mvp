export const buildSegments = ({segments, newspaperName, coverSrc, text}) => {
  if (segments && segments.length > 0) {
    return segments;
  }

  return [
    {
      newspaperName,
      coverSrc,
      text
    }
  ];
};

export const buildWordHighlights = (caption, progress) => {
  const captionWords = caption ? caption.split(" ") : [];
  const spokenWords = Math.floor(captionWords.length * progress);

  return captionWords.map((word, index) => ({
    key: `${word}-${index}`,
    text: `${index > 0 ? " " : ""}${word}`,
    active: index < spokenWords
  }));
};
